# Service Manager

The Service Manager provides a unified interface for managing all CFD Platform services, including background tasks, CFD tools (OpenFOAM, FreeCAD, Gmsh), and AI services.

## Features

- **Service Lifecycle Management**: Start, stop, restart, and monitor services
- **Health Monitoring**: Automatic health checks with configurable intervals
- **Port Management**: Automatic port detection and conflict resolution
- **Process Management**: Track running processes and resource usage
- **WebSocket Updates**: Real-time service status updates to connected clients
- **Auto-start**: Automatically start essential services on application startup

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Service Manager                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Port        │  │ Process     │  │ Health                  │  │
│  │ Detector    │  │ Manager     │  │ Checker                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Service Registry                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ FastAPI  │ │ OpenFOAM │ │ FreeCAD  │ │ Celery   │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### List Services
```
GET /api/v1/service-manager/services
```

### Start a Service
```
POST /api/v1/service-manager/services/{service_name}/start
```

### Stop a Service
```
POST /api/v1/service-manager/services/{service_name}/stop
```

### Restart a Service
```
POST /api/v1/service-manager/services/{service_name}/restart
```

### Check Service Health
```
GET /api/v1/service-manager/services/{service_name}/health
```

### Get Service Logs
```
GET /api/v1/service-manager/services/{service_name}/logs
```

### Start All Auto-start Services
```
POST /api/v1/service-manager/start-all
```

### Stop All Services
```
POST /api/v1/service-manager/stop-all
```

### Get Status Summary
```
GET /api/v1/service-manager/status-summary
```

### WebSocket for Real-time Updates
```
WS /api/v1/service-manager/ws
```

## Service Types

| Type | Description | Default Port |
|------|-------------|--------------|
| FASTAPI | Main API server | 8000 |
| OPENFOAM | CFD solver | - |
| FREECAD | CAD modeler | - |
| GMSH | Mesh generator | - |
| AI_SERVICES | AI inference | 8001 |
| CELERY_WORKER | Background tasks | - |
| REDIS | Cache/Broker | 6379 |
| POSTGRESQL | Database | 5432 |
| WEBSOCKET | WebSocket server | 8000 |

## Service Status

| Status | Description |
|--------|-------------|
| STOPPED | Service is not running |
| STARTING | Service is starting up |
| RUNNING | Service is running normally |
| FAILED | Service failed to start or crashed |
| UNHEALTHY | Service is running but health check failed |
| STOPPING | Service is shutting down |

## Configuration

Services are configured in `backend/infrastructure/service_manager/default_services.py`:

```python
ServiceConfig(
    name="openfoam",
    service_type=ServiceType.OPENFOAM,
    default_port=0,  # No HTTP port needed
    command="bash",
    args=["-c", "source /opt/OpenFOAM/OpenFOAM-dev/etc/bashrc"],
    health_check_path=None,
    auto_start=False,
    start_timeout=5,
    stop_timeout=2,
)
```

## Usage Examples

### Python Client

```python
import httpx

async with httpx.AsyncClient() as client:
    # List all services
    services = await client.get("http://localhost:8000/api/v1/service-manager/services")

    # Start a service
    await client.post("http://localhost:8000/api/v1/service-manager/services/openfoam/start")

    # Check health
    health = await client.get("http://localhost:8000/api/v1/service-manager/services/openfoam/health")
```

### WebSocket Client

```python
import websockets
import json

async def listen():
    async with websockets.connect("ws://localhost:8000/api/v1/service-manager/ws") as ws:
        async for message in ws:
            data = json.loads(message)
            print(f"Service update: {data}")
```

## Integration with Main Application

The Service Manager is automatically initialized when the FastAPI application starts:

```python
# backend/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    service_manager = ServiceManager()
    service_manager.register_default_services()
    service_manager.start_all_auto_start()
    app.state.service_manager = service_manager

    yield

    # Shutdown
    await service_manager.shutdown()
```

## Docker Compose Integration

The Service Manager works seamlessly with Docker Compose:

```bash
# Start all services
docker-compose up -d

# View service manager logs
docker-compose logs -f backend

# Check service health
curl http://localhost:8000/api/v1/service-manager/status-summary
```

## Troubleshooting

### Service Won't Start

1. Check if the port is already in use:
   ```bash
   netstat -an | grep <port>
   ```

2. Check service logs:
   ```bash
   curl http://localhost:8000/api/v1/service-manager/services/<name>/logs
   ```

3. Verify the command exists:
   ```bash
   which <command>
   ```

### Health Check Failing

1. Verify the service is running:
   ```bash
   ps aux | grep <service_name>
   ```

2. Check the health check endpoint manually:
   ```bash
   curl http://localhost:<port>/health
   ```

3. Check service logs for errors

### Port Conflicts

The Service Manager automatically detects port conflicts and can find available ports. To manually check:

```python
from infrastructure.service_manager.services import PortDetector

detector = PortDetector()
available = detector.is_port_available(8000)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SERVICE_MANAGER_AUTO_START | Enable auto-start services | true |
| SERVICE_MANAGER_HEALTH_CHECK_INTERVAL | Health check interval (seconds) | 30 |
| SERVICE_MANAGER_START_TIMEOUT | Service start timeout (seconds) | 60 |
| SERVICE_MANAGER_STOP_TIMEOUT | Service stop timeout (seconds) | 30 |