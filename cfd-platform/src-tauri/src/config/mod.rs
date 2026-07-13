//! Configuration module for HX CFD
//! 
//! Manages application configuration, paths, and settings.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use crate::error::{HxCfdError, HxCfdResult};

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Application name
    pub name: String,
    /// Application version
    pub version: String,
    /// Data directory path
    pub data_dir: PathBuf,
    /// Dependencies directory path
    pub dependencies_dir: PathBuf,
    /// Backend executable path
    pub backend_path: PathBuf,
    /// Log directory path
    pub log_dir: PathBuf,
    /// Cache directory path
    pub cache_dir: PathBuf,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            name: "HX CFD".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            data_dir: dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("hx-cfd"),
            dependencies_dir: PathBuf::from("dependencies"),
            backend_path: PathBuf::from("bin/backend/hx-cfd-backend.exe"),
            log_dir: dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("hx-cfd")
                .join("logs"),
            cache_dir: dirs::cache_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("hx-cfd"),
        }
    }
}

impl AppConfig {
    /// Create a new configuration from Tauri app handle
    pub fn new(app: &tauri::AppHandle) -> HxCfdResult<Self> {
        let mut config = Self::default();
        
        // Override with app-specific paths
        if let Some(data_dir) = app.path().app_data_dir().ok() {
            config.data_dir = data_dir.clone();
            config.log_dir = data_dir.join("logs");
            config.cache_dir = data_dir.join("cache");
        }
        
        // Get resource path for bundled resources
        if let Ok(resource_path) = app.path().resource_dir() {
            config.dependencies_dir = resource_path.join("dependencies");
            config.backend_path = resource_path.join("bin/backend/hx-cfd-backend.exe");
        }
        
        Ok(config)
    }
    
    /// Get the OpenFOAM path
    pub fn openfoam_path(&self) -> PathBuf {
        self.dependencies_dir.join("openfoam")
    }
    
    /// Get the Gmsh path
    pub fn gmsh_path(&self) -> PathBuf {
        self.dependencies_dir.join("gmsh")
    }
    
    /// Get the ParaView path
    pub fn paraview_path(&self) -> PathBuf {
        self.dependencies_dir.join("paraview")
    }
    
    /// Get the FreeCAD path
    pub fn freecad_path(&self) -> PathBuf {
        self.dependencies_dir.join("freecad")
    }
    
    /// Get the Python runtime path
    pub fn python_path(&self) -> PathBuf {
        self.dependencies_dir.join("python")
    }
    
    /// Ensure required directories exist
    pub fn ensure_directories(&self) -> HxCfdResult<()> {
        let dirs = [&self.data_dir, &self.log_dir, &self.cache_dir];
        for dir in dirs {
            if !dir.exists() {
                std::fs::create_dir_all(dir)?;
            }
        }
        Ok(())
    }
}

/// Runtime configuration for the backend process
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeConfig {
    /// OpenFOAM version
    pub openfoam_version: String,
    /// Gmsh version
    pub gmsh_version: String,
    /// ParaView version
    pub paraview_version: String,
    /// Python version
    pub python_version: String,
    /// Working directory for simulations
    pub working_directory: PathBuf,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        Self {
            openfoam_version: "v10".to_string(),
            gmsh_version: "4.12".to_string(),
            paraview_version: "5.12".to_string(),
            python_version: "3.11".to_string(),
            working_directory: dirs::document_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("HX CFD"),
        }
    }
}