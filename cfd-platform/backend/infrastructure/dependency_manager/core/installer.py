"""
Installer Engine for managing dependency installation.

The installer provides a unified interface for installing dependencies
across different platforms and package managers.
"""

import os
import sys
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .base import ToolAdapter, DependencyInfo, DependencyStatus, DependencyCategory
from .platform import PlatformDetector, Platform, PackageManager


class InstallResult(str, Enum):
    """Result of an installation attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    ALREADY_INSTALLED = "already_installed"
    NOT_SUPPORTED = "not_supported"
    PARTIAL = "partial"


@dataclass
class InstallProgress:
    """Progress information for an installation."""
    tool_name: str
    stage: str  # "detecting", "downloading", "installing", "configuring", "verifying"
    progress: float  # 0.0 to 1.0
    message: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class InstallerEngine:
    """
    Unified installer for all dependencies.
    
    The installer handles:
    - Platform detection and adaptation
    - Package manager selection
    - Installation with progress tracking
    - Verification after installation
    - Rollback on failure (where supported)
    """
    
    def __init__(self):
        self.platform_detector = PlatformDetector()
        self._progress_callbacks: List[Callable[[InstallProgress], None]] = []
        self._install_log: List[Dict[str, Any]] = []
    
    def add_progress_callback(self, callback: Callable[[InstallProgress], None]) -> None:
        """Add a callback for installation progress updates."""
        self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[InstallProgress], None]) -> None:
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def _emit_progress(self, progress: InstallProgress) -> None:
        """Emit progress to all callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception:
                pass  # Don't let callback errors break installation
    
    def install(self, adapter: ToolAdapter, **kwargs) -> tuple[InstallResult, str]:
        """
        Install a tool using its adapter.
        
        Args:
            adapter: The tool adapter to install.
            **kwargs: Additional installation options.
            
        Returns:
            Tuple of (result, message).
        """
        tool_name = adapter.name
        
        # Check if already installed
        if adapter.detect():
            return InstallResult.ALREADY_INSTALLED, f"{tool_name} is already installed"
        
        # Emit progress
        self._emit_progress(InstallProgress(
            tool_name=tool_name,
            stage="detecting",
            progress=0.0,
            message=f"Detecting installation method for {tool_name}"
        ))
        
        try:
            # Attempt installation
            self._emit_progress(InstallProgress(
                tool_name=tool_name,
                stage="installing",
                progress=0.5,
                message=f"Installing {tool_name}"
            ))
            
            result = adapter.install(**kwargs)
            
            if result:
                # Verify installation
                self._emit_progress(InstallProgress(
                    tool_name=tool_name,
                    stage="verifying",
                    progress=0.9,
                    message=f"Verifying {tool_name} installation"
                ))
                
                if adapter.detect():
                    self._log_install(tool_name, InstallResult.SUCCESS)
                    return InstallResult.SUCCESS, f"Successfully installed {tool_name}"
                else:
                    self._log_install(tool_name, InstallResult.PARTIAL)
                    return InstallResult.PARTIAL, f"{tool_name} installed but verification failed"
            else:
                self._log_install(tool_name, InstallResult.FAILED)
                return InstallResult.FAILED, f"Installation of {tool_name} failed"
                
        except NotImplementedError:
            return InstallResult.NOT_SUPPORTED, f"{tool_name} does not support automatic installation"
        except Exception as e:
            self._log_install(tool_name, InstallResult.FAILED, str(e))
            return InstallResult.FAILED, f"Installation of {tool_name} failed: {str(e)}"
    
    def install_python_package(
        self,
        package: str,
        version: Optional[str] = None,
        extras: Optional[List[str]] = None,
        upgrade: bool = False
    ) -> tuple[InstallResult, str]:
        """
        Install a Python package using pip or uv.
        
        Args:
            package: Package name.
            version: Specific version to install.
            extras: Extra requirements (e.g., ["dev", "test"]).
            upgrade: Whether to upgrade if already installed.
            
        Returns:
            Tuple of (result, message).
        """
        platform_info = self.platform_detector.detect()
        
        # Build command
        cmd = self.platform_detector.get_python_install_command()
        
        if upgrade:
            cmd.append("--upgrade")
        
        if version:
            cmd.append(f"{package}=={version}")
        else:
            cmd.append(package)
        
        if extras:
            cmd[0] = cmd[0].replace("install", "install ")  # Keep base command
            # Reconstruct with extras
            cmd = self.platform_detector.get_python_install_command()
            if upgrade:
                cmd.append("--upgrade")
            pkg_spec = package
            if extras:
                pkg_spec += f"[{','.join(extras)}]"
            if version:
                pkg_spec += f"=={version}"
            cmd.append(pkg_spec)
        
        self._emit_progress(InstallProgress(
            tool_name=package,
            stage="installing",
            progress=0.5,
            message=f"Installing {package} via {' '.join(cmd)}"
        ))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self._log_install(package, InstallResult.SUCCESS, "pip/uv")
                return InstallResult.SUCCESS, f"Successfully installed {package}"
            else:
                error = result.stderr or "Unknown error"
                self._log_install(package, InstallResult.FAILED, error)
                return InstallResult.FAILED, f"Failed to install {package}: {error}"
                
        except subprocess.TimeoutExpired:
            return InstallResult.FAILED, f"Installation of {package} timed out"
        except Exception as e:
            return InstallResult.FAILED, f"Failed to install {package}: {str(e)}"
    
    def install_platform_tool(
        self,
        tool: str,
        method: Optional[str] = None
    ) -> tuple[InstallResult, str]:
        """
        Install a platform-level tool (git, docker, etc.).
        
        Args:
            tool: Tool name.
            method: Specific installation method (winget, apt, brew, etc.).
            
        Returns:
            Tuple of (result, message).
        """
        platform_info = self.platform_detector.detect()
        
        # Get installation command
        if method:
            cmd = self._get_command_for_method(tool, method)
        else:
            cmd = self.platform_detector.get_install_command(tool)
        
        if cmd is None:
            return InstallResult.NOT_SUPPORTED, f"No installation method available for {tool} on {platform_info.platform.value}"
        
        self._emit_progress(InstallProgress(
            tool_name=tool,
            stage="installing",
            progress=0.5,
            message=f"Installing {tool} via {' '.join(cmd)}"
        ))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                self._log_install(tool, InstallResult.SUCCESS, method or "auto")
                return InstallResult.SUCCESS, f"Successfully installed {tool}"
            else:
                error = result.stderr or "Unknown error"
                self._log_install(tool, InstallResult.FAILED, error)
                return InstallResult.FAILED, f"Failed to install {tool}: {error}"
                
        except subprocess.TimeoutExpired:
            return InstallResult.FAILED, f"Installation of {tool} timed out"
        except Exception as e:
            return InstallResult.FAILED, f"Failed to install {tool}: {str(e)}"
    
    def _get_command_for_method(self, tool: str, method: str) -> Optional[List[str]]:
        """Get installation command for a specific method."""
        commands = {
            "winget": {
                "git": ["winget", "install", "Git.Git"],
                "docker": ["winget", "install", "Docker.DockerDesktop"],
                "node": ["winget", "install", "OpenJS.NodeJS.LTS"],
            },
            "apt": {
                "git": ["apt-get", "install", "-y", "git"],
                "docker": ["apt-get", "install", "-y", "docker.io"],
                "node": ["apt-get", "install", "-y", "nodejs", "npm"],
            },
            "brew": {
                "git": ["brew", "install", "git"],
                "docker": ["brew", "install", "--cask", "docker"],
                "node": ["brew", "install", "node"],
            },
        }
        
        return commands.get(method, {}).get(tool.lower())
    
    def _log_install(self, tool: str, result: InstallResult, details: str = "") -> None:
        """Log an installation attempt."""
        self._install_log.append({
            "tool": tool,
            "result": result.value,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_install_log(self) -> List[Dict[str, Any]]:
        """Get the installation log."""
        return list(self._install_log)
    
    def clear_install_log(self) -> None:
        """Clear the installation log."""
        self._install_log.clear()
    
    def verify_installation(self, adapter: ToolAdapter) -> bool:
        """
        Verify that a tool is correctly installed.
        
        Args:
            adapter: The tool adapter to verify.
            
        Returns:
            True if verified, False otherwise.
        """
        try:
            result = adapter.verify()
            return result.healthy
        except Exception:
            return False