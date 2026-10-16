import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def user_or_ip_key(request: Request) -> str:
    """Rate-limit key for authenticated endpoints: the token's username, else the client IP.

    Per-user keys stop one account from spreading requests across addresses, and keep users who
    share an address (same LAN, same reverse proxy) from using up each other's allowance. slowapi
    checks limits after FastAPI has resolved the endpoint's dependencies, so on endpoints that
    require login the token has already been verified by the time this runs."""
    from security import ALGORITHM, SECRET_KEY  # imported here: security pulls in the database

    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            sub = jwt.decode(token.strip(), SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        except jwt.PyJWTError:
            sub = None
        if isinstance(sub, str) and sub:
            return f"user:{sub}"
    return f"ip:{get_remote_address(request)}"
