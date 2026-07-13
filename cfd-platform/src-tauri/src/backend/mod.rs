//! Backend management module for HX CFD
//! 
//! Manages the Python backend process.

use serde::{Deserialize, Serialize};
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
}

impl Default for BackendManager {
    fn default() -> Self {
        Self {
            status: BackendStatus::NotRunning,
            pid: None,
            executable: PathBuf::from("bin/backend/hx-cfd-backend.exe"),
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
        cmd.env("HX_CFD_DATA_DIR", &config.data_dir);
        cmd.env("HX_CFD_LOG_DIR", &config.log_dir);
        cmd.env("HX_CFD_DEPS_DIR", &config.dependencies_dir);
        cmd.env("RUST_LOG", "info");
        
        // Redirect stdout and stderr to log files
        let log_file = config.log_dir.join("backend.log");
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());
        
        // Start the process
        let child = cmd.spawn()?;
        let pid = child.id();
        
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
            
            #[cfg(windows)]
            {
                let output = Command::new("taskkill")
                    .args(["/PID", &pid.to_string(), "/F"])
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
                    .args(["-9", &pid.to_string()])
                    .output()?;
                
                if !output.status.success() {
                    let error = String::from_utf8_lossy(&output.stderr);
                    logging::log_error(&format!("Failed to stop backend: {}", error));
                    return Err(HxCfdError::Backend(format!("Failed to stop backend: {}", error)));
                }
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
        // This would require a pipe to stdin, which is more complex
        // For now, we just log the command
        logging::log_info(&format!("Backend command: {}", command));
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