# ICRRG — Quick Start Guide

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Python** | 3.11 – 3.13 | `python --version` |
| **pip** | 22+ | `pip --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **PostgreSQL** | 15+ | `pg_isready` |
| **Redis** | 7+ | `redis-cli ping` |
| **Git** | 2.30+ | `git --version` |

---

## 0. New Device Setup (After Cloning)

Follow these steps on a fresh machine after cloning the repository.

### Step 1 — Create a Virtual Environment & Install Dependencies

**Windows (PowerShell):**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

**macOS / Linux:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Step 2 — Download spaCy Model

```powershell
python -m spacy download en_core_web_sm
```

### Step 3 — Configure Environment

Create a `.env` file in `backend/` with your database and Redis settings:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/icrrg
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
SECRET_KEY=change-me-to-a-random-string
CORS_ORIGINS=["http://localhost:4200"]
DEBUG=false
```

### Step 4 — Run Database Migrations

```powershell
alembic upgrade head
```

### Step 5 — Seed the Admin User

```powershell
python seed_admin.py
```

> Default admin credentials — username: `admin`, password: `Admin@123`

### Step 6 — Install Frontend Dependencies

```powershell
cd frontend
npm install
```

You're now ready to start the services below.

---

## 1. Start the Services

### Terminal 1 — Backend API

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — Celery Worker

```powershell
cd backend
.\venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

### Terminal 3 — Frontend Dashboard

```powershell
cd frontend
ng serve
```

Dashboard available at: **http://localhost:4200**

---

## 2. Activate the CLI

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -e .
```

Verify CLI is available:

```powershell
icrrg --help
```

---

## 3. Register & Login

Authentication is required before scanning. Register a new account or log in with existing credentials.

### Register a new user

```powershell
icrrg register
```

You will be prompted for a **username** and **password** (with confirmation).

### Log in

```powershell
icrrg login
```

Enter your credentials when prompted. The CLI stores your token locally so subsequent commands are authenticated automatically.

### Log out

```powershell
icrrg logout
```

> **Note:** A default admin account is pre-seeded — username: `admin`, password: `Admin@123`.

---

## 4. Install Hook on Any Project

```powershell
cd C:\path\to\your\project
icrrg install
```

Output:

```
Pre-commit hook installed → C:\path\to\your\project\.git\hooks\pre-commit
API endpoint: http://localhost:8000
```

---

## 5. Normal Workflow (Automatic)

```powershell
# Make changes to your code
git add .
git commit -m "your commit message"
```

The hook automatically:
1. Grabs `git diff --cached` (staged changes)
2. Sends it to the ICRRG API for scanning
3. Prints color-coded findings in the terminal
4. **Blocks the commit** if critical or high severity findings are found

### Example — Commit Blocked

```
[!] 4 finding(s) - risk score: 10.0/10
   BLOCK  [HIGH] secret:password-assignment — config.py:5
    Hardcoded password or secret detected
   BLOCK  [CRITICAL] secret:private-key-header — config.py:8
    Private key header detected
   BLOCK  [CRITICAL] phi:ssn — config.py:10
    SSN detected
   BLOCK  [HIGH] phi:person-name — config.py:13
    Person name detected in healthcare context
  scan completed in 3.58s
COMMIT BLOCKED: 2 high, 2 critical finding(s).
```

### Example — Commit Allowed

```
[OK] No issues found.
  scan completed in 2.58s
[master abc1234] your commit message
```

---

## 6. Manual Scan (Without Committing)

```powershell
git add .
icrrg scan
```

---

## 7. Uninstall Hook

```powershell
cd C:\path\to\your\project
icrrg uninstall
```

---

## Key Notes

| Topic | Detail |
|-------|--------|
| **Authentication required** | You must `icrrg login` before scanning — unauthenticated scans are rejected |
| **Backend down?** | Hook allows the commit gracefully — developers are never blocked by infra issues |
| **Test files skipped** | Files named `test_*`, `*_test.py`, `**/fixtures/**` are excluded to reduce false positives |
| **Configurable thresholds** | Place a `.icrrg.yml` in the repo root to customize which severities block commits |
| **Cached scans** | Amend commits with identical diffs skip re-scanning |
| **Rebase / merge** | Hook auto-skips during rebase and merge operations |
| **Dashboard** | View all scan results, charts, and metrics at `http://localhost:4200` |

---

## .icrrg.yml Example (Optional)

```yaml
blocking:
  critical: block
  high: block
  medium: warn
  low: info
```
