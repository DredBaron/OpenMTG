#!/bin/sh
set -e
cd /app
alembic upgrade head
exec /usr/bin/supervisord -n -c /etc/supervisord.conf
