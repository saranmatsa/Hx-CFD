//! Error handling module for HX CFD
//! 
//! Provides error types and result aliases for the application.

use thiserror::Error;

/// Main error type for HX CFD application
#[derive(Error, Debug)]
pub enum HxCfdError {
    /// Configuration error
    #[error("Configuration error: {0}")]
    Config(String),
    
    /// Backend process error
    #[error("Backend process error: {0}")]
    Backend(String),
    
    /// Dependency error
    #[error("Dependency error: {0}")]
    Dependency(String),
    
    /// Lifecycle error
    #[error("Lifecycle error: {0}")]
    Lifecycle(String),
    
    /// IO error
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    /// JSON error
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    
    /// Tauri error
    #[error("Tauri error: {0}")]
    Tauri(#[from] tauri::Error),
}

/// Result type alias for HX CFD operations
pub type HxCfdResult<T> = Result<T, HxCfdError>;

impl From<HxCfdError> for String {
    fn from(err: HxCfdError) -> Self {
        err.to_string()
    }
}