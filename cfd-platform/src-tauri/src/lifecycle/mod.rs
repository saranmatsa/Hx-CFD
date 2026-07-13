//! Lifecycle management module for HX CFD
//! 
//! Manages application lifecycle: startup, shutdown, and state transitions.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use tauri::{AppHandle, Manager, State};
use crate::config::AppConfig;
use crate::error::{HxCfdError, HxCfdResult};
use crate::logging;

/// Application lifecycle state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LifecycleState {
    /// Application is initializing
    Initializing,
    /// Application is checking dependencies
    CheckingDependencies,
    /// Application is ready to start
    Ready,
    /// Backend is starting
    StartingBackend,
    /// Backend is running
    BackendRunning,
    /// Backend is stopping
    StoppingBackend,
    /// Application is shutting down
    ShuttingDown,
    /// Application encountered an error
    Error,
}

impl Default for LifecycleState {
    fn default() -> Self {
        Self::Initializing
    }
}

/// Lifecycle manager
#[derive(Debug)]
pub struct LifecycleManager {
    /// Current state
    pub state: LifecycleState,
    /// Backend process ID
    pub backend_pid: Option<u32>,
}

impl Default for LifecycleManager {
    fn default() -> Self {
        Self {
            state: LifecycleState::Initializing,
            backend_pid: None,
        }
    }
}

impl LifecycleManager {
    /// Create a new lifecycle manager
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Transition to a new state
    pub fn set_state(&mut self, state: LifecycleState) {
        let old_state = self.state;
        self.state = state;
        logging::log_info(&format!("Lifecycle state transition: {:?} -> {:?}", old_state, state));
    }
    
    /// Check if the application can transition to a new state
    pub fn can_transition_to(&self, new_state: LifecycleState) -> bool {
        match (self.state, new_state) {
            // Valid transitions
            (LifecycleState::Initializing, LifecycleState::CheckingDependencies) => true,
            (LifecycleState::Initializing, LifecycleState::Error) => true,
            (LifecycleState::CheckingDependencies, LifecycleState::Ready) => true,
            (LifecycleState::CheckingDependencies, LifecycleState::Error) => true,
            (LifecycleState::Ready, LifecycleState::StartingBackend) => true,
            (LifecycleState::Ready, LifecycleState::ShuttingDown) => true,
            (LifecycleState::StartingBackend, LifecycleState::BackendRunning) => true,
            (LifecycleState::StartingBackend, LifecycleState::Error) => true,
            (LifecycleState::BackendRunning, LifecycleState::StoppingBackend) => true,
            (LifecycleState::StoppingBackend, LifecycleState::ShuttingDown) => true,
            (LifecycleState::StoppingBackend, LifecycleState::Error) => true,
            (LifecycleState::Error, LifecycleState::ShuttingDown) => true,
            // Same state is always allowed
            (_, s) if self.state == s => true,
            // All other transitions are invalid
            _ => false,
        }
    }
    
    /// Start the backend process
    pub fn start_backend(&mut self, config: &AppConfig) -> HxCfdResult<u32> {
        if !config.backend_path.exists() {
            return Err(HxCfdError::Backend(format!(
                "Backend executable not found at {:?}",
                config.backend_path
            )));
        }
        
        self.set_state(LifecycleState::StartingBackend);
        
        // Start the backend process
        let mut cmd = Command::new(&config.backend_path);
        cmd.env("HX_CFD_DATA_DIR", &config.data_dir);
        cmd.env("HX_CFD_LOG_DIR", &config.log_dir);
        cmd.env("HX_CFD_DEPS_DIR", &config.dependencies_dir);
        
        let child = cmd.spawn()?;
        let pid = child.id();
        
        self.backend_pid = Some(pid);
        self.set_state(LifecycleState::BackendRunning);
        
        logging::log_info(&format!("Backend started with PID: {}", pid));
        
        Ok(pid)
    }
    
    /// Stop the backend process
    pub fn stop_backend(&mut self) -> HxCfdResult<()> {
        if let Some(pid) = self.backend_pid {
            self.set_state(LifecycleState::StoppingBackend);
            
            #[cfg(windows)]
            {
                let output = Command::new("taskkill")
                    .args(["/PID", &pid.to_string(), "/F"])
                    .output()?;
                
                if !output.status.success() {
                    logging::log_error(&format!(
                        "Failed to stop backend process: {}",
                        String::from_utf8_lossy(&output.stderr)
                    ));
                }
            }
            
            #[cfg(not(windows))]
            {
                let output = Command::new("kill")
                    .args(["-9", &pid.to_string()])
                    .output()?;
                
                if !output.status.success() {
                    logging::log_error(&format!(
                        "Failed to stop backend process: {}",
                        String::from_utf8_lossy(&output.stderr)
                    ));
                }
            }
            
            self.backend_pid = None;
            self.set_state(LifecycleState::ShuttingDown);
            logging::log_info("Backend stopped");
        }
        
        Ok(())
    }
    
    /// Check if the backend is running
    pub fn is_backend_running(&self) -> bool {
        if let Some(pid) = self.backend_pid {
            #[cfg(windows)]
            {
                let output = Command::new("tasklist")
                    .args(["/FI", &format!("PID eq {}", pid)])
                    .output();
                
                if let Ok(output) = output {
                    return String::from_utf8_lossy(&output.stdout)
                        .contains(&pid.to_string());
                }
            }
            
            #[cfg(not(windows))]
            {
                let output = Command::new("ps")
                    .args(["-p", &pid.to_string()])
                    .output();
                
                if let Ok(output) = output {
                    return output.status.success();
                }
            }
        }
        
        false
    }
}