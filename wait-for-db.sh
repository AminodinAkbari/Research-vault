#!/bin/sh
# wait-for-db.sh – retry until the db hostname resolves

echo "Waiting for database hostname 'db' to be resolvable..."

until getent hosts db > /dev/null 2>&1; do
  echo "DNS not ready yet – retrying in 2s..."
  sleep 2
done

echo "Database hostname resolved. Starting application..."
exec "$@"