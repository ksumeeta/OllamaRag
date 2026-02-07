from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import sql_models as models
from app import schemas
from app.services import ollama_service
from app.utils_log import log_debug

router = APIRouter()

@router.get("/", response_model=List[schemas.Chat])
def read_chats(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    chats = db.query(models.Chat).order_by(models.Chat.updated_at.desc()).offset(skip).limit(limit).all()
    return chats

@router.post("/", response_model=schemas.Chat)
def create_chat(chat: schemas.ChatCreate, db: Session = Depends(get_db)):
    db_chat = models.Chat(title=chat.title)
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

@router.get("/{chat_id}", response_model=schemas.ChatWithMessages)
def read_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.delete("/{chat_id}")
def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"ok": True}

@router.patch("/{chat_id}", response_model=schemas.Chat)
def update_chat(chat_id: int, chat_update: schemas.ChatUpdate, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat_update.title is not None:
        chat.title = chat_update.title
    if chat_update.is_archived is not None:
        chat.is_archived = chat_update.is_archived
        
    if chat_update.tags is not None:
        # Clear current tags
        chat.tags = []
        for tag_name in chat_update.tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            
            # Check if tag exists
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if not tag:
                # Create if not exists
                tag = models.Tag(name=tag_name)
                db.add(tag)
                db.commit()
                db.refresh(tag)
            
            if tag not in chat.tags:
                chat.tags.append(tag)
        
    db.commit()
    db.refresh(chat)
    return chat

# --- Streaming Chat Endpoint ---

@router.post("/message")
async def send_message(
    message_in: schemas.MessageCreate,
    db: Session = Depends(get_db)
):
    print(f"DEBUG: Received message request: {message_in}")
    # 1. Fetch Chat
    chat = db.query(models.Chat).filter(models.Chat.id == message_in.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 2. Save User Message
    user_msg_content = message_in.content
    
    # NEW: Handle empty content with attachments (Implicit "Summarize/Analyze this")
    if not user_msg_content.strip() and message_in.attachments:
        user_msg_content = "Please analyze the attached document(s)."
    
    # Handle Attachments (Metadata/Text extraction context)
    attached_context = ""
    start_time = datetime.utcnow()
    
    if message_in.attachments:
        # Fetch actual attachment records from DB
        attachments = db.query(models.Attachment).filter(models.Attachment.id.in_(message_in.attachments)).all()
        for att in attachments:
            if att.extracted_text:
               attached_context += f"\n\n--- FILE: {att.file_name} ---\n{att.extracted_text}\n--- END FILE ---\n"
    
    user_msg = models.Message(
        chat_id=message_in.chat_id,
        role="user",
        content=message_in.content, # Store original user query in DB
        model_used=message_in.model_used,
        created_at=start_time
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Link attachments to the new message AND chat
    if message_in.attachments:
         db.query(models.Attachment).filter(models.Attachment.id.in_(message_in.attachments)).update(
             {"message_id": user_msg.id, "chat_id": message_in.chat_id}, synchronize_session=False
         )
         db.commit()

    # 3. Prepare Context
    
    # A. System Instruction (LLM Data Toggle)
    system_instruction = ""
    if not message_in.use_llm_data:
        system_instruction = "You are a stricter assistant. Answer ONLY using the provided context (Files, Documents, Web Search). Do not use your internal knowledge base. If the answer is not in the context, say 'I cannot answer this based on the provided context.'\n\n"
    
    # B. Web Search
    web_context = ""
    if message_in.use_web_search:
        try:
            search_query = await ollama_service.generate_search_query(message_in.model_used or "llama3", user_msg_content)
            print(f"DEBUG: Generated Search Query: {search_query}")
            search_results = await ollama_service.execute_web_search(search_query)
            web_context = f"\n\n--- WEB SEARCH RESULTS ({search_query}) ---\n{search_results}\n--- END WEB SEARCH ---\n"
            
            # Persist Web Search Context
            if search_results and "Error" not in search_results:
                web_ctx_entry = models.MessageContext(
                    message_id=user_msg.id,
                    document_name=f"Web Search: {search_query}",
                    content=search_results,
                    is_active=True
                )
                db.add(web_ctx_entry)
        except Exception as e:
            print(f"Web Search Error: {e}")
            web_context = f"\n[Web Search Failed: {str(e)}]\n"

    # C. RAG (Documents)
    rag_context = ""
    if message_in.use_documents:
        from app.services import ingestion
        
        # Get ALL attachments for this chat
        chat_attachments = db.query(models.Attachment).filter(models.Attachment.chat_id == message_in.chat_id).all()
        doc_ids = [str(att.id) for att in chat_attachments]
        
        # Retrieve chunks (Rich metadata)
        if doc_ids:
            chunks = ingestion.retrieve_relevant_chunks(user_msg_content, doc_ids)
        
        if chunks:
            rag_context_parts = []
            for chunk in chunks:
                text = chunk.get("text", "")
                doc_name = chunk.get("meta", {}).get("filename", "Unknown Document")
                # Append to context string
                rag_context_parts.append(f"--- DOCUMENT: {doc_name} ---\n{text}\n")
                
                # Persist RAG Context
                rag_ctx_entry = models.MessageContext(
                    message_id=user_msg.id,
                    document_id=chunk.get("doc_id"),
                    document_name=doc_name,
                    content=text,
                    is_active=True
                )
                db.add(rag_ctx_entry)
            
            rag_context = "\n\nRelevant Context from Documents:\n" + "\n".join(rag_context_parts)
            db.commit() # Commit context entries

    # D. Construct Final Prompt & Save Augmented Content
    final_content = user_msg_content
    context_block = f"{attached_context}{rag_context}{web_context}"
    
    if context_block:
        final_content = f"{system_instruction}User uploaded files/context. Use the following context to answer.\n\nContext:\n{context_block}\n\nUser Query: {user_msg_content}"
    elif system_instruction:
        final_content = f"{system_instruction}\nUser Query: {user_msg_content}"

    # Update User Message with Augmented Content
    user_msg.augmented_content = final_content
    db.commit()

    # 4. History (Last 5 Messages)
    history = db.query(models.Message).filter(
        models.Message.chat_id == message_in.chat_id,
        models.Message.id != user_msg.id 
    ).order_by(models.Message.created_at.desc()).limit(5).all() # RESTRICTED TO 5
    
    history = history[::-1]
    
    ollama_messages = []
    for msg in history:
        # If we had augmented content for previous messages, do we use it? 
        # Usually, cleaner to use original content for history to avoid massive context bloat.
        # But for correctness, maybe we should. Let's stick to original content for now to save tokens.
        ollama_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    ollama_messages.append({
        "role": "user",
        "content": final_content
    })

    # 5. Stream Generator
    async def response_generator():
        full_response = []
        try:
            async for chunk in ollama_service.stream_chat(message_in.model_used or "llama3", ollama_messages):
                full_response.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
            
            # Save Assistant Message
            response_text = "".join(full_response)
            if response_text:
                from app.core.database import SessionLocal
                new_db = SessionLocal()
                try:
                    asst_msg = models.Message(
                        chat_id=message_in.chat_id,
                        role="assistant",
                        content=response_text,
                        model_used=message_in.model_used
                    )
                    new_db.add(asst_msg)
                    # Update chat updated_at
                    chat_ref = new_db.query(models.Chat).filter(models.Chat.id == message_in.chat_id).first()
                    chat_ref.updated_at = datetime.utcnow()
                    
                    new_db.commit()
                except Exception as db_e:
                    print(f"Error saving assistant message: {db_e}")
                finally:
                    new_db.close()

    return StreamingResponse(response_generator(), media_type="text/event-stream")

@router.post("/search_context")
def search_context_endpoint(
    query_in: schemas.MessageCreate, # Reusing MessageCreate for convenience: content=query, chat_id=...
    db: Session = Depends(get_db)
):
    """
    Search vector DB for context.
    Returns: List of chunks with metadata.
    """
    from app.services import ingestion
    
    # We need doc_ids associated with this chat. 
    # Logic: Get all attachments for this chat? Or all attachments forever?
    # Usually searching within the current chat's scope is best.
    
    # Get all attachments for this chat
    chat_attachments = db.query(models.Attachment.id).filter(models.Attachment.chat_id == query_in.chat_id).all()
    if not chat_attachments:
        return []
        
    doc_ids = [str(att.id) for att in chat_attachments]
    
    chunks = ingestion.retrieve_relevant_chunks(query_in.content, doc_ids, top_k=10)
    return chunks
