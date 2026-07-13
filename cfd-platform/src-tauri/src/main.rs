//! HX CFD - Main Entry Point
//! 
//! This is the main binary entry point for the HX CFD Tauri application.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::Manager;
use hx_cfd::{
    AppState,
    commands::*,
    logging,
    LifecycleState,
};

fn main() {
    // Initialize logging
    logging::init_logging();
    logging::log_info("Starting HX CFD application");
    
    // Set up panic hook for logging
    std::panic::set_hook(Box::new(|panic_info| {
        let msg = if let Some(s) = panic_info.payload().downcast_ref::<&str>() {
            s.to_string()
        } else if let Some(s) = panic_info.payload().downcast_ref::<String>() {
            s.clone()
        } else {
            "Unknown panic".to_string()
        };
        
        let location = panic_info.location()
            .map(|l| format!("{}:{}:{}", l.file(), l.line(), l.column()))
            .unwrap_or_else(|| "unknown location".to_string());
        
        logging::log_error(&format!("PANIC at {}: {}", location, msg));
    }));
    
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            logging::log_info("Setting up application");
            
            // Initialize application state
            let state = AppState::new(app.handle())?;
            app.manage(state);
            
            // Set initial lifecycle state
            let state: tauri::State<AppState> = app.state();
            {
                let mut lifecycle = state.lifecycle_manager.lock().unwrap();
                lifecycle.set_state(LifecycleState::Initializing);
            }
            
            logging::log_info("Application setup complete");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Configuration commands
            get_config,
            get_runtime_config,
            update_runtime_config,
            // Dependency commands
            get_components,
            get_component,
            get_installation_progress,
            check_dependencies,
            // Lifecycle commands
            get_lifecycle_state,
            transition_lifecycle_state,
            // Backend commands
            get_backend_status,
            start_backend,
            stop_backend,
            // Window commands
            show_main_window,
            hide_main_window,
            minimize_main_window,
            toggle_maximize_main_window,
            close_main_window,
            // Utility commands
            get_app_version,
            open_url,
            get_log_path,
        ])
        .on_window_event(|window, event| {
            match event {
                tauri::WindowEvent::CloseRequested { api, .. } => {
                    // Handle window close
                    logging::log_info("Main window close requested");
                    
                    // Stop backend if running
                    let state: tauri::State<AppState> = window.state();
                    if let Ok(mut backend) = state.backend_manager.lock() {
                        let _ = backend.stop();
                    }
                    
                    // Update lifecycle state
                    if let Ok(mut lifecycle) = state.lifecycle_manager.lock() {
                        lifecycle.set_state(LifecycleState::ShuttingDown);
                    }
                    
                    logging::log_info("Application shutdown complete");
                }
                tauri::WindowEvent::Focused(focused) => {
                    if *focused {
                        logging::log_info("Main window focused");
                    }
                }
                _ => {}
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}