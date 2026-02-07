from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

BaseVector = declarative_base()

class DocumentChunk(BaseVector):
    __tablename__ = 'document_chunks'

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True) # Reference to Attachment ID (e.g., "att_123")
    text = Column(Text)
    embedding = Column(Vector(768)) # nomic-embed-text dimension
    metadata_json = Column(Text, nullable=True) # JSON string for page_no, bbox, etc.
