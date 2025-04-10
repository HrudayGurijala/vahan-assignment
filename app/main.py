from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional, Dict, Any
import uvicorn
import os
import uuid
import shutil
import json
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
    
    class Config:
        # Allow arbitrary types to handle datetime serialization
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat() if dt else None
        }
    
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
os.makedirs("outputs/summaries", exist_ok=True)  # Add directory for storing summaries

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

# Helper function to save summary to file
def save_summary_to_file(summary_id: str, paper_summary: PaperSummary):
    """Save the paper summary to a JSON file"""
    # Convert the PaperSummary to a dictionary
    summary_dict = paper_summary.dict()
    
    # Handle datetime serialization
    if summary_dict['metadata']['publication_date']:
        summary_dict['metadata']['publication_date'] = summary_dict['metadata']['publication_date'].isoformat()
    
    # Save to file
    summary_file_path = f"outputs/summaries/{summary_id}.json"
    with open(summary_file_path, "w") as f:
        json.dump(summary_dict, f, indent=2)
    
    return summary_file_path

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
            # Try to get the paper link from various possible attributes
            paper_link = None
            if hasattr(paper, 'pdf_url'):
                paper_link = paper.pdf_url
            elif hasattr(paper, 'entry_id'):
                paper_link = paper.entry_id
            
            # Extract author names as strings
            author_names = []
            if hasattr(paper, 'authors'):
                for author in paper.authors:
                    # Convert author objects to strings
                    author_names.append(str(author))
            
            # Only include papers that have a link
            if paper_link:
                metadata = PaperMetadata(
                    title=paper.title,
                    authors=author_names,
                    abstract=paper.summary if hasattr(paper, 'summary') else "",
                    publication_date=paper.published if hasattr(paper, 'published') else None,
                    url=paper_link,
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
        topics=paper_req.topic_list or []
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
    
    if task["status"] == "completed":
        result = summaries_db.get(task_id)
        
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

@app.get("/summaries/{summary_id}/file")
async def get_summary_file(summary_id: str):
    """Get the JSON file for a summary"""
    if summary_id not in summaries_db:
        raise HTTPException(status_code=404, detail="Summary not found")
        
    summary_file_path = f"outputs/summaries/{summary_id}.json"
    if not os.path.exists(summary_file_path):
        raise HTTPException(status_code=404, detail="Summary file not found")
        
    return FileResponse(
        summary_file_path,
        media_type="application/json",
        filename=f"summary_{summary_id}.json"
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
        summary_id = task_id
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
        
        # Save summary to in-memory database
        summaries_db[summary_id] = paper_summary
        
        # Save summary to file
        summary_file_path = save_summary_to_file(summary_id, paper_summary)
        
        # Update task status
        processing_tasks[task_id].update({
            "status": "completed",
            "summary_file_path": summary_file_path
        })
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "message": str(e)
        })


async def process_url_task(task_id: str, url: str, topics: List[str]):
    """Background task to process a paper from URL"""
    try:
        # print(f"Starting URL task processing for task_id: {task_id}, URL: {url}")
        processing_tasks[task_id]["status"] = "processing"
        
        # Create the uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Download paper from URL
        file_path = f"uploads/url_{task_id}.pdf"
        
        # print(f"Attempting to download PDF from {url}")
        try:
            pdf_service.download_pdf(url, file_path)
        except Exception as download_error:
            # print(f"Download failed: {str(download_error)}")
            processing_tasks[task_id].update({
                "status": "failed",
                "message": f"Failed to download PDF from URL: {str(download_error)}"
            })
            return
        
        # print(f"Download completed. Checking file at {file_path}")
        # Verify the file exists and has content
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            # print(f"File verification failed: File empty or not found")
            processing_tasks[task_id].update({
                "status": "failed",
                "message": "Downloaded file is empty or does not exist"
            })
            return
            
        # print(f"Successfully downloaded PDF from URL to {file_path}")
        
        # Extract text from PDF
        # print(f"Extracting text from PDF")
        text_content = pdf_service.extract_text(file_path)
        if not text_content:
            # print(f"Text extraction failed: No text content extracted")
            processing_tasks[task_id].update({
                "status": "failed",
                "message": "Could not extract text from the PDF"
            })
            return
        
        # print(f"Text extraction successful. Content length: {len(text_content)}")
        
        # Create basic metadata for the downloaded file
        metadata = PaperMetadata(
            title=f"Downloaded document from URL",
            authors=["Unknown"],
            abstract="Abstract not available for URL document",
            source="url",
            url=url,
            topics=topics
        )
        
        # Generate summary using the writer agent
        # print(f"Generating summary draft")
        try:
            draft_summary = summary_writer.generate_summary(
                full_text=text_content
            )
            
            # print(f"Draft summary generated. Sending to proof reader")
            # Proof-read and improve the summary
            final_summary = proof_reader.review_summary(
                draft_summary=draft_summary,
                full_text=text_content
            )
            # print(f"Final summary created")
        except Exception as summary_error:
            # print(f"Summary generation failed: {str(summary_error)}")
            processing_tasks[task_id].update({
                "status": "failed",
                "message": f"Error generating summary: {str(summary_error)}"
            })
            return
        
        # Generate audio for the summary
        # print(f"Generating audio")
        audio_file_path = f"outputs/audio/summary_{task_id}.mp3"
        try:
            audio_service.generate_audio(final_summary["summary"], audio_file_path)
            # print(f"Audio generation complete")
        except Exception as audio_error:
            # print(f"Audio generation failed: {str(audio_error)}")
            # Continue even if audio fails - it's not critical
            audio_file_path = None
        
        # Create summary object
        summary_id = task_id
        paper_summary = PaperSummary(
            paper_id=task_id,
            metadata=metadata,
            summary=final_summary["summary"],
            key_findings=final_summary["key_findings"],
            methodology=final_summary["methodology"],
            implications=final_summary["implications"],
            citations=final_summary.get("citations", []),
            audio_file_path=audio_file_path
        )
        
        # Save summary to in-memory database
        # print(f"Saving summary with ID: {summary_id}")
        summaries_db[summary_id] = paper_summary
        
        # Save summary to file
        summary_file_path = save_summary_to_file(summary_id, paper_summary)
        # print(f"Summary saved to file: {summary_file_path}")
        
        # Update task status
        processing_tasks[task_id].update({
            "status": "completed",
            "summary_file_path": summary_file_path
        })
        # print(f"Task completed successfully")
        
    except Exception as e:
        # print(f"Unexpected error in process_url_task: {str(e)}")
        import traceback
        traceback.print_exc()
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