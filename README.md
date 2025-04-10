# Research Paper Summarization System

A multi-agent system for finding, analyzing, and summarizing research papers from various sources, organizing them by topic, and generating audio podcasts discussing the findings.

## Features

- Search for research articles on arXiv with filtering options (relevance, recency, etc.)
- Process papers from uploaded PDFs, URLs to academic repositories, and DOI references
- Classify papers based on user-provided topics
- Generate comprehensive paper summaries with key findings, methodology, and implications
- Create audio podcast versions of the summaries
- Include citations for source traceability

## System Architecture

The system uses a FastAPI backend with a multi-agent architecture:

1. **Web Services Layer**:
   - FastAPI application handles HTTP requests and responses
   - Endpoints for paper searches, uploads, URL processing, and DOI handling
   - Background task processing for asynchronous operations

2. **Agent Layer**:
   - **Summary Writer Agent**: Generates initial paper summaries
   - **Proof Reader Agent**: Reviews and improves generated summaries

3. **Service Layer**:
   - **ArxivService**: Handles searches on arXiv
   - **DoiService**: Processes DOI references
   - **PdfService**: Extracts text from PDFs and downloads papers
   - **AudioService**: Converts text summaries to audio
   - **Classification**: Categorizes papers by topic

4. **Storage Layer**:
   - File-based storage for uploads, summaries, and audio files
   - In-memory storage for task statuses and paper metadata

## Multi-Agent Design and Coordination

The system implements a pipeline approach to multi-agent coordination:

1. **Task Initiation**: API endpoints create background tasks for processing papers
2. **Task Tracking**: Each task receives a unique ID for status tracking
3. **Agent Coordination**: The main application orchestrates the workflow between agents
4. **Service Integration**: Specialized services handle specific tasks (PDF processing, audio generation)
5. **Pipeline Processing**: Papers flow through a defined sequence:
   - Text extraction → Summary generation → Proof reading → Audio conversion

The agents communicate through structured data formats, with each focusing on its specialized role while the FastAPI application manages the overall workflow.

## Paper Processing Methodology

1. **Source Handling**:
   - Direct PDF uploads saved to the file system
   - URL submissions downloaded to local storage
   - DOI references resolved to paper details and PDFs

2. **Text Extraction**:
   - PDF text extraction using the PdfService
   - Basic metadata extraction (title, authors, source)

3. **Summary Generation**:
   - Draft summary created by SummaryWriterAgent
   - Review and improvement by ProofReaderAgent
   - Structured output with summary, key findings, methodology, and implications

4. **Topic Classification**:
   - User-provided topics associated with processed papers
   - Simple classification based on provided topic list

5. **Output Storage**:
   - Summaries stored both in-memory and as JSON files
   - Audio files saved to the file system

## Audio Generation Implementation

The system converts text summaries to audio using the AudioService:

1. The AudioService takes the generated summary text
2. Converts it to MP3 audio format using a text-to-speech engine(gTTS)
3. Saves the audio file to the outputs/audio directory
4. Associates the audio file path with the paper summary
5. Makes audio available via a dedicated API endpoint

## Setup Instructions

### Prerequisites

- Python 3.8+
- FastAPI
- Uvicorn
- PyPDF2
- Requests
- Google Text-to-Speech (gTTS)
- Other dependencies (specified in requirements.txt)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/research-paper-summarizer.git
   cd research-paper-summarizer
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables for OpenAI API (for the agents):
   ```
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

5. Run the application:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. Access the API at `http://localhost:8000` and the API documentation at `http://localhost:8000/docs`

## API Endpoints

- `POST /papers/search`: Search for papers on arXiv using various parameters
- `POST /papers/upload`: Upload a PDF file for processing
- `POST /papers/url`: Process a paper from a URL
- `POST /papers/doi`: Process a paper using its DOI
- `GET /tasks/{task_id}`: Check the status of a processing task
- `GET /summaries/{summary_id}`: Get a specific paper summary
- `GET /summaries/{summary_id}/audio`: Get the audio version of a summary
- `GET /summaries/{summary_id}/file`: Get the JSON file for a summary

## Limitations and Future Improvements

### Current Limitations

- Limited to text-based content extraction (figures, tables, and charts not analyzed)
- Simple topic classification using keyword matching
- In-memory storage not suitable for production workloads
- Basic error handling and retry logic
- Limited metadata extraction capabilities
- No authentication or user management

### Future Improvements

- Implement a database backend for persistent storage
- Add figure, table, and chart extraction from PDFs
- Improve topic classification using natural language processing
- Add support for more academic repositories and databases
- Implement cross-paper synthesis for related papers
- Enhance audio generation with better voice synthesis
- Add user authentication and personalized recommendations
- Develop a web front-end for easier interaction
- Implement batch processing for multiple papers
- Add comprehensive logging and monitoring

## Directory Structure

```
research-paper-summarizer/
├── app/
│   ├── agents/
│   │   ├── summary_writer_agent.py
│   │   └── proof_reader_agent.py
│   ├── services/
│   │   ├── arxiv_service.py
│   │   ├── doi_service.py
│   │   ├── pdf_service.py
│   │   ├── audio_service.py
│   │   └── classification.py
│   └── main.py
├── uploads/
├── outputs/
│   ├── audio/
│   └── summaries/
├── requirements.txt
└── README.md
```

# Testing

---

## `POST /papers/search`

```bash
curl -X POST http://localhost:8000/papers/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "max_results": 5,
    "sort_by": "relevance"
  }'
```

---

## `POST /papers/upload`

```bash
curl -X POST http://localhost:8000/papers/upload \
  -F "file=@/path/to/your/paper.pdf"
```

---

## `POST /papers/url`

```bash
curl -X POST http://localhost:8000/papers/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://arxiv.org/pdf/2107.12345.pdf"
  }'
```

---

## `POST /papers/doi`

```bash
curl -X POST http://localhost:8000/papers/doi \
  -H "Content-Type: application/json" \
  -d '{
    "doi": "10.1109/5.771073"
  }'
```

---

## `GET /tasks/{task_id}`

```bash
curl http://localhost:8000/tasks/your_task_id_here
```

---

## `GET /summaries/{summary_id}`

```bash
curl http://localhost:8000/summaries/your_summary_id_here
```

---

## `GET /summaries/{summary_id}/audio`

```bash
curl http://localhost:8000/summaries/your_summary_id_here/audio --output summary.mp3
```

---

## `GET /summaries/{summary_id}/file`

```bash
curl http://localhost:8000/summaries/your_summary_id_here/file --output summary.json
```

---

Replace `your_task_id_here` and `your_summary_id_here` with actual IDs you receive from previous requests.

### I have included the research paper I have used for the upload pdf is attached in the repository [basepaper.pdf]

### This is the URL of the other research paper from the demo [https://arxiv.org/pdf/2304.02924v1]