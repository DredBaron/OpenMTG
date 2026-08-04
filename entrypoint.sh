#!/bin/sh
set -e
cd /app
mkdir -p /data/uploads/card_photos
mkdir -p /data/trades
alembic upgrade head
alembic -c alembic_trades.ini upgrade head
exec /usr/bin/supervisord -n -c /etc/supervisord.conf
