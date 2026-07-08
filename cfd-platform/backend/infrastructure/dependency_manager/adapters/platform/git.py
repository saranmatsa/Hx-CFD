"""
Git Adapter for dependency management.

Git is a distributed version control system.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import shutil

from ..core.base import (
    ToolAdapter,
    DependencyInfo,
    DependencyStatus,
    DependencyCategory,
    DiagnosticResult,
    DiagnosticSeverity
)
from ..core.platform import Platform, PlatformDetector


class GitAdapter(ToolAdapter):
    """Adapter for Git."""
    
    name = "git"
    display_name = "Git"
    description = "Distributed version control system"
    category = DependencyCategory.PLATFORM
    homepage = "https://git-scm.com/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
    
    def get_info(self) -> DependencyInfo:
        """Get Git information."""
        version = self.get_version()
        status = self._determine_status(version)
        
        return DependencyInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            category=self.category,
            status=status,
            installed_version=version,
            required_version=None,
            install_path=self._find_installation_path(),
            homepage=self.homepage,
            documentation="https://git-scm.com/doc",
            dependencies=self._get_dependencies()
        )
    
    def _determine_status(self, version: Optional[str]) -> DependencyStatus:
        """Determine status based on version."""
        if version is None:
            return DependencyStatus.MISSING
        if self.verify().healthy:
            return DependencyStatus.INSTALLED
        return DependencyStatus.BROKEN
    
    def _find_installation_path(self) -> Optional[Path]:
        """Find Git installation path."""
        git_path = shutil.which("git")
        if git_path:
            return Path(git_path).parent
        return None
    
    def get_version(self) -> Optional[str]:
        """Get Git version."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return self._parse_version(result.stdout)
            
            return None
        except Exception:
            return None
    
    def _parse_version(self, output: str) -> Optional[str]:
        """Parse version from output."""
        import re
        match = re.search(r"git version ([0-9]+\.[0-9]+(?:\.[0-9]+)?)", output)
        if match:
            return match.group(1)
        return None
    
    def verify(self) -> DiagnosticResult:
        """Verify Git installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="Git not found",
                    errors=["Git executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if git config works
            result = subprocess.run(
                ["git", "config", "--list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return DiagnosticResult(
                    healthy=False,
                    message="Git configuration failed",
                    errors=[result.stderr],
                    warnings=[],
                    severity=DiagnosticSeverity.WARNING
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"Git {version} is installed",
                errors=[],
                warnings=[],
                severity=DiagnosticSeverity.INFO
            )
        except Exception as e:
            return DiagnosticResult(
                healthy=False,
                message=f"Verification failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                severity=DiagnosticSeverity.ERROR
            )
    
    def install(self, **kwargs) -> bool:
        """Install Git."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install Git on Windows."""
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "Git.Git", "-e", "--source", "winget"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try Chocolatey
            result = subprocess.run(
                ["choco", "install", "git", "-y"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install Git on macOS."""
        try:
            # Git is usually pre-installed on macOS
            # Try to update via brew if available
            result = subprocess.run(
                ["brew", "install", "git"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install Git on Linux."""
        try:
            # Try apt-get
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "git"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try yum/dnf
            result = subprocess.run(
                ["sudo", "yum", "install", "-y", "git"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try dnf
            result = subprocess.run(
                ["sudo", "dnf", "install", "-y", "git"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure Git."""
        valid_keys = {"user_name", "user_email", "default_branch", "editor"}
        for key in settings:
            if key not in valid_keys:
                return False
        
        # Apply configuration
        try:
            if "user_name" in settings:
                subprocess.run(
                    ["git", "config", "--global", "user.name", settings["user_name"]],
                    check=True
                )
            if "user_email" in settings:
                subprocess.run(
                    ["git", "config", "--global", "user.email", settings["user_email"]],
                    check=True
                )
            if "default_branch" in settings:
                subprocess.run(
                    ["git", "config", "--global", "init.defaultBranch", settings["default_branch"]],
                    check=True
                )
            return True
        except Exception:
            return False
    
    def _get_dependencies(self) -> List[Any]:
        """Get Git dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run Git diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            # Check user configuration
            try:
                name_result = subprocess.run(
                    ["git", "config", "--global", "user.name"],
                    capture_output=True,
                    text=True
                )
                if name_result.returncode == 0 and name_result.stdout.strip():
                    metrics["user_name"] = name_result.stdout.strip()
                else:
                    warnings.append("Git user.name not configured")
                
                email_result = subprocess.run(
                    ["git", "config", "--global", "user.email"],
                    capture_output=True,
                    text=True
                )
                if email_result.returncode == 0 and email_result.stdout.strip():
                    metrics["user_email"] = email_result.stdout.strip()
                else:
                    warnings.append("Git user.email not configured")
            except Exception:
                warnings.append("Could not check Git configuration")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result