# app/models/paper.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

class Paper(BaseModel):
    """Data model for a research paper"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    topics: List[str] = []
    source: str  # arxiv, doi, upload, url
    text_content: Optional[str] = None

class PaperMetadata(BaseModel):
    """Data model for paper metadata"""
    title: str
    authors: List[str]
    abstract: str
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    topics: List[str] = []
    source: str  # arxiv, doi, upload, url

class TopicClassification(BaseModel):
    """Data model for topic classification"""
    topic: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
class PaperSummary(BaseModel):
    """Data model for paper summaries"""
    paper_id: str
    metadata: PaperMetadata
    summary: str
    key_findings: List[str]
    methodology: str
    implications: str
    citations: List[str] = []
    audio_file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)