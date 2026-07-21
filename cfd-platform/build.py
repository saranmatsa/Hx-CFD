#!/usr/bin/env python3
"""
Build script for Python backend sidecar.
This script is called from build.rs to build the backend using PyInstaller.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, cwd=None, env=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def check_python():
    """Check if Python is available."""
    # Build with the interpreter that started this script. Resolving a second
    # Python executable from PATH can select a different site-packages tree
    # and produce a sidecar missing FastAPI or CFD engines.
    python_cmd = sys.executable
    result = run_command([python_cmd, "--version"])
    if result.returncode != 0:
        print("Python not found!")
        return None
    print(f"Found Python: {result.stdout.strip()}")
    return python_cmd


def install_pyinstaller(python_cmd):
    """Install PyInstaller if not available."""
    result = run_command([python_cmd, "-m", "PyInstaller", "--version"])
    if result.returncode == 0:
        print("PyInstaller already installed")
        return True
    
    print("Installing PyInstaller...")
    result = run_command([python_cmd, "-m", "pip", "install", "pyinstaller"])
    return result.returncode == 0


def build_backend(python_cmd, backend_dir, spec_file, output_dir, work_dir, profile):
    """Build the backend using PyInstaller."""
    print(f"Building backend with profile: {profile}")
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        python_cmd, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath", str(output_dir),
        "--workpath", str(work_dir / "build"),
    ]
    
    # A spec file owns executable options such as UPX/strip. PyInstaller
    # rejects ``--strip`` and ``--optimize`` when a ``.spec`` argument is
    # present, which previously made every release sidecar build fail before
    # the Tauri package could contain a current backend.

    cmd.append(str(spec_file))
    
    result = run_command(cmd, cwd=backend_dir)
    return result.returncode == 0


def verify_build(output_dir):
    """Verify the build produced the expected executable."""
    exe_name = "cfd-backend.exe" if sys.platform == "win32" else "cfd-backend"
    exe_path = output_dir / exe_name
    
    if exe_path.exists():
        print(f"Build successful! Executable at: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        return True
    else:
        print(f"Build failed! Executable not found at: {exe_path}")
        return False


def main():
    # Get arguments
    import argparse
    parser = argparse.ArgumentParser(description="Build Python backend sidecar")
    parser.add_argument("--profile", choices=["debug", "release"], default="debug")
    parser.add_argument("--backend-dir", type=Path, required=True)
    parser.add_argument("--spec-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    args.backend_dir = args.backend_dir.resolve()
    args.spec_file = args.spec_file.resolve()
    args.output_dir = args.output_dir.resolve()
    args.work_dir = args.work_dir.resolve()
    
    print("=" * 60)
    print("Building CFD Platform Python Backend Sidecar")
    print("=" * 60)
    print(f"Profile: {args.profile}")
    print(f"Backend dir: {args.backend_dir}")
    print(f"Spec file: {args.spec_file}")
    print(f"Output dir: {args.output_dir}")
    print(f"Work dir: {args.work_dir}")
    print()
    
    # Check Python
    python_cmd = check_python()
    if not python_cmd:
        sys.exit(1)
    
    # Install PyInstaller
    if not install_pyinstaller(python_cmd):
        print("Failed to install PyInstaller!")
        sys.exit(1)
    
    # Build backend
    if not build_backend(python_cmd, args.backend_dir, args.spec_file, args.output_dir, args.work_dir, args.profile):
        print("Backend build failed!")
        sys.exit(1)
    
    # Verify build
    if not verify_build(args.output_dir):
        sys.exit(1)
    
    print("=" * 60)
    print("Backend sidecar build completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
