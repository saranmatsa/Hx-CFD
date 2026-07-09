#!/bin/bash
# Quick start script for CFD Platform

set -e

echo "🚀 CFD Platform - Quick Start"
echo "=============================="
echo ""

# Step 1: Build frontend
echo "📦 Building frontend..."
cd frontend
npm install
npm run build
cd ..
echo "✓ Frontend built successfully"
echo ""

# Step 2: Start Docker services
echo "🐳 Starting Docker services..."
docker compose up -d
echo "✓ Services started"
echo ""

# Step 3: Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if docker compose exec -T postgres pg_isready -U cfd_user &>/dev/null; then
    echo "✓ PostgreSQL is ready"
    break
  fi
  attempt=$((attempt + 1))
  if [ $attempt -eq $max_attempts ]; then
    echo "✗ PostgreSQL failed to start"
    exit 1
  fi
  sleep 1
done

echo ""
echo "================================"
echo "✓ CFD Platform is ready!"
echo "================================"
echo ""
echo "📍 Access the application:"
echo "   http://localhost:3000"
echo ""
echo "🔐 Next steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Go to Settings (⚙️ icon)"
echo "   3. Add your AI provider (OpenAI, Anthropic, Ollama, etc.)"
echo "   4. Paste your API key and test the connection"
echo ""
echo "📊 Monitoring:"
echo "   - Flower (Celery tasks): http://localhost:5555"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "⚠️  To stop services: docker compose down"
echo ""
