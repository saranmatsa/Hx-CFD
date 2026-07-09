# CFD Platform - Browser-Based Provider Setup

## TL;DR

```bash
# 1. Install frontend
npm install && npm run build

# 2. Start services
docker compose up -d

# 3. Open browser
http://localhost:3000

# 4. Add AI provider via Settings page (no .env needed)
```

That's it. API keys are entered through the browser UI, not environment variables.

## Key Features

- ✅ **No .env files for API keys** - Everything configured in browser
- ✅ **Secure local storage** - Keys encrypted and stored only in browser
- ✅ **Easy provider management** - Add/edit/delete providers anytime via Settings
- ✅ **Works offline** - Keys persisted locally after first setup
- ✅ **Multi-provider support** - OpenAI, Anthropic, Ollama, Groq, Gemini, and more

## File Structure

```
cfd-platform/
├── docker-compose.yml          # No API keys here anymore
├── .env.example                # Optional DB credentials only
├── frontend/
│   └── src/
│       ├── App.tsx             # Added /settings route
│       ├── pages/
│       │   ├── SetupPage.ts     # Initial provider selection
│       │   └── SettingsPage.ts  # Runtime provider management (NEW)
│       └── store/
│           └── providerStore.ts # Manages providers in local storage
├── start.sh / start.bat         # Quick start scripts
├── INSTALLATION.md              # Full setup guide
└── SETUP_COMPLETE.md            # What changed
```

## How It Works

1. **First Visit**: User redirected to Setup page
2. **Select Provider**: Choose OpenAI, Anthropic, Ollama, etc.
3. **Enter Credentials**: Paste API key directly into form
4. **Test & Save**: Verify connection works, then save locally
5. **Ongoing**: Access Settings (⚙️) anytime to manage providers

All keys stored encrypted in browser local storage. Server only handles business logic.

## API Providers Supported

| Provider | Type | Requires Key? | Setup URL |
|----------|------|---------------|-----------|
| OpenAI | Cloud | Yes | https://platform.openai.com/api-keys |
| Anthropic | Cloud | Yes | https://console.anthropic.com/account/keys |
| Google Gemini | Cloud | Yes | https://makersuite.google.com/app/apikey |
| Groq | Cloud | Yes | https://console.groq.com/keys |
| Ollama | Local | No | http://localhost:11434 |
| LM Studio | Local | No | http://localhost:1234 |
| Custom | Any | Varies | User-provided URL |

## Common Tasks

### Add a provider
1. Settings → AI Providers → "+ Add Provider"
2. Select provider type
3. Paste API key
4. Test connection
5. Save

### Change default provider
1. Settings → AI Providers
2. Click "Set Default" on a provider

### Delete a provider
1. Settings → AI Providers
2. Click "Delete" button (will prompt for confirmation)

### Reset everything
1. Open DevTools (F12)
2. Application → Local Storage
3. Delete `provider-storage` entry
4. Refresh page (returns to Setup)

## Troubleshooting

### "Provider form won't show"
- Clear browser cache (Ctrl+Shift+Delete)
- Check browser console (F12 → Console)

### "Connection test failed"
- Verify API key is correct (check provider's dashboard)
- Check internet connection
- Try with a local provider (Ollama) to test connectivity

### "Port 3000 already in use"
Edit `docker-compose.yml`:
```yaml
ports:
  - "3001:5173"  # Changed from 3000:5173
```

### "Need to re-enter keys"
- Keys are stored in browser local storage
- They persist until you clear browser data
- Use separate browser profiles for different setups

## Docker Services

| Service | Port | Purpose | Notes |
|---------|------|---------|-------|
| Frontend | 3000 | React UI | Static site after build |
| Backend | 8000 | REST API | Uses keys from browser |
| PostgreSQL | 5432 | Database | No credentials needed |
| Redis | 6379 | Cache | Internal use |
| Flower | 5555 | Monitoring | Task queue viewer |

## Environment Variables (Optional)

Only needed for advanced configuration. Not needed for basic setup:

```bash
# Database (defaults provided)
POSTGRES_USER=cfd_user
POSTGRES_PASSWORD=cfd_password
POSTGRES_DB=cfd_platform

# Service ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
FLOWER_PORT=5555
```

All **API keys** are now managed exclusively through the browser Settings page.

## Security Model

```
Browser Local Storage (Encrypted)
    └── providerStore (Zustand)
        └── SettingsPage UI
            └── User adds/edits/deletes providers
```

- ✅ Keys never stored in Docker
- ✅ Keys never in environment variables  
- ✅ Keys never sent in REST requests (only used client-side for auth)
- ✅ Encrypted with machine-specific key
- ✅ Survives browser restarts
- ✅ Lost if browser data cleared (by design)

## Next Steps

- Read `INSTALLATION.md` for detailed setup guide
- Check `SETUP_COMPLETE.md` for what changed
- Run `./start.sh` (Linux/macOS) or `start.bat` (Windows) to get going

---

**Status:** ✅ Ready to deploy. No .env configuration needed for API keys.
