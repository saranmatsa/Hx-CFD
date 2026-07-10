//! Backend Process Manager
//!
//! Manages the lifecycle of the Python FastAPI backend process.

use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Child;
use tokio::sync::{Mutex, RwLock};
use tokio::time::timeout;
use tauri::{AppHandle, Emitter, Manager};

/// Backend process state
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum BackendStatus {
    Stopped,
    Starting,
    Running,
    Stopping,
    Error(String),
}

/// Backend log entry
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BackendLog {
    pub timestamp: String,
    pub level: String,
    pub message: String,
}

/// Backend manager handles the Python backend process lifecycle
pub struct BackendManager {
    process: Arc<Mutex<Option<Child>>>,
    status: Arc<RwLock<BackendStatus>>,
    logs: Arc<RwLock<Vec<BackendLog>>>,
    backend_path: Arc<RwLock<Option<PathBuf>>>,
    python_path: Arc<RwLock<Option<PathBuf>>>,
    max_logs: usize,
}

impl BackendManager {
    /// Create a new backend manager
    pub fn new() -> Self {
        Self {
            process: Arc::new(Mutex::new(None)),
            status: Arc::new(RwLock::new(BackendStatus::Stopped)),
            logs: Arc::new(RwLock::new(Vec::new())),
            backend_path: Arc::new(RwLock::new(None)),
            python_path: Arc::new(RwLock::new(None)),
            max_logs: 1000,
        }
    }

    /// Get the current backend status
    pub async fn status(&self) -> BackendStatus {
        self.status.read().await.clone()
    }

    /// Get backend logs
    pub async fn logs(&self) -> Vec<BackendLog> {
        self.logs.read().await.clone()
    }

    /// Add a log entry
    async fn add_log(&self, level: &str, message: &str) {
        let log = BackendLog {
            timestamp: chrono::Utc::now().to_rfc3339(),
            level: level.to_string(),
            message: message.to_string(),
        };
        let mut logs = self.logs.write().await;
        logs.push(log);
        if logs.len() > self.max_logs {
            logs.drain(0..logs.len() - self.max_logs);
        }
    }

    /// Emit status change to frontend
    async fn emit_status(&self, app: &AppHandle, status: BackendStatus) {
        let _ = app.emit("backend-status-changed", &status);
    }

    /// Emit log to frontend
    async fn emit_log(&self, app: &AppHandle, log: BackendLog) {
        let _ = app.emit("backend-log", &log);
    }

    /// Find the backend executable
    async fn find_backend(&self, app: &AppHandle) -> Result<PathBuf> {
        // Check if we already have a cached path
        if let Some(path) = self.backend_path.read().await.as_ref() {
            if path.exists() {
                return Ok(path.clone());
            }
        }

        // Try to find the backend in various locations
        let resource_dir = app
            .path()
            .resource_dir()
            .context("Failed to get resource directory")?;

        let possible_paths = vec![
            // Bundled backend (production) - PyInstaller creates 'cfd-backend' executable
            resource_dir.join("bin/backend/cfd-backend"),
            resource_dir.join("bin/backend/cfd-backend.exe"),
            // Development backend
            PathBuf::from("../../backend/main.py"),
            PathBuf::from("../backend/main.py"),
            PathBuf::from("./backend/main.py"),
        ];

        for path in possible_paths {
            if path.exists() {
                let canonical = path.canonicalize().unwrap_or(path);
                *self.backend_path.write().await = Some(canonical.clone());
                return Ok(canonical);
            }
        }

        anyhow::bail!("Backend not found. Please build the backend first.")
    }

    /// Find Python executable
    async fn find_python(&self) -> Result<PathBuf> {
        if let Some(path) = self.python_path.read().await.as_ref() {
            if path.exists() {
                return Ok(path.clone());
            }
        }

        // Try common Python commands
        let python_commands = if cfg!(target_os = "windows") {
            vec!["python.exe", "python3.exe", "python"]
        } else {
            vec!["python3", "python"]
        };

        for cmd in python_commands {
            if let Ok(output) = Command::new(cmd).arg("--version").output() {
                if output.status.success() {
                    let path = PathBuf::from(cmd);
                    *self.python_path.write().await = Some(path.clone());
                    return Ok(path);
                }
            }
        }

        anyhow::bail!("Python not found. Please install Python 3.10+")
    }

    /// Start the backend process
    pub async fn start(&self, app: &AppHandle) -> Result<()> {
        // Check if already running
        if matches!(self.status().await, BackendStatus::Running) {
            self.add_log("info", "Backend already running").await;
            return Ok(());
        }

        // Update status to starting
        *self.status.write().await = BackendStatus::Starting;
        self.emit_status(app, BackendStatus::Starting).await;
        self.add_log("info", "Starting backend...").await;

        // Find backend and Python
        let backend_path = self.find_backend(app).await?;
        let python_path = self.find_python().await?;

        self.add_log("info", &format!("Backend path: {}", backend_path.display())).await;
        self.add_log("info", &format!("Python path: {}", python_path.display())).await;

        // Determine how to run the backend
        let (program, args) = if backend_path.extension().map_or(false, |e| e == "exe") {
            // Pre-compiled executable
            (backend_path, vec![])
        } else if backend_path.extension().map_or(false, |e| e == "py") {
            // Python script
            (python_path, vec![backend_path.to_string_lossy().to_string()])
        } else {
            anyhow::bail!("Unknown backend type: {}", backend_path.display());
        };

        // Set up environment variables
        let mut env = std::env::vars().collect::<std::collections::HashMap<_, _>>();
        env.insert("PYTHONPATH".to_string(), backend_path.parent().unwrap().to_string_lossy().to_string());
        env.insert("PYTHONUNBUFFERED".to_string(), "1".to_string());
        env.insert("CFD_PLATFORM_TAURI".to_string(), "1".to_string());

        // Get the backend directory for working directory
        let backend_dir = backend_path.parent().unwrap_or_else(|| Path::new("."));

        // Spawn the process
        let mut child = Command::new(&program)
            .args(&args)
            .current_dir(backend_dir)
            .envs(&env)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context("Failed to spawn backend process")?;

        // Take stdout and stderr
        let stdout = child.stdout.take().context("Failed to capture stdout")?;
        let stderr = child.stderr.take().context("Failed to capture stderr")?;

        let process_arc = self.process.clone();
        let status_arc = self.status.clone();
        let logs_arc = self.logs.clone();
        let app_handle = app.clone();

        // Store the process
        *process_arc.lock().await = Some(child);

        // Update status to running
        *status_arc.write().await = BackendStatus::Running;
        self.emit_status(app, BackendStatus::Running).await;
        self.add_log("info", "Backend started successfully").await;

        // Spawn log readers
        let stdout_reader = self.spawn_log_reader(stdout, "stdout", app_handle.clone());
        let stderr_reader = self.spawn_log_reader(stderr, "stderr", app_handle.clone());

        // Wait for process to exit
        let process = process_arc.lock().await.as_mut().unwrap();
        let exit_status = process.wait().await;

        // Wait for log readers to finish
        let _ = tokio::join!(stdout_reader, stderr_reader);

        // Update status based on exit
        let final_status = match exit_status {
            Ok(status) if status.success() => BackendStatus::Stopped,
            Ok(status) => BackendStatus::Error(format!("Backend exited with code: {}", status)),
            Err(e) => BackendStatus::Error(format!("Backend process error: {}", e)),
        };

        *status_arc.write().await = final_status.clone();
        self.emit_status(app, final_status).await;
        self.add_log("info", "Backend stopped").await;

        // Clear process
        *process_arc.lock().await = None;

        Ok(())
    }

    /// Spawn a log reader for stdout/stderr
    fn spawn_log_reader(
        &self,
        stream: tokio::process::ChildStdout,
        stream_name: &str,
        app: AppHandle,
    ) -> tokio::task::JoinHandle<()> {
        let logs = self.logs.clone();
        let stream_name = stream_name.to_string();
        let app_handle = app.clone();

        tokio::spawn(async move {
            let reader = BufReader::new(stream);
            let mut lines = reader.lines();

            while let Ok(Some(line)) = lines.next_line().await {
                let level = if stream_name == "stderr" { "error" } else { "info" };
                let log = BackendLog {
                    timestamp: chrono::Utc::now().to_rfc3339(),
                    level: level.to_string(),
                    message: line,
                };

                let mut logs_guard = logs.write().await;
                logs_guard.push(log.clone());
                if logs_guard.len() > 1000 {
                    logs_guard.drain(0..logs_guard.len() - 1000);
                }

                let _ = app_handle.emit("backend-log", &log);
            }
        })
    }

    /// Stop the backend process
    pub async fn stop(&self) -> Result<()> {
        let mut process_guard = self.process.lock().await;
        if let Some(mut child) = process_guard.take() {
            *self.status.write().await = BackendStatus::Stopping;
            self.add_log("info", "Stopping backend...").await;

            // Try graceful shutdown first
            #[cfg(unix)]
            {
                use tokio::signal::unix::{signal, SignalKind};
                let _ = child.kill().await;
            }
            #[cfg(windows)]
            {
                let _ = child.kill().await;
            }

            // Wait for process to exit with timeout
            match timeout(Duration::from_secs(10), child.wait()).await {
                Ok(Ok(status)) => {
                    self.add_log("info", &format!("Backend stopped with status: {}", status)).await;
                }
                Ok(Err(e)) => {
                    self.add_log("error", &format!("Error waiting for backend: {}", e)).await;
                }
                Err(_) => {
                    self.add_log("warn", "Backend stop timeout, force killing").await;
                    let _ = child.kill().await;
                }
            }
        }

        *self.status.write().await = BackendStatus::Stopped;
        Ok(())
    }

    /// Restart the backend
    pub async fn restart(&self, app: &AppHandle) -> Result<()> {
        self.stop().await?;
        tokio::time::sleep(Duration::from_secs(1)).await;
        self.start(app).await
    }

    /// Check backend health via HTTP
    pub async fn health_check(&self) -> Result<bool> {
        let client = reqwest::Client::new();
        let response = client
            .get("http://localhost:8000/api/health")
            .timeout(Duration::from_secs(5))
            .send()
            .await;

        match response {
            Ok(resp) => Ok(resp.status().is_success()),
            Err(_) => Ok(false),
        }
    }
}

impl Default for BackendManager {
    fn default() -> Self {
        Self::new()
    }
}