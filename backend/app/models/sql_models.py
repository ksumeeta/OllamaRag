from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table, BigInteger, Unicode, UnicodeText
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

# Many-to-Many Association Table
chat_tags = Table(
    'ChatTags', Base.metadata,
    Column('chat_id', Integer, ForeignKey('Chats.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('Tags.id', ondelete='CASCADE'), primary_key=True)
)

class Chat(Base):
    __tablename__ = 'Chats'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Unicode(255), default='New Chat')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False)
    
    # Relationships
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=chat_tags, back_populates="chats")
    attachments = relationship("Attachment", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = 'Messages'
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey('Chats.id', ondelete='CASCADE'))
    role = Column(String(50)) # user, assistant, system
    model_used = Column(Unicode(255), nullable=True)
    content = Column(UnicodeText) # NVARCHAR(MAX) in MSSQL
    augmented_content = Column(UnicodeText, nullable=True) # Full augmented prompt (System + RAG + User)
    routing_reason = Column(Unicode(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message")
    contexts = relationship("MessageContext", back_populates="message", cascade="all, delete-orphan")

class Tag(Base):
    __tablename__ = 'Tags'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(100), unique=True)
    color = Column(String(20), default='#808080')
    
    chats = relationship("Chat", secondary=chat_tags, back_populates="tags")

class Attachment(Base):
    __tablename__ = 'Attachments'
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey('Messages.id'), nullable=True)
    chat_id = Column(Integer, ForeignKey('Chats.id', ondelete='CASCADE'), nullable=True)
    
    file_name = Column(Unicode(255))
    file_type = Column(Unicode(100))
    file_size = Column(BigInteger)
    file_path = Column(Unicode(500))
    extracted_text = Column(UnicodeText, nullable=True) # NVARCHAR(MAX)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    message = relationship("Message", back_populates="attachments")
    chat = relationship("Chat", back_populates="attachments")

class MessageContext(Base):
    __tablename__ = 'MessageContext'
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey('Messages.id', ondelete='CASCADE'))
    document_id = Column(Unicode(255), nullable=True)
    document_name = Column(Unicode(255))
    content = Column(UnicodeText) # Full text content
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    message = relationship("Message", back_populates="contexts")
