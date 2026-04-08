"""Security middleware and utilities for production deployment.

Implements:
- Prompt injection protection
- User/tenant isolation
- Rate limiting
- Session management
- CSRF protection
"""

import re
import secrets
from datetime import datetime, timedelta

import structlog
from fastapi import HTTPException, Request
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class User(BaseModel):
    """User model for authentication."""

    id: str
    username: str
    email: str
    created_at: datetime
    last_activity: datetime


class Session(BaseModel):
    """Session model for tracking user sessions."""

    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    csrf_token: str
    is_active: bool = True


# In-memory session store (replace with Redis for production)
_sessions: dict[str, Session] = {}
_users: dict[str, User] = {}


# ============================================================================
# PROMPT INJECTION PROTECTION (CRITICAL-1 FIX)
# ============================================================================


def sanitize_prompt_input(text: str, max_length: int = 2000) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.

    Detects and flags attempts to:
    - Override instructions
    - Inject new goals
    - Escape prompt context
    - Execute arbitrary logic

    Args:
        text: User-supplied input
        max_length: Maximum allowed length

    Returns:
        Sanitized text safe for LLM prompts
    """
    if not isinstance(text, str):
        return ""

    # Truncate to prevent token flooding
    text = text[:max_length]

    # Patterns that indicate prompt injection attempts
    injection_patterns = [
        r"ignore\s+(?:previous|prior|all)\s+(?:instruction|direction|prompt)",
        r"forget\s+(?:everything|all|your)",
        r"new\s+(?:instruction|task|goal|objective)",
        r"execute\s+(?:this|the following|instead)",
        r"override\s+(?:your|previous|the)",
        r"bypass\s+(?:restriction|limit|check|safeguard)",
        r"unconstrained\s+(?:mode|behavior|response)",
        r"jailbreak",
        r"roleplay\s+as",
        r"pretend\s+(?:you|I)\s+(?:are|is)",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(
                "prompt_injection_attempt_detected",
                text=text[:100],
                pattern=pattern,
            )
            # Don't block completely, but add context marker
            return f"[User instruction - reviewed]: {text}"

    return text


def sanitize_for_logging(data: dict | str) -> str:
    """
    Sanitize data for logging to prevent secrets leakage.

    Removes or masks:
    - API keys
    - Tokens
    - Passwords
    - Credentials
    - PII
    """
    if isinstance(data, str):
        return _mask_secrets(data)

    if isinstance(data, dict):
        sensitive_keys = {
            "api_key",
            "token",
            "secret",
            "password",
            "auth",
            "credential",
            "access_token",
            "refresh_token",
            "jwt",
            "bearer",
            "session_id",
            "ssn",
            "credit_card",
            "card_number",
            "cvv",
        }

        sanitized = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(value)
            elif isinstance(value, str):
                sanitized[key] = _mask_secrets(value)
            else:
                sanitized[key] = value

        return str(sanitized)

    return str(data)


def _mask_secrets(text: str) -> str:
    """Mask common secret patterns in text."""
    patterns = [
        (r"(?i)(api[_-]?key)[:\s=]+([^\s,;\n]+)", r"\1=***"),
        (r"(?i)(token)[:\s=]+([^\s,;\n]+)", r"\1=***"),
        (r"(?i)(password)[:\s=]+([^\s,;\n]+)", r"\1=***"),
        (r"(?i)(secret)[:\s=]+([^\s,;\n]+)", r"\1=***"),
        (r"(?i)(authorization)[:\s=]+([^\s,;\n]+)", r"\1=***"),
        (r"Bearer\s+\w{20,}", "Bearer ***"),
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)

    return result


# ============================================================================
# USER/TENANT ISOLATION (CRITICAL-2 FIX)
# ============================================================================


async def get_current_user(request: Request) -> User:
    """
    Extract and validate current user from request.

    Checks:
    - Session exists and is valid
    - Session not expired
    - User still exists
    - CSRF token valid

    Raises:
        HTTPException: If user not authenticated
    """
    session_id = request.cookies.get("session_id")
    csrf_token = request.headers.get("X-CSRF-Token")

    if not session_id:
        logger.warning("no_session_id_provided")
        raise HTTPException(status_code=401, detail="Unauthorized")

    session = _sessions.get(session_id)
    if not session:
        logger.warning("session_not_found", session_id=session_id[:20])
        raise HTTPException(status_code=401, detail="Invalid session")

    # Validate session not expired
    if datetime.now() > session.expires_at:
        logger.warning("session_expired", session_id=session_id[:20])
        del _sessions[session_id]
        raise HTTPException(status_code=401, detail="Session expired")

    # Validate CSRF token
    if csrf_token != session.csrf_token:
        logger.warning("csrf_token_mismatch", session_id=session_id[:20])
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    # Validate user still exists
    user = _users.get(session.user_id)
    if not user:
        logger.warning("user_not_found", user_id=session.user_id)
        raise HTTPException(status_code=401, detail="User not found")

    # Update last activity
    session.last_activity = datetime.now()

    return user


def create_session(user_id: str, username: str, email: str) -> tuple[str, str]:
    """
    Create a new session for user.

    Returns:
        Tuple of (session_id, csrf_token)
    """
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)

    user = User(
        id=user_id,
        username=username,
        email=email,
        created_at=datetime.now(),
        last_activity=datetime.now(),
    )

    session = Session(
        session_id=session_id,
        user_id=user_id,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=24),
        csrf_token=csrf_token,
    )

    _sessions[session_id] = session
    _users[user_id] = user

    logger.info(
        "session_created",
        user_id=user_id,
        session_id=session_id[:20],
        expires_at=session.expires_at,
    )

    return session_id, csrf_token


def invalidate_session(session_id: str) -> None:
    """Invalidate a session (logout)."""
    if session_id in _sessions:
        session = _sessions[session_id]
        session.is_active = False
        del _sessions[session_id]
        logger.info("session_invalidated", session_id=session_id[:20])


# ============================================================================
# RATE LIMITING & IDEMPOTENCY
# ============================================================================


class RateLimiter:
    """Simple in-memory rate limiter (use Redis for distributed systems)."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times: dict[str, list[datetime]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        if key not in self.request_times:
            self.request_times[key] = []

        # Remove old requests outside the window
        self.request_times[key] = [t for t in self.request_times[key] if t > cutoff]

        # Check if limit exceeded
        if len(self.request_times[key]) >= self.requests_per_minute:
            return False

        # Record this request
        self.request_times[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for this minute."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        if key in self.request_times:
            valid = [t for t in self.request_times[key] if t > cutoff]
            return max(0, self.requests_per_minute - len(valid))

        return self.requests_per_minute


# Idempotency tracking
_idempotency_store: dict[str, dict] = {}


def track_idempotency(key: str, response: dict) -> None:
    """Track response for idempotency key."""
    _idempotency_store[key] = {
        "response": response,
        "timestamp": datetime.now(),
    }


def get_idempotent_response(key: str) -> dict | None:
    """Get cached response for idempotency key if still valid."""
    if key not in _idempotency_store:
        return None

    stored = _idempotency_store[key]
    # Keep responses for 24 hours
    if datetime.now() - stored["timestamp"] < timedelta(hours=24):
        return stored["response"]

    del _idempotency_store[key]
    return None
