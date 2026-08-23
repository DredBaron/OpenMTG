#!/bin/sh
set -e
cd /app

LOCK_FILE="${CONFIG_PATH:-/config}/db_backend.lock"
case "$DATABASE_URL" in
  sqlite*) CURRENT_BACKEND=sqlite ;;
  *) CURRENT_BACKEND=postgresql ;;
esac

if [ -f "$LOCK_FILE" ]; then
  LOCKED_BACKEND=$(cat "$LOCK_FILE")
  if [ "$LOCKED_BACKEND" != "$CURRENT_BACKEND" ]; then
    echo "ERROR: This instance was set up with '$LOCKED_BACKEND' but DATABASE_URL now points to '$CURRENT_BACKEND'." >&2
    echo "Switching database backends after setup is not supported. Restore DATABASE_URL to '$LOCKED_BACKEND', or start a fresh instance." >&2
    exit 1
  fi
fi

mkdir -p /data/uploads/card_photos
mkdir -p /data/trades
mkdir -p /data/db
alembic upgrade head
alembic -c alembic_trades.ini upgrade head
exec /usr/bin/supervisord -n -c /etc/supervisord.conf
