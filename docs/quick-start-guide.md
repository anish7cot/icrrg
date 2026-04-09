# ICRRG — Quick Start Guide

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Python** | 3.11 – 3.13 | `python --version` |
| **Poetry** | 1.8+ | `poetry --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **PostgreSQL** | 15+ | `pg_isready` |
| **Redis** | 7+ | `redis-cli ping` |
| **Git** | 2.30+ | `git --version` |

---

## 0. New Device Setup (After Cloning)

Follow these steps on a fresh machine after cloning the repository.

### Step 1 — Install Poetry (if not installed)

**Windows (PowerShell):**

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

**macOS / Linux:**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Then add Poetry to your PATH:

- **Windows:** Add `%APPDATA%\Python\Scripts` to your system PATH, or run:
  ```powershell
  $env:Path += ";$env:APPDATA\Python\Scripts"
  ```
- **macOS / Linux:** Add `$HOME/.local/bin` to your shell profile (`~/.bashrc` or `~/.zshrc`):
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  ```

Verify: `poetry --version`

### Step 2 — Install Backend Dependencies

```powershell
cd backend
poetry install
```

This creates a virtual environment and installs all Python packages.

### Step 3 — Install Frontend Dependencies

```powershell
cd frontend
npm install
```

### Step 4 — Configure Environment

Create a `.env` file in `backend/` with your database and Redis settings:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/icrrg
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

### Step 5 — Run Database Migrations

```powershell
cd backend
poetry run alembic upgrade head
```

### Step 6 — Seed the Admin User

```powershell
cd backend
poetry run python seed_admin.py
```

> Default admin credentials — username: `admin`, password: `Admin@123`

### Step 7 — Download spaCy Model

```powershell
cd backend
poetry run python -m spacy download en_core_web_sm
```

You're now ready to start the services below.

---

## 1. Start the Services

### Terminal 1 — Backend API

```powershell
cd C:\Users\anish.neupane\Desktop\Hackathon\backend
poetry run uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — Frontend Dashboard (optional)

```powershell
cd C:\Users\anish.neupane\Desktop\Hackathon\frontend
npm start
```

Dashboard available at: **http://localhost:4200**

---

## 2. Activate the CLI

```powershell
cd C:\Users\anish.neupane\Desktop\Hackathon\backend
& "C:\Users\anish.neupane\AppData\Local\pypoetry\Cache\virtualenvs\backend-HYhMOmpw-py3.13\Scripts\Activate.ps1"
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
