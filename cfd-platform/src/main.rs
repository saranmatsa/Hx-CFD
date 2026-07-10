//! CFD Platform - Tauri Desktop Application Entry Point
//!
//! This is the main entry point for the Tauri v2 application. It manages the
//! frontend (React) and backend (Python FastAPI) processes.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod backend;
mod commands;

use backend::{BackendLog, BackendManager, BackendStatus};
use commands::AppState;
use std::sync::Arc;
use tauri::{Manager, WindowEvent};

fn main() {
    // Initialize logging
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            // Initialize backend manager
            let backend = Arc::new(BackendManager::new());

            // Store in app state
            app.manage(AppState { backend: backend.clone() });

            // Get app handle for async operations
            let app_handle = app.handle().clone();

            // Auto-start backend on launch
            let backend_clone = backend.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = backend_clone.start(&app_handle).await {
                    log::error!("Failed to auto-start backend: {}", e);
                    let _ = app_handle.emit("backend-error", &format!("Auto-start failed: {}", e));
                }
            });

            // Set up window event handlers
            let window = app.get_webview_window("main").unwrap();
            let backend_clone = backend.clone();
            window.on_window_event(move |event| {
                if let WindowEvent::CloseRequested { api, .. } = event {
                    // Prevent default close to handle graceful shutdown
                    api.prevent_close();

                    let backend = backend_clone.clone();
                    let window = window.clone();
                    tauri::async_runtime::spawn(async move {
                        log::info!("Window close requested, stopping backend...");
                        if let Err(e) = backend.stop().await {
                            log::error!("Error stopping backend: {}", e);
                        }
                        window.close().unwrap();
                    });
                }
            });

            // Set up backend log forwarding to frontend
            let app_handle_clone = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let mut interval = tokio::time::interval(tokio::time::Duration::from_millis(500));
                loop {
                    interval.tick().await;
                    let logs = backend.logs().await;
                    if !logs.is_empty() {
                        // Emit latest logs to frontend
                        let _ = app_handle_clone.emit("backend-logs", &logs);
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::start_backend,
            commands::stop_backend,
            commands::get_backend_status,
            commands::get_backend_logs,
            commands::check_backend_health,
            commands::restart_backend,
            commands::get_system_info,
            commands::get_app_paths,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, event| match event {
            tauri::RunEvent::ExitRequested { api, .. } => {
                api.prevent_exit();
            }
            tauri::RunEvent::Exit => {
                log::info!("Application exiting");
            }
            _ => {}
        });
}