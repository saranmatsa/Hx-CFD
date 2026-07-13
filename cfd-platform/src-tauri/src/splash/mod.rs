//! Splash screen module for HX CFD
//! 
//! Manages the splash screen during application startup.

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, WebviewWindow};
use crate::error::HxCfdResult;

/// Splash screen configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SplashConfig {
    /// Window title
    pub title: String,
    /// Window width
    pub width: u32,
    /// Window height
    pub height: u32,
    /// Center on screen
    pub center: bool,
    /// URL to load
    pub url: String,
}

impl Default for SplashConfig {
    fn default() -> Self {
        Self {
            title: "HX CFD".to_string(),
            width: 600,
            height: 400,
            center: true,
            url: "splash.html".to_string(),
        }
    }
}

/// Splash screen manager
#[derive(Debug)]
pub struct SplashManager {
    /// Splash window reference
    pub window: Option<WebviewWindow>,
    /// Configuration
    pub config: SplashConfig,
}

impl Default for SplashManager {
    fn default() -> Self {
        Self {
            window: None,
            config: SplashConfig::default(),
        }
    }
}

impl SplashManager {
    /// Create a new splash manager
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Create and show the splash screen
    pub fn show(&mut self, app: &AppHandle) -> HxCfdResult<()> {
        let window = tauri::WebviewWindowBuilder::new(
            app,
            "splash",
            tauri::WebviewUrl::App(self.config.url.clone().into()),
        )
        .title(&self.config.title)
        .inner_size(self.config.width as f64, self.config.height as f64)
        .center()
        .decorations(false)
        .transparent(true)
        .resizable(false)
        .build()?;
        
        self.window = Some(window);
        Ok(())
    }
    
    /// Update the splash screen progress
    pub fn update_progress(&self, progress: f64, message: &str) -> HxCfdResult<()> {
        // The splash screen receives progress updates via events
        // This is handled by the frontend
        if let Some(window) = &self.window {
            window.emit("splash-progress", serde_json::json!({
                "progress": progress,
                "message": message
            }))?;
        }
        Ok(())
    }
    
    /// Hide the splash screen and close it
    pub fn hide(&self) -> HxCfdResult<()> {
        if let Some(window) = &self.window {
            window.close()?;
        }
        Ok(())
    }
    
    /// Set the splash screen to fade out and close
    pub fn fade_out(&self, duration_ms: u64) -> HxCfdResult<()> {
        if let Some(window) = &self.window {
            // Emit event to trigger CSS fade-out animation
            window.emit("splash-fade-out", duration_ms)?;
            
            // Close after animation completes
            let window_clone = window.clone();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_millis(duration_ms));
                let _ = window_clone.close();
            });
        }
        Ok(())
    }
}