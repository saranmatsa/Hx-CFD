//! Backend management module for HX CFD
//! 
//! Manages the Python backend process.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::{AppHandle, Manager};
use crate::config::AppConfig;
use crate::error::{HxCfdError, HxCfdResult};
use crate::logging;

/// Backend process status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BackendStatus {
    /// Backend is not running
    NotRunning,
    /// Backend is starting
    Starting,
    /// Backend is running
    Running,
    /// Backend is stopping
    Stopping,
    /// Backend encountered an error
    Error,
}

impl Default for BackendStatus {
    fn default() -> Self {
        Self::NotRunning
    }
}

/// Backend information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendInfo {
    /// Process ID
    pub pid: u32,
    /// Status
    pub status: BackendStatus,
    /// Executable path
    pub executable: PathBuf,
    /// Start time
    pub start_time: String,
}

/// Backend manager
#[derive(Debug)]
pub struct BackendManager {
    /// Backend status
    pub status: BackendStatus,
    /// Process ID
    pub pid: Option<u32>,
    /// Backend executable path
    pub executable: PathBuf,
    /// Retained child handle for supervised lifecycle management.
    pub child: Option<std::process::Child>,
}

impl Default for BackendManager {
    fn default() -> Self {
        Self {
            status: BackendStatus::NotRunning,
            pid: None,
            executable: PathBuf::from("bin/backend/hx-cfd-backend.exe"),
            child: None,
        }
    }
}

impl BackendManager {
    /// Create a new backend manager
    pub fn new(executable: PathBuf) -> Self {
        Self {
            executable,
            ..Default::default()
        }
    }
    
    /// Check if the backend is running
    pub fn is_running(&self) -> bool {
        self.status == BackendStatus::Running && self.pid.is_some()
    }
    
    /// Start the backend process
    pub fn start(&mut self, config: &AppConfig) -> HxCfdResult<BackendInfo> {
        if self.is_running() {
            return Err(HxCfdError::Backend("Backend is already running".to_string()));
        }
        
        if !self.executable.exists() {
            return Err(HxCfdError::Backend(format!(
                "Backend executable not found at {:?}",
                self.executable
            )));
        }
        
        self.status = BackendStatus::Starting;
        logging::log_info(&format!("Starting backend: {:?}", self.executable));
        
        // Set up environment variables
        let mut cmd = Command::new(&self.executable);
        self.configure_local_environment(&mut cmd, config);
        
        // Redirect stdout and stderr to log files
        let log_file = config.log_dir.join("backend.log");
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());
        
        // Start the process
        let child = cmd.spawn()?;
        let pid = child.id();
        
        self.child = Some(child);
        self.pid = Some(pid);
        self.status = BackendStatus::Running;
        
        logging::log_info(&format!("Backend started successfully with PID: {}", pid));
        
        Ok(BackendInfo {
            pid,
            status: self.status,
            executable: self.executable.clone(),
            start_time: chrono::Local::now().to_rfc3339(),
        })
    }
    
    /// Stop the backend process
    pub fn stop(&mut self) -> HxCfdResult<()> {
        if !self.is_running() {
            return Ok(());
        }
        
        self.status = BackendStatus::Stopping;
        
        if let Some(pid) = self.pid {
            logging::log_info(&format!("Stopping backend process with PID: {}", pid));
            
            self.stop_process_tree(pid)?;
            if let Some(mut child) = self.child.take() {
                let _ = child.wait();
            }
            
            self.pid = None;
            self.status = BackendStatus::NotRunning;
            logging::log_info("Backend stopped successfully");
        }
        
        Ok(())
    }
    
    /// Get backend status
    pub fn get_status(&self) -> BackendStatus {
        // Check if process is still alive
        if let Some(pid) = self.pid {
            let alive = check_process_alive(pid);
            if !alive && self.status == BackendStatus::Running {
                // Process died unexpectedly
                return BackendStatus::Error;
            }
        }
        self.status
    }
    
    /// Send a command to the backend via stdin
    pub fn send_command(&self, command: &str) -> HxCfdResult<()> {
        Err(HxCfdError::Backend(format!(
            "Unsupported raw backend command: {}. Use a typed desktop contract instead.",
            command
        )))
    }

    /// Query the canonical fourteen-engine inventory through a private local contract.
    pub fn engine_inventory(&self, config: &AppConfig) -> HxCfdResult<Value> {
        self.run_local_contract(config, &["--engine-inventory"], None)
    }

    /// Read a project's local workflow state through the managed backend executable.
    pub fn workflow_snapshot(&self, config: &AppConfig, project_id: &str) -> HxCfdResult<Value> {
        self.run_local_contract(config, &["--workflow-snapshot", project_id], None)
    }

    /// Persist a semantic workflow recipe without exposing a localhost endpoint to the UI.
    pub fn configure_workflow_stage(
        &self,
        config: &AppConfig,
        project_id: &str,
        stage_id: &str,
        recipe: &Value,
    ) -> HxCfdResult<Value> {
        let payload = serde_json::to_string(recipe)
            .map_err(|error| HxCfdError::Backend(format!("Unable to serialize workflow recipe: {}", error)))?;
        self.run_local_contract(
            config,
            &["--workflow-config", project_id, stage_id],
            Some(&payload),
        )
    }

    fn run_local_contract(
        &self,
        config: &AppConfig,
        arguments: &[&str],
        payload: Option<&str>,
    ) -> HxCfdResult<Value> {
        if !self.executable.exists() {
            return Err(HxCfdError::Backend(format!(
                "Backend executable not found at {:?}",
                self.executable
            )));
        }

        let mut command = Command::new(&self.executable);
        command
            .args(arguments)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        self.configure_local_environment(&mut command, config);
        let mut child = command.spawn()?;
        if let Some(payload) = payload {
            if let Some(stdin) = child.stdin.as_mut() {
                stdin.write_all(payload.as_bytes())?;
            }
        }
        let output = child.wait_with_output()?;
        if !output.status.success() {
            let error = String::from_utf8_lossy(&output.stderr);
            return Err(HxCfdError::Backend(format!(
                "Local backend contract failed: {}",
                error.trim()
            )));
        }
        serde_json::from_slice(&output.stdout).map_err(|error| {
            HxCfdError::Backend(format!(
                "Local backend contract returned invalid JSON: {}",
                error
            ))
        })
    }

    fn configure_local_environment(&self, command: &mut Command, config: &AppConfig) {
        command
            .env("DATA_DIR", &config.data_dir)
            .env("LOGS_DIR", &config.log_dir)
            .env("PROJECTS_DIR", config.data_dir.join("projects"))
            .env("TEMP_DIR", config.cache_dir.join("tmp"))
            .env("CACHE_DIR", &config.cache_dir)
            .env("OPENFOAM_PATH", config.openfoam_path())
            .env("GMSH_PATH", config.gmsh_path())
            .env("PARAVIEW_PATH", config.paraview_path())
            .env("FREECAD_PATH", config.freecad_path())
            .env("RUST_LOG", "info");
    }

    fn stop_process_tree(&self, pid: u32) -> HxCfdResult<()> {
        #[cfg(windows)]
        {
            let output = Command::new("taskkill")
                .args(["/PID", &pid.to_string(), "/T", "/F"])
                .output()?;
            if !output.status.success() {
                let error = String::from_utf8_lossy(&output.stderr);
                logging::log_error(&format!("Failed to stop backend: {}", error));
                return Err(HxCfdError::Backend(format!("Failed to stop backend: {}", error)));
            }
        }

        #[cfg(not(windows))]
        {
            let output = Command::new("kill")
                .args(["-TERM", &pid.to_string()])
                .output()?;
            if !output.status.success() {
                let error = String::from_utf8_lossy(&output.stderr);
                logging::log_error(&format!("Failed to stop backend: {}", error));
                return Err(HxCfdError::Backend(format!("Failed to stop backend: {}", error)));
            }
        }

        Ok(())
    }
}

/// Check if a process is still alive
fn check_process_alive(pid: u32) -> bool {
    #[cfg(windows)]
    {
        let output = Command::new("tasklist")
            .args(["/FI", &format!("PID eq {}", pid), "/NH"])
            .output();
        
        if let Ok(output) = output {
            let stdout = String::from_utf8_lossy(&output.stdout);
            return stdout.contains(&pid.to_string());
        }
    }
    
    #[cfg(not(windows))]
    {
        let output = Command::new("ps")
            .args(["-p", &pid.to_string(), "-o", "pid="])
            .output();
        
        if let Ok(output) = output {
            return output.status.success();
        }
    }
    
    false
}
