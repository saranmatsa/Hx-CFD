/**
 * Main Application Entry Point
 * Integrates all backend services for the CFD Platform
 */

import express, { Express, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { createServer } from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import { AnalysisOrchestrator } from './services/analysisOrchestrator';
import { getPluginManager } from './services/pluginManager';
import { getResultCache, getMeshCache, getFieldCache } from './services/cacheManager';

interface WSClient {
  id: string;
  socket: WebSocket;
  subscriptions: Set<string>;
}

class CFDPlatformServer {
  private app: Express;
  private server: ReturnType<typeof createServer>;
  private wss: WebSocketServer;
  private orchestrator: AnalysisOrchestrator;
  private clients: Map<string, WSClient> = new Map();
  private clientIdCounter = 0;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.wss = new WebSocketServer({ server: this.server });
    this.orchestrator = new AnalysisOrchestrator();

    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSocket();
    this.setupOrchestratorEvents();
  }

  private setupMiddleware() {
    // Security
    this.app.use(helmet({
      contentSecurityPolicy: false,
      crossOriginEmbedderPolicy: false
    }));

    // CORS
    this.app.use(cors({
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:5173'],
      credentials: true
    }));

    // Body parsing
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

    // Request logging
    this.app.use((req: Request, _res: Response, next: NextFunction) => {
      console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
      next();
    });
  }

  private setupRoutes() {
    // Health check
    this.app.get('/api/health', (_req: Request, res: Response) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        uptime: process.uptime()
      });
    });

    // Analysis endpoints
    this.app.post('/api/analysis', async (req: Request, res: Response) => {
      try {
        const { parameters, fidelity, options } = req.body;
        
        if (!parameters) {
          return res.status(400).json({ error: 'Parameters required' });
        }

        const result = await this.orchestrator.analyze(parameters, fidelity, options);
        res.json(result);
      } catch (error) {
        console.error('Analysis error:', error);
        res.status(500).json({ 
          error: 'Analysis failed',
          message: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    // Batch analysis
    this.app.post('/api/analysis/batch', async (req: Request, res: Response) => {
      try {
        const { requests } = req.body;
        
        if (!Array.isArray(requests)) {
          return res.status(400).json({ error: 'Requests array required' });
        }

        const results = await Promise.all(
          requests.map((r: any) => 
            this.orchestrator.analyze(r.parameters, r.fidelity, r.options)
          )
        );

        res.json({ results });
      } catch (error) {
        console.error('Batch analysis error:', error);
        res.status(500).json({ 
          error: 'Batch analysis failed',
          message: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    // Parameter study
    this.app.post('/api/analysis/study', async (req: Request, res: Response) => {
      try {
        const { parameter, range, fidelity, options } = req.body;
        
        if (!parameter || !range || !Array.isArray(range)) {
          return res.status(400).json({ error: 'Parameter and range array required' });
        }

        const results = await this.orchestrator.parameterStudy(
          parameter,
          range,
          fidelity || 'instant',
          options
        );

        res.json({ results });
      } catch (error) {
        console.error('Parameter study error:', error);
        res.status(500).json({ 
          error: 'Parameter study failed',
          message: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    // Plugin management
    this.app.get('/api/plugins', (_req: Request, res: Response) => {
      const pluginManager = getPluginManager();
      res.json({
        plugins: pluginManager.getAll().map(p => ({
          id: p.id,
          name: p.name,
          version: p.version,
          category: p.category,
          capabilities: p.capabilities,
          parameters: p.parameters
        })),
        info: pluginManager.getAllInfo()
      });
    });

    this.app.post('/api/plugins/:id/execute', async (req: Request, res: Response) => {
      try {
        const { id } = req.params;
        const { parameters, geometry, options } = req.body;

        const pluginManager = getPluginManager();
        const result = await pluginManager.execute({
          id: `req-${Date.now()}`,
          pluginId: id,
          parameters,
          geometry,
          options
        });

        res.json(result);
      } catch (error) {
        console.error('Plugin execution error:', error);
        res.status(500).json({ 
          error: 'Plugin execution failed',
          message: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    // Cache management
    this.app.get('/api/cache/stats', (_req: Request, res: Response) => {
      res.json({
        result: getResultCache().getStats(),
        mesh: getMeshCache().getStats(),
        field: getFieldCache().getStats()
      });
    });

    this.app.delete('/api/cache', (_req: Request, res: Response) => {
      getResultCache().clear();
      getMeshCache().clear();
      getFieldCache().clear();
      res.json({ success: true, message: 'Cache cleared' });
    });

    // Orchestrator status
    this.app.get('/api/orchestrator/status', (_req: Request, res: Response) => {
      res.json(this.orchestrator.getStatus());
    });

    // System resources
    this.app.get('/api/system/resources', (_req: Request, res: Response) => {
      const memUsage = process.memoryUsage();
      res.json({
        memory: {
          heapUsed: memUsage.heapUsed,
          heapTotal: memUsage.heapTotal,
          rss: memUsage.rss,
          external: memUsage.external
        },
        cpu: process.cpuUsage(),
        uptime: process.uptime()
      });
    });

    // Error handling
    this.app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
      console.error('Unhandled error:', err);
      res.status(500).json({ 
        error: 'Internal server error',
        message: err.message
      });
    });
  }

  private setupWebSocket() {
    this.wss.on('connection', (socket, req) => {
      const clientId = `client-${++this.clientIdCounter}`;
      const client: WSClient = {
        id: clientId,
        socket,
        subscriptions: new Set(['analysis', 'metrics', 'status'])
      };
      this.clients.set(clientId, client);

      console.log(`[WS] Client connected: ${clientId}`);

      // Send welcome message
      socket.send(JSON.stringify({
        type: 'connected',
        clientId,
        timestamp: Date.now()
      }));

      socket.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleWSMessage(client, message);
        } catch (error) {
          console.error('[WS] Invalid message:', error);
        }
      });

      socket.on('close', () => {
        this.clients.delete(clientId);
        console.log(`[WS] Client disconnected: ${clientId}`);
      });

      socket.on('error', (error) => {
        console.error(`[WS] Client ${clientId} error:`, error);
      });
    });
  }

  private handleWSMessage(client: WSClient, message: any) {
    switch (message.type) {
      case 'subscribe':
        if (message.channel) {
          client.subscriptions.add(message.channel);
          client.socket.send(JSON.stringify({
            type: 'subscribed',
            channel: message.channel
          }));
        }
        break;

      case 'unsubscribe':
        if (message.channel) {
          client.subscriptions.delete(message.channel);
          client.socket.send(JSON.stringify({
            type: 'unsubscribed',
            channel: message.channel
          }));
        }
        break;

      case 'analyze':
        this.handleAnalysisRequest(client, message);
        break;

      case 'parameterChange':
        this.broadcastToClients('parameterChange', message, ['analysis']);
        break;

      default:
        console.log(`[WS] Unknown message type: ${message.type}`);
    }
  }

  private async handleAnalysisRequest(client: WSClient, message: any) {
    try {
      const { parameters, fidelity, options } = message;

      // Send progress updates
      client.socket.send(JSON.stringify({
        type: 'analysisStart',
        requestId: message.requestId
      }));

      const result = await this.orchestrator.analyze(parameters, fidelity, options);

      client.socket.send(JSON.stringify({
        type: 'analysisComplete',
        requestId: message.requestId,
        result
      }));
    } catch (error) {
      client.socket.send(JSON.stringify({
        type: 'analysisError',
        requestId: message.requestId,
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
    }
  }

  private setupOrchestratorEvents() {
    this.orchestrator.on('analysisStart', (data) => {
      this.broadcastToClients('analysisStart', data, ['analysis', 'status']);
    });

    this.orchestrator.on('analysisProgress', (data) => {
      this.broadcastToClients('analysisProgress', data, ['analysis']);
    });

    this.orchestrator.on('analysisComplete', (data) => {
      this.broadcastToClients('analysisComplete', data, ['analysis', 'metrics']);
    });

    this.orchestrator.on('analysisError', (data) => {
      this.broadcastToClients('analysisError', data, ['analysis', 'status']);
    });

    this.orchestrator.on('metricsUpdate', (data) => {
      this.broadcastToClients('metricsUpdate', data, ['metrics']);
    });
  }

  private broadcastToClients(type: string, data: any, channels: string[]) {
    const message = JSON.stringify({ type, data, timestamp: Date.now() });
    
    for (const client of this.clients.values()) {
      if (channels.some(c => client.subscriptions.has(c)) && client.socket.readyState === WebSocket.OPEN) {
        client.socket.send(message);
      }
    }
  }

  public start(port: number = 8080): void {
    this.server.listen(port, () => {
      console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   CFD Platform Backend Server                             ║
║   ─────────────────────────────                          ║
║                                                           ║
║   HTTP Server:  http://localhost:${port}                    ║
║   WebSocket:    ws://localhost:${port}                      ║
║   Health:       http://localhost:${port}/api/health        ║
║                                                           ║
║   Plugins loaded: ${getPluginManager().getAll().length}                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
      `);
    });
  }

  public stop(): void {
    console.log('Shutting down CFD Platform...');
    
    // Close WebSocket connections
    for (const client of this.clients.values()) {
      client.socket.close();
    }
    this.wss.close();
    
    // Close HTTP server
    this.server.close(() => {
      console.log('Server closed');
    });

    // Dispose orchestrator
    this.orchestrator.dispose();
    
    // Dispose plugin manager
    getPluginManager().dispose();
  }
}

// Start server
const server = new CFDPlatformServer();
const PORT = parseInt(process.env.PORT || '8080', 10);
server.start(PORT);

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nReceived SIGINT, shutting down...');
  server.stop();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nReceived SIGTERM, shutting down...');
  server.stop();
  process.exit(0);
});

export { CFDPlatformServer };