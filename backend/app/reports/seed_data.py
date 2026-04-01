"""Seed the database with realistic mock scan data for report testing.

Usage:  poetry run python -m app.reports.seed_data
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding

# ---------------------------------------------------------------------------
# Realistic sample data
# ---------------------------------------------------------------------------

REPOS = ["acme-webapp", "acme-webapp"]

FILES = [
    "src/auth/login.py",
    "src/auth/jwt_utils.py",
    "src/api/users.py",
    "src/api/payments.py",
    "src/config/settings.py",
    "src/db/migrations/002_add_users.sql",
    "src/utils/crypto.py",
    "src/services/email_service.py",
    "src/services/notification.py",
    "src/middleware/cors.py",
    "tests/test_auth.py",
    "docker-compose.yml",
    ".env.example",
    "src/api/health.py",
    "src/models/user.py",
]

FINDING_TEMPLATES = [
    # (finding_type, severity, message_template)
    ("secret:aws_access_key", "critical", "AWS Access Key ID found in source code"),
    ("secret:github_token", "critical", "GitHub Personal Access Token exposed"),
    ("secret:generic_api_key", "high", "Generic API key detected in configuration"),
    ("secret:private_key", "critical", "Private key material found in commit"),
    ("secret:password_in_url", "high", "Password embedded in database connection URL"),
    ("entropy:high_entropy_string", "medium", "High-entropy string may be a secret"),
    ("entropy:base64_blob", "medium", "Base64-encoded blob with high entropy detected"),
    ("phi:email_address", "medium", "Email address (PII) found in source code"),
    ("phi:phone_number", "medium", "Phone number (PII) detected"),
    ("phi:ssn", "high", "Possible SSN pattern detected"),
    ("phi:ip_address", "low", "Hardcoded IP address found"),
    ("review:sql_injection", "critical", "Potential SQL injection via string concatenation"),
    ("review:xss", "high", "Unsanitized user input rendered in template"),
    ("review:insecure_hash", "medium", "MD5 used for password hashing — use bcrypt"),
    ("review:hardcoded_secret", "high", "Hardcoded credentials in application code"),
    ("review:missing_auth", "high", "Endpoint missing authentication decorator"),
    ("review:open_redirect", "medium", "User-controlled redirect URL without validation"),
    ("review:path_traversal", "high", "File path constructed from user input"),
    ("review:weak_crypto", "medium", "Weak cryptographic algorithm (DES) in use"),
    ("review:logging_sensitive", "medium", "Sensitive data written to log output"),
]

SEVERITY_WEIGHT = {"critical": 10.0, "high": 7.0, "medium": 4.0, "low": 1.0}


def _risk_score(findings: list[dict]) -> float:
    total = sum(SEVERITY_WEIGHT.get(f["severity"], 1.0) for f in findings)
    return min(10.0, round(total, 2))


async def seed(num_scans: int = 40) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    base_time = datetime.now(timezone.utc) - timedelta(days=14)

    async with session_factory() as session:
        for i in range(num_scans):
            repo = random.choice(REPOS)
            commit_hash = uuid.uuid4().hex[:40]
            created_at = base_time + timedelta(
                hours=random.randint(0, 14 * 24),
                minutes=random.randint(0, 59),
            )

            # 1-6 findings per scan
            num_findings = random.randint(1, 6)
            chosen = random.sample(
                FINDING_TEMPLATES, min(num_findings, len(FINDING_TEMPLATES))
            )

            findings_data = []
            for ft, sev, msg in chosen:
                file_path = random.choice(FILES)
                findings_data.append(
                    {
                        "finding_type": ft,
                        "severity": sev,
                        "message": f"{msg} — matched_text_sample_{random.randint(100,999)}",
                        "file_path": file_path,
                        "line_number": random.randint(1, 300),
                        "confidence": round(random.uniform(0.6, 1.0), 2),
                    }
                )

            scan = Scan(
                repository=repo,
                commit_hash=commit_hash,
                status="completed",
                risk_score=_risk_score(findings_data),
                created_at=created_at,
            )
            session.add(scan)
            await session.flush()

            for fd in findings_data:
                session.add(ScanFinding(scan_id=scan.id, **fd))

        await session.commit()

    await engine.dispose()
    print(f"Seeded {num_scans} scans with findings.")


if __name__ == "__main__":
    asyncio.run(seed())
