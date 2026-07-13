//! Logging module for HX CFD
//! 
//! Provides logging configuration and utilities.

use log::{info, error, LevelFilter};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use chrono::Local;

/// Initialize the logging system
pub fn init_logging(log_dir: &PathBuf) -> HxCfdResult<()> {
    // Ensure log directory exists
    if !log_dir.exists() {
        std::fs::create_dir_all(log_dir)?;
    }
    
    // Create log file with timestamp
    let timestamp = Local::now().format("%Y%m%d_%H%M%S");
    let log_file = log_dir.join(format!("hx-cfd_{}.log", timestamp));
    
    // Open log file for writing
    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_file)?;
    
    // Set up env_logger to write to both stdout and file
    env_logger::Builder::new()
        .filter_level(LevelFilter::Info)
        .format(|buf, record| {
            writeln!(
                buf,
                "{} [{}] {} - {}",
                Local::now().format("%Y-%m-%d %H:%M:%S%.3f"),
                record.level(),
                record.target(),
                record.args()
            )
        })
        .target(env_logger::Target::Pipe(Box::new(file)))
        .init();
    
    info!("Logging initialized. Log file: {:?}", log_file);
    Ok(())
}

/// Log an info message
pub fn log_info(message: &str) {
    info!("{}", message);
}

/// Log an error message
pub fn log_error(message: &str) {
    error!("{}", message);
}

/// Get the path to the current log file
pub fn get_log_path(log_dir: &PathBuf) -> Option<PathBuf> {
    std::fs::read_dir(log_dir)
        .ok()?
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            entry.path().extension().map_or(false, |ext| ext == "log")
        })
        .filter(|entry| {
            entry.file_name().to_string_lossy().starts_with("hx-cfd_")
        })
        .max_by_key(|entry| {
            entry.metadata().ok().and_then(|m| m.modified().ok())
        })
        .map(|entry| entry.path())
}