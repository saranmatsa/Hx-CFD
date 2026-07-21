//! Tauri Commands
//!
//! Provides Tauri commands for frontend-backend communication.

use crate::backend::{BackendLog, BackendManager, BackendStatus};
use anyhow::Context;
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
pub async fn get_backend_status(
    state: State<'_, AppState>,
) -> Result<BackendStatusResponse, String> {
    let status = state.backend.status().await;
    Ok(BackendStatusResponse {
        status,
        uptime_seconds: None, // TODO: track uptime
        pid: None,            // TODO: track PID
    })
}

/// Get backend logs
#[tauri::command]
pub async fn get_backend_logs(
    state: State<'_, AppState>,
    limit: Option<usize>,
) -> Result<Vec<BackendLog>, String> {
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

/// Get the canonical capability inventory for the fourteen local engineering engines.
#[tauri::command]
pub async fn get_engine_inventory(
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .engine_inventory(&app)
        .await
        .and_then(|response| {
            response
                .get("engines")
                .cloned()
                .context("Local backend engine contract returned no engine inventory")
        })
        .map_err(|error| format!("Unable to read local engine inventory: {}", error))
}

/// List active projects from the local-first project store.
#[tauri::command]
pub async fn list_local_projects(
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<Vec<serde_json::Value>, String> {
    state
        .backend
        .list_local_projects(&app)
        .await
        .and_then(|response| {
            response
                .get("projects")
                .and_then(serde_json::Value::as_array)
                .cloned()
                .context("Local backend project contract returned no project list")
        })
        .map_err(|error| format!("Unable to list local projects: {}", error))
}

/// Create a new project with the workflow ledger initialized by the backend.
#[tauri::command]
pub async fn create_local_project(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .create_local_project(&app, &project_id)
        .await
        .and_then(local_project_from_response)
        .map_err(|error| format!("Unable to create local project: {}", error))
}

/// Open an existing project without creating a missing project directory.
#[tauri::command]
pub async fn open_local_project(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .open_local_project(&app, &project_id)
        .await
        .and_then(local_project_from_response)
        .map_err(|error| format!("Unable to open local project: {}", error))
}

/// Rename a durable local project and its manifest through the workflow service.
#[tauri::command]
pub async fn rename_local_project(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
    new_project_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .rename_local_project(&app, &project_id, &new_project_id)
        .await
        .and_then(local_project_from_response)
        .map_err(|error| format!("Unable to rename local project: {}", error))
}

/// Archive an active project without deleting its engineering artifacts.
#[tauri::command]
pub async fn archive_local_project(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .archive_local_project(&app, &project_id)
        .await
        .and_then(local_project_from_response)
        .map_err(|error| format!("Unable to archive local project: {}", error))
}

/// Permanently delete a validated local project directory.
#[tauri::command]
pub async fn delete_local_project(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .delete_local_project(&app, &project_id)
        .await
        .and_then(local_project_from_response)
        .map_err(|error| format!("Unable to delete local project: {}", error))
}

/// Read the local durable workflow state without exposing a backend URL to the UI.
#[tauri::command]
pub async fn get_workflow_snapshot(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .workflow_snapshot(&app, &project_id)
        .await
        .map_err(|error| format!("Unable to read workflow state: {}", error))
}

/// List project-owned artifact descriptors without returning local filesystem paths.
#[tauri::command]
pub async fn list_workflow_artifacts(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
    stage_id: Option<String>,
) -> Result<Vec<serde_json::Value>, String> {
    state
        .backend
        .workflow_artifacts(&app, &project_id, stage_id.as_deref())
        .await
        .and_then(|response| {
            response
                .get("artifacts")
                .and_then(serde_json::Value::as_array)
                .cloned()
                .context("Local backend artifact contract returned no artifact list")
        })
        .map_err(|error| format!("Unable to list project artifacts: {}", error))
}

/// Read one bounded project artifact by opaque catalog ID.
#[tauri::command]
pub async fn read_workflow_artifact(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
    artifact_id: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .read_workflow_artifact(&app, &project_id, &artifact_id)
        .await
        .map_err(|error| format!("Unable to read project artifact: {}", error))
}

/// Export one validated project artifact to a destination chosen by the native dialog.
#[tauri::command]
pub async fn export_workflow_artifact(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
    artifact_id: String,
    destination: String,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .export_workflow_artifact(&app, &project_id, &artifact_id, &destination)
        .await
        .map_err(|error| format!("Unable to export project artifact: {}", error))
}

/// Persist a semantic workflow recipe through the Tauri-owned local bridge.
#[tauri::command]
pub async fn configure_workflow_stage(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
    stage_id: String,
    configuration: serde_json::Value,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .configure_workflow_stage(&app, &project_id, &stage_id, &configuration)
        .await
        .map_err(|error| format!("Unable to save workflow configuration: {}", error))
}

/// Execute a configured workflow stage through its real local-engine adapter.
#[tauri::command]
pub async fn execute_workflow_stage(
    state: State<'_, AppState>,
    app: AppHandle,
    project_id: String,
    stage_id: String,
    recipe: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    state
        .backend
        .execute_workflow_stage(&app, &project_id, &stage_id, recipe.as_ref())
        .await
        .map_err(|error| format!("Unable to execute engineering workflow: {}", error))
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

fn local_project_from_response(response: serde_json::Value) -> anyhow::Result<serde_json::Value> {
    response
        .get("project")
        .cloned()
        .context("Local backend project contract returned no project payload")
}
