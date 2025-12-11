#!/bin/bash
# Run database migration for model_comparison_metrics table

echo "🔧 Running database migration..."

# Run the migration SQL inside the Docker container
docker exec bpr-db psql -U admin -d car_prediction -f /migrations/001_add_model_comparison_metrics.sql

echo "✅ Migration complete!"
