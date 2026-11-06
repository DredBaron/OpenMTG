"""Size and rate limits for pasted card-list imports (collection and deck).

Every card line can cost a Scryfall lookup through the shared, rate-limited Scryfall queue, so a
single huge import, or many imports in a row, would delay card lookups for every user.
Keep MAX_IMPORT_LINES in step with frontend/src/constants.js.
"""
from fastapi import HTTPException

MAX_IMPORT_LINES = 1000
# Room for 1000 lines of even the longest card names; stops a huge paste with few line breaks.
MAX_IMPORT_CHARS = 200_000
# Per user, shared by collection and deck imports.
IMPORT_RATE_LIMIT = "5/minute;30/hour"


def import_lines(list_text: str) -> list[str]:
    """The stripped lines of an import that carry content (blank lines and # comments dropped).

    Raises a 400 if the import is over the limits."""
    too_many = (f"Imports are limited to {MAX_IMPORT_LINES} lines at a time "
                "(blank lines and # comments don't count). Split the list into smaller imports.")
    if len(list_text) > MAX_IMPORT_CHARS:
        raise HTTPException(status_code=400, detail=too_many)
    lines = [line.strip() for line in list_text.strip().splitlines()]
    lines = [line for line in lines if line and not line.startswith("#")]
    if len(lines) > MAX_IMPORT_LINES:
        raise HTTPException(status_code=400, detail=too_many)
    return lines
