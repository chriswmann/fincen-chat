#!/bin/bash
set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "Creating data folder..."
mkdir -vp data/neo4j

echo "Ensuring Neo4j container is running..."
docker compose up -d

echo "Waiting for Neo4j to be ready (this may take a few moments)..."
# Wait until cypher-shell can successfully execute a simple test query
until docker compose exec neo4j cypher-shell -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" "RETURN 1;" > /dev/null 2>&1; do
  sleep 2
done

echo "Neo4j is ready! Loading FinCEN data from local CSV files..."
cat scripts/fincen_csv.cypher | docker compose exec -T neo4j cypher-shell -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD"

echo "Data loaded successfully!"
