# RoboVault

Inventory & equipment lending API for the robotics club.

## Status

Software Engineering academic project — FastAPI backend with PostgreSQL,
Docker deployment, and CI/CD via GitHub Actions.

## Architecture

```text
app/
├── api/routes/       # HTTP endpoints (thin — no business logic)
│   ├── auth.py       #   POST /register, POST /login
│   ├── items.py      #   CRUD inventory (admin writes, any user reads)
│   ├── loans.py      #   Request / approve / reject / return
│   └── ocr.py        #   POST /parse-bill (admin only)
├── core/
│   ├── config.py     #   Pydantic Settings (env-driven)
│   └── security.py   #   bcrypt hashing, JWT create/decode
├── db/
│   ├── base.py       #   SQLAlchemy declarative base
│   └── session.py    #   Engine + get_db dependency
├── models/           #   SQLAlchemy ORM models
│   ├── user.py       #     User (ADMIN / MEMBER / GUEST)
│   ├── item.py       #     Item (inventory with quantity tracking)
│   ├── loan.py       #     Loan (request → approved → returned)
│   └── bill.py       #     BillUpload (OCR scan records)
├── ocr/
│   ├── preprocess.py #   Image normalization for Tesseract
│   └── parser.py     #   Regex line-item extraction
├── schemas/          #   Pydantic request/response models
│   ├── user.py       #     UserCreate, UserRead, Token
│   ├── item.py       #     ItemCreate, ItemUpdate, ItemRead
│   └── loan.py       #     LoanRequest, LoanRead
├── services/
│   ├── files.py      #   Photo upload helper
│   └── lending.py    #   Business rules (stock checks, overdue flag)
└── main.py           #   FastAPI app factory
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.141 |
| Database | PostgreSQL 16 (Docker) |
| ORM | SQLAlchemy 2.0 (mapped columns) |
| Migrations | Alembic |
| Auth | bcrypt + python-jose JWT |
| OCR | Tesseract + Pillow + OpenCV |
| Testing | pytest + pytest-cov |
| Linting | ruff + black |
| CI/CD | GitHub Actions |
| Containerization | Docker + Docker Compose |

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/SuhanVerse/RoboVault.git
cd RoboVault
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the database

```bash
docker compose up -d db
```

Wait for healthy status:

```bash
docker compose ps   # STATUS should say "(healthy)"
```

### 3. Apply database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

## API Reference

Interactive docs: open http://localhost:8000/docs (Swagger UI) or /redoc.

### Authentication

```bash
# Register a new account (default role: GUEST)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ali","email":"ali@club.edu","password":"secret123"}'

# Login and get a JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ali@club.edu","password":"secret123"}'
# → {"access_token": "...", "token_type": "bearer"}
```

### Inventory (items)

```bash
# List all items (requires any authenticated user)
curl http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer <token>"

# Create an item (ADMIN only)
curl -X POST http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer <admin_token>" \
  -F "name=Motors" \
  -F "category=electronics" \
  -F "quantity_total=10" \
  -F "unit_price=25.00" \
  -F "source=MANUAL"
```

### Lending (loans)

```bash
# Request a loan (any authenticated user)
curl -X POST http://localhost:8000/api/v1/loans/request \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"item_id": 1, "quantity": 2, "due_days": 7}'

# Approve a loan (ADMIN only)
curl -X PUT http://localhost:8000/api/v1/loans/1/approve \
  -H "Authorization: Bearer <admin_token>"

# Return a loan (ADMIN only)
curl -X PUT http://localhost:8000/api/v1/loans/1/return \
  -H "Authorization: Bearer <admin_token>"
```

### OCR (bill scanning)

```bash
# Parse a bill image → suggestions (ADMIN only)
curl -X POST http://localhost:8000/api/v1/ocr/parse-bill \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@bill_photo.jpg"
# → {"id": 1, "status": "PROCESSED", "suggestions": [...]}
```

### Health Check

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

## Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Create account |
| POST | `/api/v1/auth/login` | None | Get JWT token |
| GET | `/api/v1/items` | Any user | List inventory |
| POST | `/api/v1/items` | ADMIN | Create item |
| GET | `/api/v1/items/{id}` | Any user | Get item details |
| PUT | `/api/v1/items/{id}` | ADMIN | Update item |
| DELETE | `/api/v1/items/{id}` | ADMIN | Delete item |
| POST | `/api/v1/loans/request` | Any user | Request a loan |
| PUT | `/api/v1/loans/{id}/approve` | ADMIN | Approve loan |
| PUT | `/api/v1/loans/{id}/reject` | ADMIN | Reject loan |
| PUT | `/api/v1/loans/{id}/return` | ADMIN | Return loan |
| POST | `/api/v1/ocr/parse-bill` | ADMIN | Parse bill image |
| GET | `/health` | None | Health check |

## Roles & Permissions

| Role | Can do |
|------|--------|
| **ADMIN** | Full access — create/edit/delete items, approve/reject/return loans, run OCR |
| **MEMBER** | Read items, request loans |
| **GUEST** | Read items only (default on registration) |

## Running Tests

```bash
pytest --cov=app --cov-report=term
# Open htmlcov/index.html for the HTML coverage report
```

## Project Structure

```text
RoboVault/
├── app/                 # Application source code
├── alembic/             # Database migrations
├── tests/               # Test suite
├── .github/workflows/   # CI/CD pipeline
├── docs/                # Guides and documentation
├── docker-compose.yml   # Container orchestration
├── Dockerfile           # App container image
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Tool configuration (ruff, black, pytest)
└── README.md            # This file
```

## Team

| Member | Role | Contributions |
|--------|------|---------------|
| Member 1 (Engineer 1) | Infrastructure Lead | Project scaffold, Docker, CI/CD, Alembic, database setup |
| Member 2 (Engineer 2) | Backend Developer | Authentication, JWT, RBAC, inventory CRUD, lending workflow |
| Member 3 (Engineer 3) | Documentation & QA | API documentation, README, Swagger polish, test coverage |

## License

Academic project — not for production use.
