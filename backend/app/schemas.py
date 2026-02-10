from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime

# --- Tags ---
class TagBase(BaseModel):
    name: str
    color: Optional[str] = '#808080'

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: int

    class Config:
        from_attributes = True

# --- Attachments ---
class AttachmentBase(BaseModel):
    file_name: str
    file_type: str
    file_size: int
    extracted_text: Optional[str] = None

class Attachment(AttachmentBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Message Context ---
class MessageContextBase(BaseModel):
    document_name: str
    content: str
    is_active: bool = True

class MessageContext(MessageContextBase):
    id: int
    message_id: int
    document_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Messages ---
class MessageBase(BaseModel):
    role: str
    content: str
    model_used: Optional[str] = None

class MessageCreate(MessageBase):
    role: str = "user"
    chat_id: int
    attachments: Optional[List[int]] = [] # List of Attachment IDs
    use_smart_selector: Optional[bool] = False
    
    # Context Flags
    use_llm_data: Optional[bool] = True
    use_documents: Optional[bool] = True
    use_web_search: Optional[bool] = False


class Message(MessageBase):
    id: int
    chat_id: int
    created_at: datetime
    content: str
    thinking_process: Optional[str] = None
    augmented_content: Optional[str] = None
    attachments: List[Attachment] = []
    contexts: List[MessageContext] = []

    class Config:
        from_attributes = True

# --- Chats ---
class ChatBase(BaseModel):
    title: Optional[str] = "New Chat"

class ChatCreate(ChatBase):
    pass

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    tags: Optional[List[str]] = None

class Chat(ChatBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    tags: List[Tag] = []
    attachments: List[Attachment] = []
    
    class Config:
        from_attributes = True

class ChatWithMessages(Chat):
    messages: List[Message] = []

# --- Custom Responses ---
class ChatStreamResponse(BaseModel):
    chunk: str
