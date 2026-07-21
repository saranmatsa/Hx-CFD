//! Build script for Tauri application
//!
//! This script handles:
//! - Building the frontend (React/Vite)
//! - Staging the managed local Python backend runtime for release bundles
//! - Optionally building a PyInstaller sidecar for diagnostic distribution
//! - Copying resources to the correct locations

use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    // Tauri validates resource globs while its build helper runs, including
    // during debug-only `cargo check`. Keep a tiny generated marker so the
    // release-only runtime tree has a valid resource root in those builds.
    ensure_backend_runtime_resource_root(&manifest_dir);

    // Generate Tauri's IPC permission manifests and embed capability files.
    // The desktop UI uses the native dialog plugin to let engineers select
    // local CAD input, so its narrowly scoped capability must be compiled
    // into the application context.
    tauri_build::build();

    // Tell cargo to rerun if these files change
    println!("cargo:rerun-if-changed=frontend/package.json");
    println!("cargo:rerun-if-changed=frontend/vite.config.ts");
    println!("cargo:rerun-if-changed=frontend/src");
    println!("cargo:rerun-if-changed=backend");
    println!("cargo:rerun-if-changed=build.py");
    println!("cargo:rerun-if-changed=backend.spec");
    println!("cargo:rerun-if-env-changed=HX_CFD_BUILD_FROZEN_SIDECAR");
    println!("cargo:rerun-if-env-changed=HX_CFD_SKIP_SIDECAR_BUILD");

    let profile = env::var("PROFILE").unwrap_or_else(|_| "debug".to_string());

    // Build frontend
    if profile == "release" {
        build_frontend(&manifest_dir);
        // Stage the primary self-contained managed Python backend. A frozen
        // sidecar remains an optional compact artifact, never a prerequisite
        // for Tauri to start local engineering work.
        stage_backend_runtime(&manifest_dir);
    }

    // The managed source/runtime resource is the default desktop backend.
    // Freezing the same stack with PyInstaller is strictly opt-in because it
    // is expensive and can fail for environment-specific native packages.
    // A successful frozen sidecar is still bundled as an alternate artifact,
    // but it is never required for HX CFD to launch.
    if env::var_os("HX_CFD_BUILD_FROZEN_SIDECAR").is_some()
        && env::var_os("HX_CFD_SKIP_SIDECAR_BUILD").is_none()
    {
        build_backend_sidecar(&manifest_dir, &profile);
    } else {
        println!(
            "cargo:warning=Using managed Python runtime backend; frozen sidecar build is opt-in (set HX_CFD_BUILD_FROZEN_SIDECAR=1)"
        );
    }

    // Copy resources
    copy_resources(&manifest_dir, &profile);
}

fn ensure_backend_runtime_resource_root(manifest_dir: &Path) {
    let runtime_root = manifest_dir.join("bin").join("backend-runtime");
    if runtime_root.exists() {
        return;
    }
    fs::create_dir_all(&runtime_root).expect("Unable to create backend runtime resource root");
    fs::write(
        runtime_root.join("HX_CFD_RUNTIME_PLACEHOLDER.txt"),
        "Release builds replace this marker with the managed backend runtime.\n",
    )
    .expect("Unable to create backend runtime resource marker");
}

fn find_npm() -> PathBuf {
    // Try portable Node.js location first
    if let Ok(temp) = env::var("TEMP") {
        let portable_dir = PathBuf::from(temp)
            .join("node-portable")
            .join("node-v22.14.0-win-x64");
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

fn find_python() -> PathBuf {
    // Honour an explicit build interpreter first. This makes the sidecar use
    // the same managed environment that contains the local engineering stack.
    for variable in ["HX_CFD_PYTHON", "PYTHON"] {
        if let Some(value) = env::var_os(variable) {
            let candidate = PathBuf::from(value);
            if candidate.exists() {
                return candidate;
            }
        }
    }

    if let Some(virtual_env) = env::var_os("VIRTUAL_ENV") {
        let candidate = if cfg!(target_os = "windows") {
            PathBuf::from(virtual_env).join("Scripts/python.exe")
        } else {
            PathBuf::from(virtual_env).join("bin/python")
        };
        if candidate.exists() {
            return candidate;
        }
    }

    // The desktop runtime deliberately uses this managed environment. Prefer
    // the same interpreter while freezing the sidecar so a release build does
    // not accidentally package a globally installed Python missing the CFD
    // dependencies that passed local workflow validation.
    let managed_runtime = if cfg!(target_os = "windows") {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("backend")
            .join(".venv")
            .join("Scripts")
            .join("python.exe")
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("backend")
            .join(".venv")
            .join("bin")
            .join("python")
    };
    if managed_runtime.exists() {
        return managed_runtime;
    }

    if cfg!(target_os = "windows") {
        PathBuf::from("python.exe")
    } else {
        PathBuf::from("python3")
    }
}

fn build_frontend(manifest_dir: &Path) {
    let frontend_dir = manifest_dir.join("frontend");
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
    let backend_dir = manifest_dir.join("backend");
    let bin_dir = manifest_dir.join("bin/backend");
    let bin_deps_dir = manifest_dir.join("bin/backend_deps");
    let spec_file = manifest_dir.join("backend.spec");
    let build_script = manifest_dir.join("build.py");

    println!("cargo:warning=Building Python backend sidecar...");

    // Create output directories
    std::fs::create_dir_all(&bin_dir).expect("Failed to create bin/backend directory");
    std::fs::create_dir_all(&bin_deps_dir).expect("Failed to create bin/backend_deps directory");

    // Package with the managed engineering environment rather than whichever
    // unrelated Python executable happens to appear first on PATH.
    let python_cmd = find_python();

    let python_version = Command::new(&python_cmd)
        .arg("--version")
        .output()
        .expect("Failed to check Python version");

    if !python_version.status.success() {
        println!("cargo:warning=Python not found, skipping backend sidecar build");
        return;
    }

    println!(
        "cargo:warning=Python version: {}",
        String::from_utf8_lossy(&python_version.stdout)
    );

    // Run the build script
    let mut cmd = Command::new(&python_cmd);
    cmd.args([
        build_script.to_str().unwrap(),
        "--profile",
        profile,
        "--backend-dir",
        backend_dir.to_str().unwrap(),
        "--spec-file",
        spec_file.to_str().unwrap(),
        "--output-dir",
        bin_dir.to_str().unwrap(),
        "--work-dir",
        bin_deps_dir.to_str().unwrap(),
    ]);

    println!("cargo:warning=Running build script: {:?}", cmd);

    let status = cmd.status().expect("Failed to run build script");

    if !status.success() {
        // The managed source/runtime resource staged above is an intentional
        // release fallback.  Do not turn a PyInstaller-specific problem into
        // a non-functional desktop build.  Release lookup prefers that
        // fallback, so an old executable cannot mask it either.
        println!(
            "cargo:warning=Backend sidecar build failed; packaging the managed Python runtime fallback instead"
        );
        return;
    }

    // Verify the executable was created
    let exe_name = if cfg!(target_os = "windows") {
        "cfd-backend.exe"
    } else {
        "cfd-backend"
    };
    let exe_path = bin_dir.join(exe_name);

    if !exe_path.exists() {
        println!(
            "cargo:warning=Backend sidecar executable was not produced; packaging the managed Python runtime fallback instead"
        );
        return;
    }

    println!(
        "cargo:warning=Backend sidecar built successfully at {:?}",
        exe_path
    );
}

/// Stage a portable managed Python runtime for release bundles.
///
/// A Windows virtual environment is not portable by itself: its `pyvenv.cfg`
/// points at the build machine's base interpreter.  We therefore ship the
/// backend source, the managed environment and that base CPython runtime as a
/// single resource tree.  `BackendManager` launches the embedded base Python
/// with `PYTHONHOME` and a bootstrap that adds the managed site-packages, so
/// no dependency on a user-installed Python remains.
fn stage_backend_runtime(manifest_dir: &Path) {
    let backend_dir = manifest_dir.join("backend");
    let backend_source = backend_dir.join("src");
    let managed_venv = backend_dir.join(".venv");
    let managed_python = find_python();

    if !backend_source.is_dir() {
        panic!(
            "Cannot stage backend runtime: source directory is missing at {}",
            backend_source.display()
        );
    }
    if !managed_venv.is_dir() {
        panic!(
            "Cannot stage backend runtime: managed environment is missing at {}",
            managed_venv.display()
        );
    }

    let base_python = python_base_prefix(&managed_python).unwrap_or_else(|error| {
        panic!(
            "Cannot stage backend runtime from {}: {error}",
            managed_python.display()
        )
    });
    let base_python_executable = if cfg!(target_os = "windows") {
        base_python.join("python.exe")
    } else {
        base_python.join("bin/python3")
    };
    if !base_python_executable.is_file() {
        panic!(
            "Cannot stage backend runtime: base Python executable is missing at {}",
            base_python_executable.display()
        );
    }

    let runtime_root = manifest_dir.join("bin").join("backend-runtime");
    let staging_root = manifest_dir.join("bin").join("backend-runtime.staging");
    if staging_root.exists() {
        fs::remove_dir_all(&staging_root).unwrap_or_else(|error| {
            panic!(
                "Unable to remove incomplete backend runtime staging directory {}: {error}",
                staging_root.display()
            )
        });
    }
    fs::create_dir_all(&staging_root).unwrap_or_else(|error| {
        panic!(
            "Unable to create backend runtime staging directory {}: {error}",
            staging_root.display()
        )
    });

    copy_tree(&backend_source, &staging_root.join("backend").join("src")).unwrap_or_else(|error| {
        panic!(
            "Unable to stage backend source from {}: {error}",
            backend_source.display()
        )
    });
    copy_tree(&managed_venv, &staging_root.join("venv")).unwrap_or_else(|error| {
        panic!(
            "Unable to stage managed Python environment from {}: {error}",
            managed_venv.display()
        )
    });
    copy_tree(&base_python, &staging_root.join("python")).unwrap_or_else(|error| {
        panic!(
            "Unable to stage base Python runtime from {}: {error}",
            base_python.display()
        )
    });

    fs::write(
        staging_root.join("launch_backend.py"),
        r#"# Generated by HX CFD's build script. This file is intentionally local-only.
from pathlib import Path
import runpy
import site
import sys

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "backend" / "src"
SITE_PACKAGES = ROOT / "venv" / "Lib" / "site-packages"
site.addsitedir(str(SITE_PACKAGES))
sys.path.insert(0, str(SOURCE_ROOT))
BACKEND_MAIN = SOURCE_ROOT / "cfd_backend" / "main.py"
sys.argv = [str(BACKEND_MAIN)]
runpy.run_path(str(BACKEND_MAIN), run_name="__main__")
"#,
    )
    .expect("Unable to write managed backend runtime bootstrap");
    fs::write(
        staging_root.join("HX_CFD_RUNTIME"),
        "HX CFD managed backend runtime v1\n",
    )
    .expect("Unable to write managed backend runtime marker");

    if runtime_root.exists() {
        fs::remove_dir_all(&runtime_root).unwrap_or_else(|error| {
            panic!(
                "Unable to replace staged backend runtime {}: {error}",
                runtime_root.display()
            )
        });
    }
    fs::rename(&staging_root, &runtime_root).unwrap_or_else(|error| {
        panic!(
            "Unable to finalize staged backend runtime {}: {error}",
            runtime_root.display()
        )
    });

    println!(
        "cargo:warning=Staged managed backend runtime fallback at {}",
        runtime_root.display()
    );
}

fn python_base_prefix(python: &Path) -> Result<PathBuf, String> {
    let output = Command::new(python)
        .env_remove("PYTHONHOME")
        .env_remove("PYTHONPATH")
        .args(["-c", "import sys; print(sys.base_prefix)"])
        .output()
        .map_err(|error| format!("unable to run Python: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "Python exited with {}: {}",
            output.status,
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let prefix = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if prefix.is_empty() {
        return Err("Python did not report sys.base_prefix".to_string());
    }
    Ok(PathBuf::from(prefix))
}

fn copy_tree(source: &Path, destination: &Path) -> std::io::Result<()> {
    fs::create_dir_all(destination)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let source_path = entry.path();
        let destination_path = destination.join(entry.file_name());
        let metadata = entry.metadata()?;
        if metadata.is_dir() {
            copy_tree(&source_path, &destination_path)?;
        } else if metadata.is_file() {
            fs::copy(&source_path, &destination_path)?;
        }
    }
    Ok(())
}

fn copy_resources(manifest_dir: &Path, profile: &str) {
    let resources_dir = manifest_dir.join("resources");
    let target_dir = if profile == "release" {
        manifest_dir.join("target/release")
    } else {
        manifest_dir.join("target/debug")
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
