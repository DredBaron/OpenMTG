from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

_trades_path = os.environ.get("TRADES_PATH", "/data/trades")
TRADES_DATABASE_URL = os.environ.get(
    "TRADES_DATABASE_URL",
    f"sqlite:///{os.path.join(_trades_path, 'trades.db')}",
)

connect_args = {"check_same_thread": False} if TRADES_DATABASE_URL.startswith("sqlite") else {}

trades_engine = create_engine(TRADES_DATABASE_URL, connect_args=connect_args)

TradesSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=trades_engine)

TradesBase = declarative_base()

def get_trades_db():
    db = TradesSessionLocal()
    try:
        yield db
    finally:
        db.close()
