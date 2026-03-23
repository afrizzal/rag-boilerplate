# RAG Chatbot API Boilerplate

A production-ready **Retrieval-Augmented Generation (RAG)** API boilerplate that lets you build a chatbot capable of answering questions based on your own documents — powered by **Gemini Flash** and local embeddings.

Built with **FastAPI · SQLAlchemy · MySQL · Sentence Transformers · Gemini Flash**

---

## Features

- **Document ingestion** — Upload PDF, DOCX, and TXT files via API or bulk-ingest from a local folder
- **Local embeddings** — Runs `all-MiniLM-L6-v2` locally via Sentence Transformers (free, no API needed)
- **MySQL storage** — All documents, chunks, embeddings, and Q&A history stored in MySQL
- **Gemini Flash generation** — Fast and cost-efficient LLM answers grounded in your documents
- **System instructions** — Teach the AI about your database schema, business rules, and formulas via a CRUD API — no redeployment needed
- **JWT authentication** — Secure API access; only authorized clients can call the endpoints
- **Auto Swagger UI** — Interactive API docs available at `/docs` out of the box
- **Bulk ingest script** — Index an entire folder of documents with a single command

---

## How It Works

```
PHASE 1 — Indexing (when a document is uploaded)

  File (PDF/DOCX/TXT)
       │
       ▼
  Extract Text
       │
       ▼
  Split into Chunks (default: 500 words, 50-word overlap)
       │
       ▼
  Generate Embeddings  ◄── Sentence Transformers (runs locally, free)
       │
       ▼
  Store in MySQL  (documents + document_chunks tables)


PHASE 2 — Question Answering

  User Question
       │
       ▼
  Embed Question  ◄── same local model
       │
       ▼
  Cosine Similarity  ◄── compare against all chunks in MySQL
       │
       ▼
  Top-K Relevant Chunks
       │
       ▼
  Gemini Flash  ◄── "Answer based only on this context: [chunks]"
       │
       ▼
  Answer  →  saved to MySQL  →  returned to client
```

---

## Project Structure

```
rag-boilerplate/
├── app/
│   ├── main.py                   # FastAPI entry point; creates DB tables on startup
│   ├── config.py                 # All settings loaded from .env
│   ├── database.py               # SQLAlchemy engine, session, Base
│   ├── auth.py                   # JWT creation, verification, password hashing
│   ├── models/
│   │   ├── document.py           # Tables: documents, document_chunks
│   │   ├── qa.py                 # Tables: questions, answers, relevant_chunks
│   │   └── user.py               # Table: api_users
│   ├── schemas/
│   │   ├── document.py           # Pydantic request/response for documents
│   │   ├── qa.py                 # Pydantic request/response for Q&A
│   │   └── auth.py               # Pydantic schemas for auth
│   ├── services/
│   │   ├── embedding.py          # Singleton SentenceTransformer loader
│   │   ├── document_processor.py # Extract → chunk → embed → save pipeline
│   │   └── rag.py                # Retrieve → generate → save pipeline
│   └── routers/
│       ├── auth.py               # POST /api/auth/token, GET /api/auth/me
│       ├── documents.py          # CRUD for /api/documents/*
│       └── qa.py                 # POST /api/qa/ask, GET /api/qa/history
├── ingest.py                     # CLI script to bulk-index a local folder
├── create_user.py                # CLI script to create API user accounts
├── requirements.txt
├── .env.example                  # Configuration template
└── README.md
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| MySQL | 5.7+ |
| Gemini API Key | Free at [aistudio.google.com](https://aistudio.google.com) |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/rag-boilerplate.git
cd rag-boilerplate
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first run will download the `all-MiniLM-L6-v2` embedding model (~90 MB). This happens once and is cached locally.

### 4. Create the MySQL database

```sql
CREATE DATABASE rag_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# MySQL
DB_NAME=rag_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306

# Gemini API — get yours free at aistudio.google.com
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash

# JWT — generate a strong secret:
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your-random-secret-key-min-32-chars
JWT_EXPIRE_HOURS=24

# RAG tuning
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_CHUNKS=5
```

### 6. Create the first API user

```bash
python create_user.py my-app --description "My Application"
```

Save the generated password — it won't be shown again.

### 7. Start the server

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`.
All MySQL tables are created automatically on first startup.
Interactive API docs: **`http://localhost:8000/docs`**

---

## Authentication

All endpoints (except `POST /api/auth/token`) require a valid JWT token.

### Step 1 — Get a token

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "my-app", "password": "your-password"}'
```

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in_hours": 24
}
```

### Step 2 — Use the token in every request

```bash
curl http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer eyJhbGci..."
```

Tokens expire after `JWT_EXPIRE_HOURS` (default: 24 hours). Simply re-call `/api/auth/token` to get a new one.

### Managing API users

```bash
# Create a new user
python create_user.py mis-app --description "MIS Application"

# Reset password for an existing user
python create_user.py mis-app --reset
```

---

## API Reference

### Auth

| Method | Endpoint | Auth required | Description |
|--------|----------|:---:|-------------|
| `POST` | `/api/auth/token` | No | Login and receive JWT token |
| `GET` | `/api/auth/me` | Yes | Get current user info |

---

### Documents

| Method | Endpoint | Auth required | Description |
|--------|----------|:---:|-------------|
| `GET` | `/api/documents/` | Yes | List all documents |
| `POST` | `/api/documents/upload` | Yes | Upload and process a document |
| `GET` | `/api/documents/{id}` | Yes | Get document details |
| `DELETE` | `/api/documents/{id}` | Yes | Delete a document and its chunks |

#### Upload a document

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@handbook.pdf" \
  -F "title=Employee Handbook"
```

```json
{
  "message": "Dokumen 'Employee Handbook' berhasil diupload dan diproses.",
  "document": {
    "id": "3f2a1b...",
    "title": "Employee Handbook",
    "file_type": "pdf",
    "file_size": 204800,
    "is_processed": true,
    "chunk_count": 24,
    "uploaded_at": "2026-03-23T10:00:00"
  }
}
```

---

### Q&A (Chatbot)

| Method | Endpoint | Auth required | Description |
|--------|----------|:---:|-------------|
| `POST` | `/api/qa/ask` | Yes | Ask a question |
| `GET` | `/api/qa/history?limit=20` | Yes | Get Q&A history |

#### Ask a question

```bash
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the annual leave policy?"}'
```

```json
{
  "question_id": "a1b2c3...",
  "answer_id": "d4e5f6...",
  "question": "What is the annual leave policy?",
  "answer": "Based on the Employee Handbook, the annual leave policy states that...",
  "confidence_score": 0.8734,
  "sources": [
    {
      "document": "Employee Handbook",
      "similarity_score": 0.9201,
      "excerpt": "Employees are entitled to 12 days of annual leave per year..."
    },
    {
      "document": "HR Policy 2025",
      "similarity_score": 0.8447,
      "excerpt": "Leave requests must be submitted at least 3 days in advance..."
    }
  ]
}
```

---

## System Instructions

System Instructions let you teach the AI about your specific domain — database table names, business rules, calculation formulas, and context — **without redeploying the app**. Instructions are stored in MySQL and automatically injected into every Gemini prompt.

### Instruction Categories

| Category | Use for |
|---|---|
| `schema` | Table names, column mappings, relationships |
| `rule` | Business logic, data filters, status definitions |
| `formula` | How to calculate KPIs and metrics |
| `context` | Company background, fiscal year, branch info |
| `general` | Any other instruction |

### Quick Setup via Seed Script

Edit `seed_instructions.py` with your domain knowledge, then run:

```bash
# Add instructions (skip existing ones)
python seed_instructions.py

# Overwrite existing instructions
python seed_instructions.py --replace
```

### Manage via API

```bash
# List all instructions
curl http://localhost:8000/api/instructions/ \
  -H "Authorization: Bearer <token>"

# Add a new instruction
curl -X POST http://localhost:8000/api/instructions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "schema_customer",
    "category": "schema",
    "order": 1,
    "content": "Customer table is named mis_cust. Columns: cust_id, cust_name, cust_phone, cust_created (registration date), branch_id."
  }'

# Update an instruction
curl -X PUT http://localhost:8000/api/instructions/<id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated content here..."}'

# Toggle active/inactive without deleting
curl -X POST http://localhost:8000/api/instructions/<id>/toggle \
  -H "Authorization: Bearer <token>"

# Delete
curl -X DELETE http://localhost:8000/api/instructions/<id> \
  -H "Authorization: Bearer <token>"
```

### How It Affects the Prompt

When the AI receives a question, the prompt sent to Gemini looks like this:

```
[DATABASE SCHEMA & TABLE MAPPING]
- Customer table is named mis_cust. Columns: cust_id, cust_name...
- Visit table is named mis_visit. Columns: visit_id, cust_id...

[BUSINESS RULES]
- Only count visits where visit_status = "done"
- Active customer = at least 1 visit in the last 90 days

[CALCULATION FORMULAS]
- New customer: first-time visitor in the given period
- Revenue: SUM(total_amount) WHERE trx_status = "paid"

=== DOCUMENT CONTEXT ===
[Source 1: Employee Handbook]
...relevant document chunks...
========================

Question: How many new customers visited last month?
Answer:
```

### Tips for Writing Good Instructions

- **Be specific** — `"table is named mis_cust"` is better than `"customer table"`
- **One fact per instruction** — easier to enable/disable individually
- **Use `order`** — lower numbers appear first in the prompt; put schema before rules
- **Use `is_active`** — disable instructions temporarily without losing them

---

## Bulk Ingest from a Local Folder

Index an entire directory of documents without uploading one by one.

```bash
# Index all supported files in a folder (including subfolders)
python ingest.py ./my-docs

# Use an absolute path
python ingest.py "C:/Users/you/Documents/knowledge-base"

# Clear all existing documents first, then re-index
python ingest.py ./my-docs --clear
```

**Supported formats:** `.pdf`, `.txt`, `.docx`, `.doc`

Files already in the database are automatically skipped (no duplicate processing).

Example output:

```
[INFO] Found 5 files in: ./my-docs
--------------------------------------------------
[1/5] handbook.pdf ... OK (24 chunks)
[2/5] faq.txt ... OK (6 chunks)
[3/5] products/catalog.docx ... SKIP (already indexed)
[4/5] policy.pdf ... OK (11 chunks)
[5/5] corrupted.pdf ... FAILED — file could not be read
--------------------------------------------------
Done: 3 succeeded | 1 skipped | 1 failed
```

> The FastAPI server does **not** need to be running. The ingest script connects to MySQL directly.

---

## Embedding in Your Application

### JavaScript / TypeScript

```javascript
const RAG_URL = 'http://localhost:8000'
let token = null

// Authenticate once (e.g., on app startup)
async function authenticate() {
  const res = await fetch(`${RAG_URL}/api/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'my-app', password: 'your-password' })
  })
  const data = await res.json()
  token = data.access_token
}

// Ask a question
async function ask(question) {
  const res = await fetch(`${RAG_URL}/api/qa/ask`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ question })
  })
  return res.json()
}

// Usage
await authenticate()
const result = await ask('What is the refund policy?')
console.log(result.answer)
```

### Python

```python
import requests

RAG_URL = 'http://localhost:8000'

# Authenticate
res = requests.post(f'{RAG_URL}/api/auth/token', json={
    'username': 'my-app',
    'password': 'your-password'
})
token = res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Ask a question
res = requests.post(f'{RAG_URL}/api/qa/ask',
    headers=headers,
    json={'question': 'What is the refund policy?'}
)
print(res.json()['answer'])
```

### PHP

```php
<?php
$RAG_URL = 'http://localhost:8000';

// Authenticate
$ch = curl_init("$RAG_URL/api/auth/token");
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
    CURLOPT_POSTFIELDS => json_encode(['username' => 'my-app', 'password' => 'your-password']),
]);
$token = json_decode(curl_exec($ch), true)['access_token'];

// Ask a question
$ch = curl_init("$RAG_URL/api/qa/ask");
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        "Authorization: Bearer $token",
    ],
    CURLOPT_POSTFIELDS => json_encode(['question' => 'What is the refund policy?']),
]);
$result = json_decode(curl_exec($ch), true);
echo $result['answer'];
```

---

## Configuration Reference

All options are set in `.env`:

| Variable | Default | Description |
|---|---|---|
| `DB_NAME` | `rag_db` | MySQL database name |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | _(empty)_ | MySQL password |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `GEMINI_API_KEY` | _(required)_ | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model to use |
| `JWT_SECRET_KEY` | _(required)_ | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_HOURS` | `24` | Token validity duration in hours |
| `CHUNK_SIZE` | `500` | Words per document chunk |
| `CHUNK_OVERLAP` | `50` | Overlapping words between consecutive chunks |
| `TOP_K_CHUNKS` | `5` | Number of relevant chunks sent to the LLM |

**Tuning tips:**
- Increase `TOP_K_CHUNKS` for more complete answers (slightly higher API cost)
- Decrease `CHUNK_SIZE` for documents with many distinct topics
- Use `gemini-1.5-pro` instead of `flash` for higher answer quality

---

## Database Schema

```
documents                    document_chunks
─────────────────────        ──────────────────────────
id          STRING(36) PK    id           STRING(36) PK
title       VARCHAR(255)     document_id  FK → documents.id
content     TEXT             content      TEXT
file_type   VARCHAR(50)      chunk_index  INT
file_size   INT              embedding    JSON  ← float array
is_processed BOOLEAN         created_at   DATETIME
uploaded_at DATETIME
processed_at DATETIME


questions                    answers                   relevant_chunks
─────────────────            ────────────────────      ──────────────────────────
id       STRING(36) PK       id      STRING(36) PK     id               STRING(36) PK
text     TEXT                question_id FK            question_id      FK → questions.id
embedding JSON               text    TEXT              chunk_id         FK → document_chunks.id
created_at DATETIME          confidence_score FLOAT    similarity_score FLOAT
                             created_at DATETIME       rank             INT


api_users
──────────────────────
id           STRING(36) PK
username     VARCHAR(100)
hashed_password VARCHAR(255)
description  VARCHAR(255)
is_active    BOOLEAN
created_at   DATETIME
last_login   DATETIME
```

---

## Security Considerations

- **Never commit `.env`** — it is already listed in `.gitignore`
- **Generate a strong `JWT_SECRET_KEY`** using `python -c "import secrets; print(secrets.token_hex(32))"`
- **Keep this API on your internal network** — do not expose it to the public internet without an additional gateway
- **Do not index sensitive personal data** (patient records, financial data) if you use an external LLM API — data is sent to Google's servers during generation. Use a local model (e.g., [Ollama](https://ollama.com)) for sensitive data.

---

## Tech Stack

| Layer | Technology | Cost |
|---|---|---|
| API Framework | FastAPI | Free |
| ORM | SQLAlchemy 2.0 | Free |
| Database | MySQL | Free |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) | Free — runs locally |
| LLM | Gemini Flash (Google) | Paid — very low cost |
| Auth | python-jose + passlib (bcrypt) | Free |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.
