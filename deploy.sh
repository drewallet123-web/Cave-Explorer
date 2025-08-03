#!/bin/bash

set -e

echo "🚀 Starting Cave Explorer deployment..."

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | xargs)
fi

# Build and deploy
echo "📦 Building containers..."
docker-compose down
docker-compose build --no-cache

echo "🔄 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Health checks
echo "🏥 Checking backend health..."
curl -f http://localhost:8000/health || exit 1

echo "🏥 Checking frontend health..."
curl -f http://localhost/ || exit 1

echo "✅ Deployment successful!"
echo "🌐 Frontend: http://localhost"
echo "🔧 API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"

# Show running containers
echo "📋 Running containers:"
docker-compose ps