# app/main.py
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional, Dict, Any
import uvicorn
import os
import uuid
import shutil
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field

app = FastAPI(
    title="Research Paper Summarization System",
    description="A multi-agent system to search, process, and summarize research papers"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class PaperRequest(BaseModel):
    url: Optional[HttpUrl] = None
    doi: Optional[str] = None
    topic_list: Optional[List[str]] = []
    
class ArxivSearchParams(BaseModel):
    query: str
    max_results: int = 10
    sort_by: str = "relevance"  # relevance, lastUpdatedDate, submittedDate
    sort_order: str = "descending"
    year_from: Optional[int] = None
    year_to: Optional[int] = None

class PaperMetadata(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    topics: List[str] = []
    source: str  # arxiv, doi, upload, url

class PaperSummary(BaseModel):
    paper_id: str
    metadata: PaperMetadata
    summary: str
    key_findings: List[str]
    methodology: str
    implications: str
    citations: List[str] = []
    audio_file_path: Optional[str] = None
    
class ProcessingStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    message: Optional[str] = None
    result: Optional[PaperSummary] = None

# In-memory storage (replace with a proper database in production)
processing_tasks = {}
papers_db = {}
summaries_db = {}

# Create directories for uploads and outputs
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("outputs/audio", exist_ok=True)

# Import services and agents
from app.services.arxiv_service import ArxivService
from app.services.doi_service import DoiService
from app.services.pdf_service import PdfService
from app.services.audio_service import AudioService
from app.services.classification import classify_paper

from app.agents.summary_writer_agent import SummaryWriterAgent
from app.agents.proof_reader_agent import ProofReaderAgent

# Initialize services and agents
arxiv_service = ArxivService()
doi_service = DoiService()
pdf_service = PdfService()
audio_service = AudioService()

summary_writer = SummaryWriterAgent()
proof_reader = ProofReaderAgent()

@app.post("/papers/search", response_model=List[PaperMetadata])
async def search_papers(params: ArxivSearchParams):
    """Search for papers on arXiv based on provided parameters"""
    try:
        papers = arxiv_service.search(
            query=params.query,
            max_results=params.max_results,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            year_from=params.year_from,
            year_to=params.year_to
        )
        
        # Convert to PaperMetadata format
        results = []
        for paper in papers:
            metadata = PaperMetadata(
                title=paper.title,
                authors=paper.authors,
                abstract=paper.summary,
                publication_date=paper.published,
                url=paper.link,
                source="arxiv"
            )
            results.append(metadata)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching papers: {str(e)}")

@app.post("/papers/upload", response_model=ProcessingStatus)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    topics: str = Form("")
):
    """Upload a research paper PDF for processing"""
    task_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        file_path = f"uploads/{task_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Create processing task
        processing_tasks[task_id] = {"status": "pending", "file_path": file_path}
        
        # Parse topics
        topic_list = [t.strip() for t in topics.split(",")] if topics else []
        
        # Process paper in background
        background_tasks.add_task(
            process_paper_task, 
            task_id=task_id, 
            file_path=file_path, 
            topics=topic_list
        )
        
        return ProcessingStatus(task_id=task_id, status="pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.post("/papers/url", response_model=ProcessingStatus)
async def process_paper_url(background_tasks: BackgroundTasks, paper_req: PaperRequest):
    """Process a paper from a URL"""
    if not paper_req.url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    task_id = str(uuid.uuid4())
    processing_tasks[task_id] = {"status": "pending", "url": str(paper_req.url)}
    
    background_tasks.add_task(
        process_url_task,
        task_id=task_id,
        url=str(paper_req.url),
        topics=paper_req.topic_list
    )
    
    return ProcessingStatus(task_id=task_id, status="pending")

@app.post("/papers/doi", response_model=ProcessingStatus)
async def process_paper_doi(background_tasks: BackgroundTasks, paper_req: PaperRequest):
    """Process a paper using its DOI"""
    if not paper_req.doi:
        raise HTTPException(status_code=400, detail="DOI is required")
        
    task_id = str(uuid.uuid4())
    processing_tasks[task_id] = {"status": "pending", "doi": paper_req.doi}
    
    background_tasks.add_task(
        process_doi_task,
        task_id=task_id,
        doi=paper_req.doi,
        topics=paper_req.topic_list
    )
    
    return ProcessingStatus(task_id=task_id, status="pending")

@app.get("/tasks/{task_id}", response_model=ProcessingStatus)
async def get_task_status(task_id: str):
    """Check the status of a processing task"""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = processing_tasks[task_id]
    result = None
    
    if task["status"] == "completed" and "summary_id" in task:
        result = summaries_db.get(task["summary_id"])
        
    return ProcessingStatus(
        task_id=task_id,
        status=task["status"],
        message=task.get("message"),
        result=result
    )

@app.get("/summaries/{summary_id}", response_model=PaperSummary)
async def get_summary(summary_id: str):
    """Get a specific paper summary"""
    if summary_id not in summaries_db:
        raise HTTPException(status_code=404, detail="Summary not found")
        
    return summaries_db[summary_id]

@app.get("/summaries/{summary_id}/audio")
async def get_summary_audio(summary_id: str):
    """Get the audio version of a summary"""
    if summary_id not in summaries_db:
        raise HTTPException(status_code=404, detail="Summary not found")
        
    summary = summaries_db[summary_id]
    if not summary.audio_file_path or not os.path.exists(summary.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio not generated for this summary")
        
    return FileResponse(
        summary.audio_file_path, 
        media_type="audio/mpeg", 
        filename=f"summary_{summary_id}.mp3"
    )

async def process_paper_task(task_id: str, file_path: str, topics: List[str]):
    """Background task to process an uploaded paper"""
    try:
        processing_tasks[task_id]["status"] = "processing"
        
        # Extract text from PDF
        text_content = pdf_service.extract_text(file_path)
        if not text_content:
            raise ValueError("Could not extract text from the PDF")
        
        # Extract basic metadata from the PDF (filename or attempt to parse title)
        filename = os.path.basename(file_path)
        # Create basic metadata for the uploaded file
        metadata = PaperMetadata(
            title=f"Uploaded document: {filename}",
            authors=["Unknown"],  # You might want to extract this from the PDF if possible
            abstract="Abstract not available for uploaded document",
            source="upload",
            topics=topics
        )
        
        # Generate summary using the writer agent
        draft_summary = summary_writer.generate_summary(
            full_text=text_content
        )
        
        # Proof-read and improve the summary
        final_summary = proof_reader.review_summary(
            draft_summary=draft_summary,
            full_text=text_content
        )
        
        # Generate audio for the summary
        audio_file_path = f"outputs/audio/summary_{task_id}.mp3"
        audio_service.generate_audio(final_summary["summary"], audio_file_path)
        
        # Create summary object
        summary_id = str(uuid.uuid4())
        paper_summary = PaperSummary(
            paper_id=task_id,
            metadata=metadata,  # Add the metadata here
            summary=final_summary["summary"],
            key_findings=final_summary["key_findings"],
            methodology=final_summary["methodology"],
            implications=final_summary["implications"],
            citations=final_summary["citations"],
            audio_file_path=audio_file_path
        )
        
        # Save summary
        summaries_db[summary_id] = paper_summary
        
        # Update task status
        processing_tasks[task_id].update({
            "status": "completed",
            "summary_id": summary_id
        })
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "message": str(e)
        })


async def process_url_task(task_id: str, url: str, topics: List[str]):
    """Background task to process a paper from URL"""
    try:
        processing_tasks[task_id]["status"] = "processing"
        
        # Download paper from URL
        file_path = f"uploads/url_{task_id}.pdf"
        pdf_service.download_pdf(url, file_path)
        
        # Process the downloaded PDF
        await process_paper_task(task_id, file_path, topics)
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "message": str(e)
        })

async def process_doi_task(task_id: str, doi: str, topics: List[str]):
    """Background task to process a paper from DOI"""
    try:
        processing_tasks[task_id]["status"] = "processing"
        
        # Get paper details and PDF URL from DOI
        paper_details = doi_service.get_paper_details(doi)
        
        if not paper_details or "pdf_url" not in paper_details:
            raise ValueError("Could not retrieve PDF URL from DOI")
            
        # Download the paper
        file_path = f"uploads/doi_{task_id}.pdf"
        pdf_service.download_pdf(paper_details["pdf_url"], file_path)
        
        # Process the downloaded PDF
        await process_paper_task(task_id, file_path, topics)
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "message": str(e)
        })

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)