# Financial Accountability MVP

> **Enterprise AI platform that transforms meeting transcripts into actionable commitments with human validation, audit trail, asynchronous processing and local LLM support.**

---

# Overview

Financial Accountability MVP is an enterprise-oriented AI application designed to eliminate one of the biggest operational problems in financial organizations:

> **Commitments made during meetings that are never tracked until they become business problems.**

The platform automatically processes meeting transcripts or audio recordings, extracts actionable commitments using a local Large Language Model, routes them for human validation, tracks their lifecycle and provides complete accountability through dashboards and audit trails.

Everything runs locally without sending sensitive financial information to external AI providers.

---

# Architecture

```
                 Audio / Text
                       │
                       ▼
              Meeting Intake
                       │
                       ▼
          Background Processing Worker
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   Faster-Whisper              Text Input
          │                         │
          └────────────┬────────────┘
                       ▼
                 Ollama (Llama 3.1)
                       │
                       ▼
          Commitment Extraction Engine
                       │
                       ▼
              Human Review Queue
                       │
                       ▼
        Approved Business Commitments
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
 Dashboard                    Audit Trail
```

---

# Main Features

## AI-powered meeting processing

* Audio transcription using Faster-Whisper
* Local LLM inference using Ollama
* Structured commitment extraction
* Confidence scoring
* Evidence preservation
* Human validation workflow

---

## Meeting Management

* Text meetings
* Audio meetings
* TXT upload
* Automatic transcription
* Processing status tracking
* Background worker
* Retry processing

---

## Commitment Lifecycle

* Automatic extraction
* Human approval
* Rejection workflow
* Closing
* Reopening
* Full audit history

---

## Client Management

* Automatic client creation
* Commitment history
* Timeline
* Ownership

---

## Dashboard

Traffic-light visualization:

| Status    | Rule      |
| --------- | --------- |
| 🟢 Green  | ≤ 7 days  |
| 🟡 Yellow | 8–21 days |
| 🔴 Red    | > 21 days |

---

## Security

* Login
* Session management
* Role Based Access Control (RBAC)
* Audit logging
* Background processing isolation

---

# Technology Stack

## Backend

* Python 3.13
* FastAPI
* SQLAlchemy 2.x
* Alembic
* PostgreSQL
* SQLite

---

## Artificial Intelligence

* Ollama
* Llama 3.1 8B
* Faster-Whisper
* Local inference
* Prompt engineering

---

## Frontend

* Jinja2
* HTML5
* CSS

---

## Infrastructure

* Docker
* Docker Compose
* Uvicorn

---

# Current Processing Flow

```
Meeting
      │
      ▼
Queued
      │
      ▼
Transcribing
      │
      ▼
Extracting
      │
      ▼
Pending Review
      │
      ▼
Approved
      │
      ▼
Closed
```

---

# Project Structure

```
app/
 ├── main.py
 ├── worker.py
 ├── models.py
 ├── services.py
 ├── security.py
 ├── database.py
 ├── templates/
 ├── static/
 └── integrations/

scripts/
migrations/
tests/
docker-compose.yml
README.md
```

---

# Running locally

## Create virtual environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Start PostgreSQL

```powershell
docker compose up -d
```

---

## Configure environment

```powershell
$env:DATABASE_URL="postgresql+psycopg://financial:financial@localhost:5432/financial"

$env:USE_OLLAMA="true"

$env:OLLAMA_URL="http://localhost:11434"

$env:OLLAMA_MODEL="llama3.1:8b"

$env:WHISPER_COMMAND="python -m scripts.transcribe"
```

---

## Start Worker

```powershell
python -m app.worker
```

---

## Start API

```powershell
uvicorn app.main:app --reload
```

---

Open

http://localhost:8000

---

# Default Accounts

Administrator

```
admin@local
Admin123!
```

Additional test users

* manager@local
* advisor@local
* reviewer@local
* auditor@local

---

# Current Capabilities

* ✅ PostgreSQL
* ✅ Alembic migrations
* ✅ Local authentication
* ✅ RBAC
* ✅ Audit Trail
* ✅ Background Worker
* ✅ Faster-Whisper integration
* ✅ Ollama integration
* ✅ Human Review Queue
* ✅ Dashboard
* ✅ Docker support

---

# Planned Features

* Salesforce Integration
* CRM Synchronization
* Automatic commitment completion detection
* Semantic search
* Vector database
* Email notifications
* Calendar integration
* Enterprise reporting

---

# License

MIT License
