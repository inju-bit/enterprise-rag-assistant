# Enterprise AI Knowledge Assistant

An end-to-end Retrieval-Augmented Generation (RAG) application for analysing research papers and extracting information from PDF documents using Large Language Models (LLMs).

Built with **Python, FastAPI, React, LangChain, OpenAI, SentenceTransformers and ChromaDB**, the application enables users to upload multiple PDFs, manage a document library, perform semantic searches and ask AI-powered questions grounded in their selected documents.

The project also includes automated RAG evaluation using RAGAS, Python testing and a GitHub Actions CI/CD workflow.

## 1. Features

### Document Management
- Upload and store PDF research papers.
- Automatically extract text and divide documents into chunks.
- Generate semantic embeddings using SentenceTransformers.
- Store document embeddings in ChromaDB.
- Maintain a persistent document library using SQLite.
- Monitor document indexing status.
- Select individual PDFs for question answering.
- Delete individual documents and their corresponding vector embeddings.

### AI-Powered Research Assistant
- Ask natural-language questions about uploaded PDFs.
- Retrieve relevant text passages using vector similarity search.
- Generate contextual answers with OpenAI and LangChain.
- Summarise research objectives, methodologies and reported findings.
- Display supporting source passages alongside AI-generated answers.
- Restrict retrieval to the selected document to prevent mixing information across papers.

### Frontend
- Responsive React interface.
- Drag-and-drop PDF uploading.
- Document library with indexing statuses.
- Individual document selection and deletion.
- AI chat interface with Markdown-formatted responses.
- Source references and semantic similarity scores.
- Dark and light themes.
- In-app Back and Forward navigation.

### Evaluation and Testing
- RAGAS evaluation for faithfulness, answer relevancy and context precision.
- Automated PDF-processing tests using pytest.
- GitHub Actions workflow for Python testing and React production builds.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python, JavaScript |
| Backend | FastAPI |
| Frontend | React, Vite |
| LLM Integration | OpenAI API |
| LLM Orchestration | LangChain |
| Embedding Model | all-MiniLM-L6-v2 |
| Embedding Framework | SentenceTransformers |
| Vector Database | ChromaDB |
| Document Metadata | SQLite |
| PDF Processing | pypdf |
| Evaluation | RAGAS |
| Testing | pytest |
| CI/CD | GitHub Actions |
| Version Control | Git, GitHub |

## 3. System Architecture

```text
User
 |
 v
React Frontend
 |
 | Upload PDF / Select PDF / Ask Question
 v
FastAPI Backend
 |
 +----------------------+
 |                      |
 v                      v
PDF Processing      SQLite Database
 |                  Document Metadata
 v
Text Chunking
 |
 v
SentenceTransformers
 |
 v
ChromaDB Vector Store
 |
 v
Similarity Search
 |
 v
Relevant Document Passages
 |
 v
LangChain + OpenAI LLM
 |
 v
Grounded AI Response
 |
 v
React Chat Interface
```

## 4. RAG Pipeline

**Step 1: Document Upload**

The user uploads a PDF document through the React interface. FastAPI stores the original PDF locally and creates a document record in SQLite.

**Step 2: Text Extraction**

The backend extracts text from the PDF using pypdf.

**Step 3: Text Chunking**

Extracted text is split into smaller overlapping chunks to improve semantic retrieval.

**Step 4: Embedding Generation**

Each chunk is converted into a numerical vector using the SentenceTransformers model:

`sentence-transformers/all-MiniLM-L6-v2`

**Step 5: Vector Storage**

Embeddings, chunks and document metadata are stored in ChromaDB.

**Step 6: Semantic Retrieval**

When the user asks a question, the application generates a query embedding and retrieves relevant chunks belonging to the selected document.

**Step 7: Answer Generation**

LangChain passes the retrieved passages and user question to an OpenAI language model to generate a contextual response.

**Step 8: Source Display**

The frontend presents the AI response and supporting passages, including semantic similarity scores.

Similarity scores indicate the semantic relationship between the query and a retrieved passage. They do not represent the factual accuracy of the generated answer.

## 5. Project Structure

```text
enterprise-rag-assistant/
|
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── pdf_processor.py
│   ├── document_store.py
│   ├── vector_store.py
│   └── rag.py
|
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   ├── package.json
│   └── package-lock.json
|
├── evaluation/
│   ├── create_dataset.py
│   ├── collect_answers.py
│   ├── evaluate_ragas.py
│   └── datasets/
|
├── tests/
│   └── test_pdf_processor.py
|
├── .github/
│   └── workflows/
│       └── ci.yml
|
├── uploads/
├── chroma_data/
├── documents.db
├── requirements-ci.txt
├── .gitignore
├── .env
└── README.md
```

The `uploads/`, `chroma_data/`, `documents.db` and `.env` files contain local data or configuration and should not be committed to GitHub.

## 6. Installation

### Prerequisites

- Python 3.12
- Node.js and npm
- Git
- OpenAI API key

### Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/enterprise-rag-assistant.git
cd enterprise-rag-assistant
```

Replace `YOUR_USERNAME` with your GitHub username.

### Create Python Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Install Backend Dependencies

```bash
python -m pip install \
  fastapi \
  uvicorn \
  python-multipart \
  pypdf \
  chromadb \
  sentence-transformers \
  langchain-core \
  langchain-openai \
  python-dotenv
```

For reproducibility, install compatible versions of the machine-learning dependencies. The development environment used Python 3.12 with NumPy 1.26.4, SciPy 1.13.1, PyTorch 2.2.2, Transformers 4.44.2 and SentenceTransformers 3.0.1.

### Configure OpenAI API

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Never upload your actual API key to GitHub.

### Start Backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

### Install Frontend Dependencies

Open another terminal:

```bash
cd frontend
npm install
```

Start the React application:

```bash
npm run dev
```

Frontend:

http://localhost:5173

## 7. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application information |
| GET | `/health` | Backend health status |
| POST | `/upload` | Upload PDF and queue indexing |
| GET | `/documents` | List indexed and processing documents |
| GET | `/documents/{document_id}` | Retrieve document information |
| DELETE | `/documents/{document_id}` | Delete a specific PDF and its embeddings |
| POST | `/search` | Perform document-specific semantic search |
| POST | `/ask` | Generate a document-grounded AI answer |

### Example Question Request

```json
{
  "question": "Summarise the research methodology and key findings.",
  "document_id": "DOCUMENT_UUID",
  "top_k": 5
}
```

### Example Response Structure

```json
{
  "question": "Summarise the research methodology and key findings.",
  "document_id": "DOCUMENT_UUID",
  "document_name": "research.pdf",
  "answer": "The research investigates...",
  "sources": [
    {
      "filename": "research.pdf",
      "document_id": "DOCUMENT_UUID",
      "text": "Relevant document passage...",
      "similarity": 0.78
    }
  ]
}
```

These example values illustrate the API format and are not actual evaluation results.

## 8. RAGAS Evaluation

RAGAS provides metrics to evaluate different aspects of the RAG pipeline.

The project uses:

- **Faithfulness:** Measures whether generated claims are supported by retrieved contexts.
- **Answer Relevancy:** Evaluates whether the generated answer addresses the user's question.
- **Context Precision:** Evaluates the relevance and ranking of retrieved contexts against a reference answer.

### Initial Evaluation Results

A five-question evaluation produced:

| Metric | Average Score |
|---|---:|
| Faithfulness | 1.0000 |
| Answer Relevancy | 0.6330 |
| Context Precision | 0.6067 |

These scores came from a small initial experiment. Reference answers were not independently verified, so the results should be treated as preliminary rather than a definitive assessment of system accuracy.

### Run Evaluation

Start the backend first, then activate the evaluation environment:

```bash
cd evaluation
source .venv/bin/activate

python create_dataset.py
python collect_answers.py
python evaluate_ragas.py
```

The evaluation scripts save collected responses and metric results locally.

## 9. Automated Testing

The project includes pytest tests for PDF extraction, including blank documents, multi-page documents and invalid PDF input.

Run:

```bash
python -m pytest tests/ -v
```

## 10. CI/CD Pipeline

GitHub Actions automates basic code validation.

The workflow is configured to run on pushes, pull requests and manual triggers.

### Python Job

- Sets up Python 3.12.
- Installs lightweight CI dependencies.
- Compiles backend Python files.
- Runs PDF-processing tests with pytest.

### React Job

- Sets up Node.js.
- Installs frontend dependencies.
- Builds the React application.

The current CI pipeline verifies the PDF-processing test suite and frontend build. It does not run the full RAG pipeline, OpenAI integration or RAGAS evaluation.

## 11. Current Limitations

- Only text-based PDFs are supported; scanned documents require OCR.
- Large documents can require additional processing time.
- Whole-document summarisation can require multiple LLM API requests.
- Vector retrieval quality depends on chunking, embedding models and document content.
- Chat history is not yet stored permanently.
- Background indexing uses FastAPI's local task mechanism rather than a distributed worker queue.
- The application currently lacks authentication and user-specific access controls.
- PDF data is stored locally, but selected document passages are sent to the configured OpenAI API when generating answers.

This is a development and portfolio application, not a production-ready multi-user document platform.

## 12. Future Improvements

Planned enhancements include:

- Hybrid search combining dense vectors and keyword retrieval.
- Reranking retrieved document passages.
- Page-level citations and PDF preview.
- Persistent chat conversations.
- OCR support for scanned PDFs.
- User authentication and document ownership.
- S3 document storage and AWS deployment.
- Dedicated background worker queues.
- Expanded RAGAS evaluation datasets.
- Monitoring, logging and observability.
- Docker containerisation and deployment pipelines.

## 13. Skills Demonstrated

This project demonstrates practical experience with:

- Python backend development
- REST API design
- React frontend development
- Large Language Model integration
- Retrieval-Augmented Generation
- LangChain orchestration
- Vector databases and semantic search
- PDF ingestion and processing
- SQLite persistence
- ML embedding models
- RAG evaluation with RAGAS
- Automated testing
- GitHub Actions CI/CD
- Full-stack AI application development

## 14. Security Considerations

The application is intended to run locally during development.

Before public deployment, authentication, authorisation, file ownership checks, upload validation and API rate limiting should be implemented.

API keys must remain server-side. Uploaded PDF content and vector databases should not be included in public Git repositories.

## 15. Licence

No open-source licence has been selected yet. Unless a licence is added, standard copyright restrictions apply.