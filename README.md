# Smart Legal Metrology Compliance Inspection Platform (SLM-CIP)
**SIH Problem Statement ID: 26034**
*"Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels."*

---

## 🏛️ Architectural Overview

SLM-CIP is an enterprise-grade digital enforcement platform designed to automate and augment Legal Metrology inspections. It adheres strictly to the guiding design principle:
> **"AI extracts evidence; a deterministic rule engine evaluates compliance."**

The platform consists of:
1. **Frontend**: Next.js 14/15, TypeScript, Tailwind CSS, Lucide icons, responsive officer dashboard & evidence viewer.
2. **Backend API**: Python FastAPI providing async RESTful endpoints, JWT/OAuth RBAC authorization, and automated OpenAPI documentation.
3. **AI / CV Pipeline**: Multi-stage pipeline covering Image Quality Assessment (blur, glare, skew, occlusion), Preprocessing, Region Detection (YOLO/RT-DETR), Multilingual OCR, and Structured Field Extraction. Includes new Google Gemini 3.8 Flash Hybrid Integrations.
4. **Deterministic Legal Rule Engine**: Versioned, auditable legal compliance engine evaluating mandatory declarations under Legal Metrology (Packaged Commodities) Rules, 2011 with a strict 4-state output (`COMPLIANT`, `NON_COMPLIANT`, `NEEDS_REVIEW`, `NOT_APPLICABLE`).
5. **Async Worker Tier**: Celery & Redis decoupled task processing for long-running computer vision and report generation.
6. **Data & Storage**: PostgreSQL relational database with immutable audit logging and S3-compatible MinIO object storage. Now supports built-in auth, PDF report generation, and Dynamic FAQ.

---

## 📂 Codebase Directory Hierarchy

```
SIH2026/
├── .env.example                       # Unified environment variable template
├── .gitignore                         # Python, Node, Celery, Docker ignore rules
├── docker-compose.yml                 # Multi-container orchestration
├── README.md                          # Platform documentation & setup guide
│
├── backend/                           # FastAPI API & Celery Worker Application
│   ├── requirements.txt               # Core API dependencies (FastAPI, SQLAlchemy, Celery, etc.)
│   ├── requirements-ai.txt            # CV/OCR & ML dependencies (OpenCV, PyTorch, YOLO, OCR)
│   ├── pyproject.toml                 # Backend tooling configuration
│   ├── Dockerfile.api                 # Container build for API
│   ├── Dockerfile.worker              # Container build for AI Worker
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, CORS, routers
│   │   ├── core/                      # Config, Security, DB session, Celery setup
│   │   ├── models/                    # SQLAlchemy ORM models (Users, Inspections, Evidence, Rules, Audit)
│   │   ├── schemas/                   # Pydantic DTOs for request/response validation
│   │   ├── api/v1/                    # Endpoints (Auth, Inspections, Images, Analysis, Rules, Reports)
│   │   ├── services/                  # Business logic services
│   │   ├── rule_engine/               # Deterministic legal rule evaluator & schemas
│   │   ├── pipeline/                  # AI/CV stages: Quality, Preprocessing, Detection, OCR, Extraction
│   │   ├── workers/                   # Celery background tasks
│   │   └── reporting/                 # PDF & DOCX report generators
│   └── tests/                         # Test suites for rule engine, pipeline, and API
│
├── rules/                             # Declarative versioned Legal Metrology rules (PC Rules 2011)
│   ├── pc_rules_2011_v1.json          # Core mandatory declaration rules
│   └── exemptions.json                # Category-based legal exemption criteria
│
├── frontend/                          # Next.js 14/15 App Router Web Application
│   ├── package.json                   # Frontend dependencies
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── tailwind.config.ts             # Tailwind CSS tokens & design system
│   ├── Dockerfile                     # Container build for Next.js
│   └── src/
│       ├── app/                       # 15 enforcement screens mapping PRD Section 25
│       ├── components/                # Modular UI, Evidence Bounding-Box Viewer, Status Pills
│       ├── lib/                       # API clients & token helpers
│       └── types/                     # Shared TypeScript domain types
│
└── scripts/                           # Operational scripts (DB init, rule seeder, environment runner)
    ├── init_db.py
    ├── seed_data.py
    └── setup_env.bat
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Docker & Docker Compose** (optional for containerized deployment)

### 1. Automated Setup (Windows)
Run the automated environment setup batch script:
```cmd
scripts\setup_env.bat
```

### 2. Manual Setup (Without Docker)

> **Note for Windows Users**: The Celery background worker requires **Redis** to function as a message broker. Redis does not run natively on Windows. If you are avoiding Docker, you must either:
> 1. Run Redis via Windows Subsystem for Linux (WSL).
> 2. Install a Windows-native Redis port like [Memurai](https://www.memurai.com/).
> 
> *By default, manual setup uses local SQLite databases and local file storage instead of Postgres and MinIO.*

#### Backend Setup
```bash
# Navigate to backend directory & create virtual environment
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run database migrations / initialization
python ../scripts/init_db.py
python ../scripts/seed_data.py

# Launch FastAPI development server
uvicorn app.main:app --reload --port 8000
```

#### Celery Worker
```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info -P solo
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend
npm install
npm run dev
```

### 3. Docker Setup (Containerized)
The easiest way to run the entire stack (PostgreSQL, Redis, MinIO, FastAPI Backend, Celery Worker, and Next.js Frontend) is using Docker Compose.

```bash
# From the root directory (where docker-compose.yml is located)
# 1. Build and start all containers in the background
docker compose up -d --build

# 2. View the logs for all services
docker compose logs -f

# 3. To stop the containers
docker compose down
```

The application will be accessible at:
- **Web UI**: [http://localhost:3000](http://localhost:3000)
- **API Documentation (Swagger)**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)
