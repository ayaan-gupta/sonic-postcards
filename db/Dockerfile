# Postgres 16 with both pgvector and PostGIS.
# The pgvector image ships the vector extension; PostGIS comes from the PGDG
# apt repository that image is already configured with.
FROM pgvector/pgvector:pg16

RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-postgis-3 postgresql-16-postgis-3-scripts \
 && rm -rf /var/lib/apt/lists/*

# Extensions are created by the API's first migration, so the image stays generic.
