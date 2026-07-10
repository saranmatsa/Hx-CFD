//! Tauri Commands
//!
//! Provides Tauri commands for frontend-backend communication.

use crate::backend::{BackendLog, BackendManager, BackendStatus};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{AppHandle, Manager, State};

/// Application state
pub struct AppState {
    pub backend: Arc<BackendManager>,
}

/// System information
#[derive(Debug, Serialize, Deserialize)]
pub struct SystemInfo {
    pub os: String,
    pub arch: String,
    pub version: String,
    pub hostname: String,
    pub cpu_count: usize,
    pub total_memory: u64,
    pub available_memory: u64,
}

/// Application paths
#[derive(Debug, Serialize, Deserialize)]
pub struct AppPaths {
    pub app_data: String,
    pub config: String,
    pub cache: String,
    pub temp: String,
    pub backend: Option<String>,
}

/// Backend status response
#[derive(Debug, Serialize, Deserialize)]
pub struct BackendStatusResponse {
    pub status: BackendStatus,
    pub uptime_seconds: Option<u64>,
    pub pid: Option<u32>,
}

/// Start the backend
#[tauri::command]
pub async fn start_backend(state: State<'_, AppState>, app: AppHandle) -> Result<(), String> {
    state
        .backend
        .start(&app)
        .await
        .map_err(|e| format!("Failed to start backend: {}", e))
}

/// Stop the backend
#[tauri::command]
pub async fn stop_backend(state: State<'_, AppState>) -> Result<(), String> {
    state
        .backend
        .stop()
        .await
        .map_err(|e| format!("Failed to stop backend: {}", e))
}

/// Get backend status
#[tauri::command]
pub async fn get_backend_status(state: State<'_, AppState>) -> Result<BackendStatusResponse, String> {
    let status = state.backend.status().await;
    Ok(BackendStatusResponse {
        status,
        uptime_seconds: None, // TODO: track uptime
        pid: None,            // TODO: track PID
    })
}

/// Get backend logs
#[tauri::command]
pub async fn get_backend_logs(state: State<'_, AppState>, limit: Option<usize>) -> Result<Vec<BackendLog>, String> {
    let logs = state.backend.logs().await;
    let limit = limit.unwrap_or(100);
    if logs.len() > limit {
        Ok(logs[logs.len() - limit..].to_vec())
    } else {
        Ok(logs)
    }
}

/// Check backend health
#[tauri::command]
pub async fn check_backend_health(state: State<'_, AppState>) -> Result<bool, String> {
    state
        .backend
        .health_check()
        .await
        .map_err(|e| format!("Health check failed: {}", e))
}

/// Restart the backend
#[tauri::command]
pub async fn restart_backend(state: State<'_, AppState>, app: AppHandle) -> Result<(), String> {
    state
        .backend
        .restart(&app)
        .await
        .map_err(|e| format!("Failed to restart backend: {}", e))
}

/// Get system information
#[tauri::command]
pub async fn get_system_info() -> Result<SystemInfo, String> {
    let sys = sysinfo::System::new_all();
    Ok(SystemInfo {
        os: sysinfo::System::name().unwrap_or_default(),
        arch: std::env::consts::ARCH.to_string(),
        version: sysinfo::System::os_version().unwrap_or_default(),
        hostname: sysinfo::System::host_name().unwrap_or_default(),
        cpu_count: sys.cpus().len(),
        total_memory: sys.total_memory(),
        available_memory: sys.available_memory(),
    })
}

/// Get application paths
#[tauri::command]
pub async fn get_app_paths(app: AppHandle) -> Result<AppPaths, String> {
    let app_data = app
        .path()
        .app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();

    let config = app
        .path()
        .config_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();

    let cache = app
        .path()
        .cache_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();

    let temp = std::env::temp_dir().to_string_lossy().to_string();

    let backend = app
        .path()
        .resource_dir()
        .ok()
        .map(|p| p.join("bin/backend/main").to_string_lossy().to_string());

    Ok(AppPaths {
        app_data,
        config,
        cache,
        temp,
        backend,
    })
}