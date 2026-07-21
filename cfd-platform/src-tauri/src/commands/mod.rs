//! Commands module for HX CFD
//! 
//! Exposes Tauri commands to the frontend.

use tauri::{AppHandle, Manager, State, WebviewWindow};
use std::sync::Mutex;
use crate::config::{AppConfig, RuntimeConfig};
use crate::dependency::{Component, ComponentStatus, DependencyManager};
use crate::lifecycle::{LifecycleManager, LifecycleState};
use crate::backend::{BackendManager, BackendInfo, BackendStatus};
use crate::error::HxCfdResult;

/// Application state
pub struct AppState {
    /// Application configuration
    pub config: Mutex<AppConfig>,
    /// Runtime configuration
    pub runtime_config: Mutex<RuntimeConfig>,
    /// Dependency manager
    pub dependency_manager: Mutex<DependencyManager>,
    /// Lifecycle manager
    pub lifecycle_manager: Mutex<LifecycleManager>,
    /// Backend manager
    pub backend_manager: Mutex<BackendManager>,
}

impl AppState {
    pub fn new(app: &AppHandle) -> HxCfdResult<Self> {
        let config = AppConfig::new(app)?;
        config.ensure_directories()?;
        
        let dependency_manager = DependencyManager::new(&config);
        let backend_manager = BackendManager::new(config.backend_path.clone());
        
        Ok(Self {
            config: Mutex::new(config),
            runtime_config: Mutex::new(RuntimeConfig::default()),
            dependency_manager: Mutex::new(dependency_manager),
            lifecycle_manager: Mutex::new(LifecycleManager::new()),
            backend_manager: Mutex::new(backend_manager),
        })
    }
}

// ============================================================================
// Configuration Commands
// ============================================================================

/// Get the application configuration
#[tauri::command]
pub fn get_config(state: State<AppState>) -> Result<AppConfig, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.clone())
}

/// Get the runtime configuration
#[tauri::command]
pub fn get_runtime_config(state: State<AppState>) -> Result<RuntimeConfig, String> {
    let config = state.runtime_config.lock().map_err(|e| e.to_string())?;
    Ok(config.clone())
}

/// Update the runtime configuration
#[tauri::command]
pub fn update_runtime_config(
    state: State<AppState>,
    working_directory: Option<String>,
) -> Result<(), String> {
    let mut config = state.runtime_config.lock().map_err(|e| e.to_string())?;
    if let Some(dir) = working_directory {
        config.working_directory = std::path::PathBuf::from(dir);
    }
    Ok(())
}

// ============================================================================
// Dependency Commands
// ============================================================================

/// Get all components
#[tauri::command]
pub fn get_components(state: State<AppState>) -> Result<Vec<Component>, String> {
    let manager = state.dependency_manager.lock().map_err(|e| e.to_string())?;
    Ok(manager.components.clone())
}

/// Get a specific component by ID
#[tauri::command]
pub fn get_component(state: State<AppState>, id: String) -> Result<Option<Component>, String> {
    let manager = state.dependency_manager.lock().map_err(|e| e.to_string())?;
    Ok(manager.get_component(&id).cloned())
}

/// Get installation progress
#[tauri::command]
pub fn get_installation_progress(state: State<AppState>) -> Result<f64, String> {
    let manager = state.dependency_manager.lock().map_err(|e| e.to_string())?;
    Ok(manager.installation_progress())
}

/// Check if all required components are installed
#[tauri::command]
pub fn check_dependencies(state: State<AppState>) -> Result<bool, String> {
    let manager = state.dependency_manager.lock().map_err(|e| e.to_string())?;
    Ok(manager.all_required_installed())
}

// ============================================================================
// Lifecycle Commands
// ============================================================================

/// Get the current lifecycle state
#[tauri::command]
pub fn get_lifecycle_state(state: State<AppState>) -> Result<LifecycleState, String> {
    let manager = state.lifecycle_manager.lock().map_err(|e| e.to_string())?;
    Ok(manager.state)
}

/// Transition to a new lifecycle state
#[tauri::command]
pub fn transition_lifecycle_state(
    state: State<AppState>,
    new_state: LifecycleState,
) -> Result<bool, String> {
    let mut manager = state.lifecycle_manager.lock().map_err(|e| e.to_string())?;
    if manager.can_transition_to(new_state) {
        manager.set_state(new_state);
        Ok(true)
    } else {
        Ok(false)
    }
}

// ============================================================================
// Backend Commands
// ============================================================================

/// Get backend status
#[tauri::command]
pub fn get_backend_status(state: State<AppState>) -> Result<BackendStatus, String> {
    let manager = state.backend_manager.lock().map_err(|e| e.to_string())?;
    Ok(manager.get_status())
}

/// Start the backend
#[tauri::command]
pub fn start_backend(state: State<AppState>) -> Result<BackendInfo, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let mut manager = state.backend_manager.lock().map_err(|e| e.to_string())?;
    manager.start(&config).map_err(|e| e.to_string())
}

/// Stop the backend
#[tauri::command]
pub fn stop_backend(state: State<AppState>) -> Result<(), String> {
    let mut manager = state.backend_manager.lock().map_err(|e| e.to_string())?;
    manager.stop().map_err(|e| e.to_string())
}

/// Get the canonical local capability state for all fourteen engineering engines.
#[tauri::command]
pub fn get_engine_inventory(state: State<AppState>) -> Result<serde_json::Value, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    let manager = state.backend_manager.lock().map_err(|e| e.to_string())?;
    let inventory = manager.engine_inventory(&config).map_err(|e| e.to_string())?;
    inventory
        .get("engines")
        .cloned()
        .ok_or_else(|| "Local backend engine contract returned no engine inventory.".to_string())
}

/// Read a project's durable workflow state through the local desktop bridge.
#[tauri::command]
pub fn get_workflow_snapshot(
    state: State<AppState>,
    project_id: String,
) -> Result<serde_json::Value, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    let manager = state.backend_manager.lock().map_err(|e| e.to_string())?;
    manager
        .workflow_snapshot(&config, &project_id)
        .map_err(|e| e.to_string())
}

/// Persist a semantic workflow recipe without allowing the webview to reach a port directly.
#[tauri::command]
pub fn configure_workflow_stage(
    state: State<AppState>,
    project_id: String,
    stage_id: String,
    configuration: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    let manager = state.backend_manager.lock().map_err(|e| e.to_string())?;
    manager
        .configure_workflow_stage(&config, &project_id, &stage_id, &configuration)
        .map_err(|e| e.to_string())
}

// ============================================================================
// Window Commands
// ============================================================================

/// Show the main window and hide the splash screen
#[tauri::command]
pub fn show_main_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
    }
    
    // Close splash window if it exists
    if let Some(splash) = app.get_webview_window("splash") {
        let _ = splash.close();
    }
    
    Ok(())
}

/// Hide the main window
#[tauri::command]
pub fn hide_main_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Minimize the main window
#[tauri::command]
pub fn minimize_main_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.minimize().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Maximize or restore the main window
#[tauri::command]
pub fn toggle_maximize_main_window(app: AppHandle) -> Result<bool, String> {
    if let Some(window) = app.get_webview_window("main") {
        let is_maximized = window.is_maximized().map_err(|e| e.to_string())?;
        if is_maximized {
            window.unmaximize().map_err(|e| e.to_string())?;
        } else {
            window.maximize().map_err(|e| e.to_string())?;
        }
        Ok(!is_maximized)
    } else {
        Ok(false)
    }
}

/// Close the main window (quit application)
#[tauri::command]
pub fn close_main_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

// ============================================================================
// Utility Commands
// ============================================================================

/// Get application version
#[tauri::command]
pub fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Open a URL in the default browser
#[tauri::command]
pub fn open_url(app: AppHandle, url: String) -> Result<(), String> {
    tauri::opener::open_url(&url, Some(&app))
        .map_err(|e| e.to_string())
}

/// Get log file path
#[tauri::command]
pub fn get_log_path(state: State<AppState>) -> Result<Option<String>, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let log_path = crate::logging::get_log_path(&config.log_dir);
    Ok(log_path.map(|p| p.to_string_lossy().to_string()))
}
