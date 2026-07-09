# CFD Platform - Installation & Setup Guide

## Quick Start (No Environment Variables)

The CFD Platform is designed to work without requiring any environment variable configuration. API keys are managed entirely through the browser UI.

### Prerequisites
- Docker & Docker Compose installed
- Node.js 18+ and npm installed
- Git

### Step 1: Clone & Install Frontend

```bash
cd frontend
npm install
npm run build
```

The frontend will be built as a production-ready static site.

### Step 2: Start Services with Docker Compose

```bash
cd ..
docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Frontend (port 3000)
- Worker services (Celery, Flower on port 5555)

### Step 3: Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

You'll be presented with the Setup page.

### Step 4: Add API Providers

1. **Select a Provider**: Click on an AI provider (OpenAI, Anthropic, Ollama, etc.)
2. **Enter Your API Key**: Paste your API key directly into the form
3. **Configure Settings**: Set model name, temperature, and other preferences
4. **Test Connection**: Click "Test Connection" to verify your setup
5. **Save Provider**: Click "Save Provider" to store it securely

Your API keys are:
- Stored **only in your browser's local storage** (not sent to server)
- Encrypted using a machine-specific key
- **Never** stored in environment variables or Docker containers

### Step 5: Manage Providers Anytime

After setup, access provider settings:
1. Click the **⚙️ Settings** icon in the navigation
2. View all configured providers
3. Add new providers, edit existing ones, or delete providers
4. Set a default provider

## API Key Security

✓ Keys stored only in browser local storage  
✓ Encrypted with machine-specific key  
✓ No keys in environment variables  
✓ No keys in Docker containers  
✓ No keys persisted to server  

## Available Providers

### Cloud Providers (Require API Key)
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude 3, Claude Opus
- **Google Gemini**: Gemini Pro
- **Groq**: LLaMA 2, Mixtral
- **NVIDIA NIM**: Enterprise LLMs
- **OpenRouter**: Multi-model aggregator

### Local Providers (No API Key Needed)
- **Ollama**: Run models locally (http://localhost:11434)
- **LM Studio**: Desktop LLM runner (http://localhost:1234)
- **Custom**: Point to any OpenAI-compatible API

## Docker Compose Services

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | Web UI |
| Backend | 8000 | REST API |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache & Message Broker |
| Flower | 5555 | Celery Monitoring |

## Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs -f backend

# Restart services
docker compose down
docker compose up -d
```

### Can't connect to providers
1. Verify your API key is correct
2. Check internet connection
3. Use "Test Connection" button to debug

### Port conflicts
Edit `docker-compose.yml` to change port mappings:
```yaml
ports:
  - "3001:5173"  # Change frontend to port 3001
```

### Clear all provider data
To reset provider configuration:
- Open browser DevTools (F12)
- Go to Application → Local Storage
- Delete the `provider-storage` entry
- Refresh the page

## Next Steps

1. **Upload Project**: Use Upload page to import CFD meshes
2. **Create Simulation**: Define simulation parameters
3. **Monitor Runs**: Track execution with Flower dashboard
4. **View Results**: Analyze results with 3D visualization

## For Production

For production deployment:
1. Create separate `docker-compose.prod.yml` with appropriate resource limits
2. Use a reverse proxy (nginx, Traefik) for SSL/TLS
3. Configure persistent volumes for data backup
4. Set up monitoring and logging aggregation
5. Use Docker secrets for sensitive credentials

## Support

For issues or questions, check:
- Docker Compose logs: `docker compose logs <service-name>`
- Browser console: F12 → Console tab
- Settings page for provider diagnostics
