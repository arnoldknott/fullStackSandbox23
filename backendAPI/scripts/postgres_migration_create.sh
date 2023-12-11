#!/bin/sh

# apk add --no-cache git
mkdir -P /data/migrations/stage_prod/versions
cd /app/src
alembic -c alembic_stage_prod.ini  revision --autogenerate -m \"$COMMIT_SHA\" > alembic_revision.log
MIGRATION_SCRIPT_FILENAME=$(cat alembic_revision.log | awk '/Generating /{print $2}')
mv $MIGRATION_SCRIPT_FILENAME /data/migrations/stage_prod/versions
mv alembic_revision.log /data/migrations/stage_prod/logs
# Leave those outputs as they are, as the runer picks up the echo and recreates the file for pull request:
cat $MIGRATION_SCRIPT_FILENAME
echo $MIGRATION_SCRIPT_FILENAME

# apk del git
# docker compose run -T --rm backend_api sh -c "alembic revision --autogenerate -m \"$1\"