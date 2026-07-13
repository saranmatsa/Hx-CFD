//! HX CFD - Tauri Backend Library
//! 
//! This library provides the core functionality for the HX CFD desktop application,
//! including dependency management, lifecycle control, and backend process management.

pub mod error;
pub mod config;
pub mod logging;
pub mod dependency;
pub mod lifecycle;
pub mod splash;
pub mod backend;
pub mod commands;

pub use error::{HxCfdError, HxCfdResult};
pub use config::{AppConfig, RuntimeConfig};
pub use dependency::{Component, ComponentStatus, DependencyManager};
pub use lifecycle::{LifecycleManager, LifecycleState};
pub use splash::{SplashConfig, SplashManager};
pub use backend::{BackendManager, BackendInfo, BackendStatus};
pub use commands::AppState;