"""Startup validation for JWT_SECRET.

Imported by security.py, and run directly by entrypoint.sh before migrations so the
container refuses to start with a clear message:

    python jwt_secret.py
"""
import os
import sys

MIN_LENGTH = 32

# Example values from .env.example, the README, CONTRIBUTING and the wiki, plus common
# placeholders. Compared case-insensitively after trimming whitespace.
PLACEHOLDERS = {
    "changeme",
    "change_me",
    "change-me",
    "changeit",
    "your_long_random_secret_here",
    "dev-secret",
    "secret",
    "jwt_secret",
    "your_jwt_secret",
    "your-secret-key",
}

_HOW_TO_FIX = (
    "Generate a new value with `openssl rand -hex 32`, set it as JWT_SECRET in your .env "
    "file, and restart. Changing it signs out all users, which is expected."
)


def problem(secret: str | None) -> str | None:
    """Return a description of what is wrong with the secret, or None if it is acceptable."""
    if not secret or not secret.strip():
        return "JWT_SECRET is not set. It MUST be set before OpenMTG will start. " + _HOW_TO_FIX
    if secret.strip().lower() in PLACEHOLDERS:
        return ("JWT_SECRET is still set to a placeholder value. It MUST be changed before "
                "OpenMTG will start. " + _HOW_TO_FIX)
    if len(secret) < MIN_LENGTH:
        return (f"JWT_SECRET is only {len(secret)} characters long. It MUST be changed to a "
                f"random value of at least {MIN_LENGTH} characters before OpenMTG will start. "
                + _HOW_TO_FIX)
    return None


def load() -> str:
    """Return JWT_SECRET from the environment, or raise RuntimeError if it is unusable."""
    secret = os.environ.get("JWT_SECRET")
    message = problem(secret)
    if message:
        raise RuntimeError(message)
    return secret


if __name__ == "__main__":
    message = problem(os.environ.get("JWT_SECRET"))
    if message:
        print(f"ERROR: {message}", file=sys.stderr)
        sys.exit(1)
