from docling.document_converter import (DocumentConverter, PdfFormatOption, WordFormatOption, InputFormat)
from docling.datamodel.pipeline_options import (PdfPipelineOptions, TableFormerMode, 
                                                AcceleratorOptions, AcceleratorDevice,TesseractCliOcrOptions)
from docling.chunking import HybridChunker
from docling_core.types.io import DocumentStream
from io import BytesIO
import pathlib
# from docling.datamodel.base_models import InputFormat

from sqlalchemy.orm import Session
from app.core.database import VectorSessionLocal
from app.models.vector_models import DocumentChunk
from app.core.config import settings
import ollama
import json
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#-----------------GPU CKECK-------------------------
import torch
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"CUDA available: {torch.cuda.is_available()}")
logger.info(f"CUDA version: {torch.version.cuda}")
logger.info(f"GPU device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# Setup Docling Pipeline
pdfpipeline_options = PdfPipelineOptions()
pdfpipeline_options.do_ocr = True
pdfpipeline_options.do_table_structure = True
pdfpipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
pdfpipeline_options.accelerator_options = AcceleratorOptions(num_threads=4, device=AcceleratorDevice.AUTO)
pdfpipeline_options.ocr_options = TesseractCliOcrOptions(lang=["auto"])

converter = DocumentConverter(
    format_options={
        "pdf": PdfFormatOption(pipeline_options=pdfpipeline_options)
    }
)
# converter = DocumentConverter()

import os
# ... (existing imports)

# ... (converter init)

def get_embedding(text: str) -> list[float]:
    response = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return response["embedding"]


def get_docling_document(file_path: str):
    """
    Centralized function to get a Docling Document from a file path.
    Handles supported file types via Docling and falls back to plain text read -> DocumentStream for others.
    """
    path_obj = pathlib.Path(file_path)
    ext = path_obj.suffix.lower()
    
    # Supported by Docling natively (PDF, DOCX, images, etc.)
    DOCLING_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", 
        ".html", ".htm", 
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".md"
    }

    try:
        if ext in DOCLING_EXTENSIONS:
            logger.info(f"Using Docling converter for {file_path}")
            conv_res = converter.convert(path_obj)
        else:
            # Fallback for plain text files (code, logs, txt, csv, json, etc.)
            logger.info(f"Reading as plain text for {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
                
                # Treat as Markdown (.md) to preserve structure/content in a generic way
                # We use a fake filename with .md extension so Docling invokes the MD parser
                fake_filename = path_obj.stem + ".md"
                ds = DocumentStream(name=fake_filename, stream=BytesIO(text_content.encode("utf-8")))
                
                conv_res = converter.convert(ds)
            except Exception as read_err:
                 logger.error(f"Failed to read file as text: {read_err}")
                 raise read_err

        return conv_res.document
    except Exception as e:
        logger.error(f"Docling conversion failed for {file_path}: {e}")
        raise e

def extract_text_content(file_path: str) -> str:
    """
    Extracts text content from a file using the centralized Docling logic.
    Returns markdown-formatted text.
    """
    try:
        doc = get_docling_document(file_path)
        return doc.export_to_markdown()
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return ""

def process_and_index_document(file_path: str, doc_id: str):
    logger.info(f"Processing file: {file_path}")
    
    # 1. Convert Document (Docling)
    try:
        doc = get_docling_document(file_path)
        
        # logger.info(f"Document converted. Pages: {len(doc.pages)}")
        logger.info(f"Document converted. Pages: {len(doc.pages)}\n-------------\n{doc.export_to_markdown()}\n-------------\n")
    except Exception as e:
        logger.error(f"Docling conversion failed: {e}")
        raise e

    # 2. Chunking (Hybrid)
    chunker = HybridChunker(
        tokenizer="sentence-transformers/all-MiniLM-L6-v2", # Default, or align with nomic if possible
        # merge_peers=True
    )
    chunks_iter = chunker.chunk(doc)
    chunks = list(chunks_iter)
    logger.info(f"Generated {len(chunks)} chunks.")

    # 3. Embedding & Storage
    if not VectorSessionLocal:
        logger.warning("Vector DB not configured. Skipping indexing.")
        return

    vector_db = VectorSessionLocal()
    try:
        for i, chunk in enumerate(chunks):
            # logger.info(f"\n--------------Processing chunk {i+1}/{len(chunks)}")
            logger.info(f"\nProcessing chunk {i+1}/{len(chunks)} chunk.text:\n-------------\n{chunk.text}\n--------------------\n")    
            text_content = chunk.text
            meta = chunk.meta.export_json_dict()
            
            # Embed
            embedding = get_embedding(text_content)
            
            # Store
            db_chunk = DocumentChunk(
                doc_id=doc_id,
                text=text_content,
                embedding=embedding,
                metadata_json=json.dumps(meta)
            )
            vector_db.add(db_chunk)
        
        vector_db.commit()
        vector_db.commit()
        logger.info(f"Indexed {len(chunks)} chunks to Vector DB.")
    except Exception as e:
        vector_db.rollback()
        logger.error(f"Indexing failed: {e}")
        raise e
    finally:
        vector_db.close()

    return doc.export_to_markdown() # Return full text/markdown for MS SQL if needed

def retrieve_relevant_chunks(query: str, doc_ids: list[str], top_k: int = 5) -> list[dict]:
    if not VectorSessionLocal or not doc_ids:
        return []

    vector_db = VectorSessionLocal()
    try:
        if not query or not query.strip():
            logger.info("Empty query for retrieval. Skipping.")
            return []

        query_embedding = get_embedding(query)
        
        # PGVector search: Use L2 distance (or cosine if normalized)
        # Using l2_distance operator <->
        results = vector_db.query(DocumentChunk).filter(
            DocumentChunk.doc_id.in_(doc_ids)
        ).order_by(
            DocumentChunk.embedding.l2_distance(query_embedding)
        ).limit(top_k).all()
        
        return [
            {
                "text": chunk.text,
                "doc_id": chunk.doc_id,
                "val_score": 0.0, # Placeholder or actual distance if we can get it
                "meta": json.loads(chunk.metadata_json) if chunk.metadata_json else {}
            }
            for chunk in results
        ]
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return []
    finally:
        vector_db.close()

def delete_document_chunks(doc_id: str):
    """
    Deletes all chunks associated with a specific doc_id from the Vector DB.
    """
    if not VectorSessionLocal:
        logger.warning("Vector DB not configured. Skipping deletion.")
        return

    vector_db = VectorSessionLocal()
    try:
        # Delete chunks with matching doc_id
        # Note: Depending on your vector DB/ORM, this might need adjustment.
        # For PGVector with SQLAlchemy:
        deleted_count = vector_db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).delete()
        vector_db.commit()
        logger.info(f"Deleted {deleted_count} chunks for doc_id: {doc_id}")
    except Exception as e:
        vector_db.rollback()
        logger.error(f"Deletion failed for doc_id {doc_id}: {e}")
        raise e
    finally:
        vector_db.close()
