//! Build script for Tauri application
//!
//! This script handles:
//! - Building the frontend (React/Vite)
//! - Building the Python backend sidecar using PyInstaller
//! - Copying resources to the correct locations

use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

fn main() {
    // Tell cargo to rerun if these files change
    println!("cargo:rerun-if-changed=../frontend/package.json");
    println!("cargo:rerun-if-changed=../frontend/vite.config.ts");
    println!("cargo:rerun-if-changed=../frontend/src");
    println!("cargo:rerun-if-changed=../backend");
    println!("cargo:rerun-if-changed=build.py");
    println!("cargo:rerun-if-changed=backend.spec");

    let profile = env::var("PROFILE").unwrap_or_else(|_| "debug".to_string());
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());

    // Build frontend
    if profile == "release" {
        build_frontend(&manifest_dir);
    }

    // Build Python backend sidecar
    build_backend_sidecar(&manifest_dir, &profile);

    // Copy resources
    copy_resources(&manifest_dir, &profile);
}

fn find_npm() -> PathBuf {
    // Try portable Node.js location first
    if let Ok(temp) = env::var("TEMP") {
        let portable_dir = PathBuf::from(temp).join("node-portable").join("node-v22.14.0-win-x64");
        let portable_npm_cmd = portable_dir.join("npm.cmd");
        if portable_npm_cmd.exists() {
            return portable_npm_cmd;
        }
        let portable_npm_exe = portable_dir.join("npm.exe");
        if portable_npm_exe.exists() {
            return portable_npm_exe;
        }
    }
    // Fall back to PATH
    PathBuf::from("npm")
}

fn build_frontend(manifest_dir: &Path) {
    let frontend_dir = manifest_dir.join("../frontend");
    let dist_dir = frontend_dir.join("dist");

    println!("cargo:warning=Building frontend...");

    let npm_cmd = find_npm();
    println!("cargo:warning=Using npm at: {}", npm_cmd.display());

    // Check if node_modules exists
    if !frontend_dir.join("node_modules").exists() {
        println!("cargo:warning=Installing frontend dependencies...");
        let status = Command::new(&npm_cmd)
            .arg("ci")
            .current_dir(&frontend_dir)
            .status()
            .expect("Failed to run npm ci");
        if !status.success() {
            panic!("npm ci failed");
        }
    }

    // Build frontend
    let status = Command::new(&npm_cmd)
        .arg("run")
        .arg("build")
        .current_dir(&frontend_dir)
        .status()
        .expect("Failed to run npm run build");

    if !status.success() {
        panic!("Frontend build failed");
    }

    // Verify dist directory exists
    if !dist_dir.exists() {
        panic!("Frontend dist directory not found after build");
    }

    println!("cargo:warning=Frontend built successfully");
}

fn build_backend_sidecar(manifest_dir: &Path, profile: &str) {
    let backend_dir = manifest_dir.join("../backend");
    let bin_dir = manifest_dir.join("../bin/backend");
    let bin_deps_dir = manifest_dir.join("../bin/backend_deps");
    let spec_file = manifest_dir.join("backend.spec");
    let build_script = manifest_dir.join("build.py");

    println!("cargo:warning=Building Python backend sidecar...");

    // Create output directories
    std::fs::create_dir_all(&bin_dir).expect("Failed to create bin/backend directory");
    std::fs::create_dir_all(&bin_deps_dir).expect("Failed to create bin/backend_deps directory");

    // Check if Python is available
    let python_cmd = if cfg!(target_os = "windows") { "python" } else { "python3" };

    let python_version = Command::new(python_cmd)
        .arg("--version")
        .output()
        .expect("Failed to check Python version");

    if !python_version.status.success() {
        println!("cargo:warning=Python not found, skipping backend sidecar build");
        return;
    }

    println!("cargo:warning=Python version: {}", String::from_utf8_lossy(&python_version.stdout));

    // Run the build script
    let mut cmd = Command::new(python_cmd);
    cmd.args([
        build_script.to_str().unwrap(),
        "--profile", profile,
        "--backend-dir", backend_dir.to_str().unwrap(),
        "--spec-file", spec_file.to_str().unwrap(),
        "--output-dir", bin_dir.to_str().unwrap(),
        "--work-dir", bin_deps_dir.to_str().unwrap(),
    ]);

    println!("cargo:warning=Running build script: {:?}", cmd);

    let status = cmd.status().expect("Failed to run build script");

    if !status.success() {
        panic!("Backend sidecar build failed");
    }

    // Verify the executable was created
    let exe_name = if cfg!(target_os = "windows") { "cfd-backend.exe" } else { "cfd-backend" };
    let exe_path = bin_dir.join("cfd-backend").join(exe_name);

    if !exe_path.exists() {
        panic!("Backend executable not found at {:?}", exe_path);
    }

    println!("cargo:warning=Backend sidecar built successfully at {:?}", exe_path);
}

fn copy_resources(manifest_dir: &Path, profile: &str) {
    let resources_dir = manifest_dir.join("../resources");
    let target_dir = if profile == "release" {
        manifest_dir.join("../../target/release")
    } else {
        manifest_dir.join("../../target/debug")
    };

    if resources_dir.exists() {
        println!("cargo:warning=Copying resources...");

        let mut copy_options = fs_extra::dir::CopyOptions::new();
        copy_options.overwrite = true;
        copy_options.copy_inside = true;

        fs_extra::dir::copy(&resources_dir, &target_dir, &copy_options)
            .expect("Failed to copy resources");

        println!("cargo:warning=Resources copied successfully");
    }
}