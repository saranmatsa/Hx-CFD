"""
Platform detection module.

Automatically detects the operating environment and provides
platform-specific information.
"""

import platform
import os
import subprocess
import shutil
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .base import DependencyInfo, DependencyCategory, DependencyPriority, DependencyStatus


class Platform(str, Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    LINUX = "linux"
    WSL = "wsl"           # Windows Subsystem for Linux
    MACOS = "macos"
    UNKNOWN = "unknown"


class PackageManager(str, Enum):
    """Supported package managers."""
    APT = "apt"
    DNF = "dnf"
    PACMAN = "pacman"
    YUM = "yum"
    CHOCO = "choco"
    WINGET = "winget"
    BREW = "brew"
    PIP = "pip"
    UV = "uv"
    PNPM = "pnpm"
    NPM = "npm"
    YARN = "yarn"


class PlatformInfo(BaseModel):
    """Information about the current platform."""
    platform: Platform
    os_name: str
    os_version: str
    arch: str
    hostname: str
    python_version: str
    python_executable: str
    
    # Package managers available
    available_managers: List[PackageManager] = []
    
    # GPU info
    has_nvidia_gpu: bool = False
    cuda_version: Optional[str] = None
    nvidia_driver_version: Optional[str] = None
    
    # WSL info
    is_wsl: bool = False
    wsl_version: Optional[int] = None
    
    # Environment variables
    env_vars: Dict[str, str] = {}
    
    # Paths
    home_dir: str
    temp_dir: str
    app_data_dir: Optional[str] = None
    
    model_config = {"from_attributes": True}


class PlatformDetector:
    """
    Detects the current platform and its capabilities.
    
    This class provides information about the operating environment
    to help the Dependency Manager make informed decisions about
    installation methods and configuration.
    """
    
    _instance: Optional["PlatformDetector"] = None
    _info: Optional[PlatformInfo] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def detect(self, force: bool = False) -> PlatformInfo:
        """
        Detect the current platform.
        
        Args:
            force: Force re-detection even if cached.
            
        Returns:
            PlatformInfo with platform details.
        """
        if self._info is None or force:
            self._info = self._detect_platform()
        return self._info
    
    def _detect_platform(self) -> PlatformInfo:
        """Perform platform detection."""
        system = platform.system().lower()
        
        # Detect WSL first
        is_wsl, wsl_version = self._detect_wsl()
        
        if system == "linux" or is_wsl:
            if is_wsl:
                platform_type = Platform.WSL
            else:
                platform_type = Platform.LINUX
            os_name = "Linux"
            os_version = self._get_linux_version()
        elif system == "darwin":
            platform_type = Platform.MACOS
            os_name = "macOS"
            os_version = platform.mac_ver()[0] or "Unknown"
        elif system == "windows" or system == "nt":
            platform_type = Platform.WINDOWS
            os_name = "Windows"
            os_version = platform.win32_ver()[0] or "Unknown"
        else:
            platform_type = Platform.UNKNOWN
            os_name = system
            os_version = "Unknown"
        
        # Detect available package managers
        managers = self._detect_package_managers()
        
        # Detect GPU
        has_nvidia, cuda_ver, driver_ver = self._detect_gpu()
        
        # Get paths
        home = os.path.expanduser("~")
        temp = os.getenv("TEMP") or os.getenv("TMP") or "/tmp"
        
        app_data = None
        if platform_type == Platform.WINDOWS:
            app_data = os.getenv("APPDATA")
        
        return PlatformInfo(
            platform=platform_type,
            os_name=os_name,
            os_version=os_version,
            arch=platform.machine(),
            hostname=platform.node(),
            python_version=platform.python_version(),
            python_executable=platform.python_executable(),
            available_managers=managers,
            has_nvidia_gpu=has_nvidia,
            cuda_version=cuda_ver,
            nvidia_driver_version=driver_ver,
            is_wsl=is_wsl,
            wsl_version=wsl_version,
            env_vars=dict(os.environ),
            home_dir=home,
            temp_dir=temp,
            app_data_dir=app_data,
        )
    
    def _detect_wsl(self) -> tuple[bool, Optional[int]]:
        """Detect if running in WSL and return version."""
        try:
            # Check /proc/version for WSL signature
            if os.path.exists("/proc/version"):
                with open("/proc/version", "r") as f:
                    content = f.read().lower()
                    if "microsoft" in content or "wsl" in content:
                        # WSL2 has specific indicators
                        if "microsoft-standard" in content:
                            return True, 2
                        return True, 1
        except Exception:
            pass
        
        # Check for WSLENV environment variable (set in WSL)
        if os.getenv("WSLENV"):
            return True, None
        
        return False, None
    
    def _get_linux_version(self) -> str:
        """Get Linux distribution version."""
        try:
            # Try /etc/os-release
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=", 1)[1].strip().strip('"')
            
            # Try lsb_release
            result = subprocess.run(
                ["lsb_release", "-ds"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        # Fallback to uname
        result = subprocess.run(
            ["uname", "-r"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        
        return "Unknown Linux"
    
    def _detect_package_managers(self) -> List[PackageManager]:
        """Detect available package managers."""
        managers = []
        
        # Check for each package manager
        checks = {
            PackageManager.APT: ["apt-get", "apt"],
            PackageManager.DNF: ["dnf"],
            PackageManager.PACMAN: ["pacman"],
            PackageManager.YUM: ["yum"],
            PackageManager.CHOCO: ["choco"],
            PackageManager.WINGET: ["winget"],
            PackageManager.BREW: ["brew"],
            PackageManager.PIP: ["pip", "pip3"],
            PackageManager.UV: ["uv"],
            PackageManager.PNPM: ["pnpm"],
            PackageManager.NPM: ["npm"],
            PackageManager.YARN: ["yarn"],
        }
        
        for manager, commands in checks.items():
            for cmd in commands:
                if shutil.which(cmd):
                    managers.append(manager)
                    break
        
        return managers
    
    def _detect_gpu(self) -> tuple[bool, Optional[str], Optional[str]]:
        """Detect NVIDIA GPU and CUDA."""
        has_nvidia = False
        cuda_version = None
        driver_version = None
        
        try:
            # Check for nvidia-smi
            if shutil.which("nvidia-smi"):
                has_nvidia = True
                
                # Get driver version
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    driver_version = result.stdout.strip().split("\n")[0]
                
                # Get CUDA version
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    cuda_version = result.stdout.strip().split("\n")[0]
            
            # Check nvcc
            if shutil.which("nvcc"):
                result = subprocess.run(
                    ["nvcc", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # Parse version from output
                    for line in result.stdout.split("\n"):
                        if "release" in line.lower():
                            parts = line.split("release")[-1].strip().split(",")
                            if parts:
                                cuda_version = parts[0].strip()
                                break
        except Exception:
            pass
        
        return has_nvidia, cuda_version, driver_version
    
    def get_install_command(self, tool: str) -> Optional[List[str]]:
        """
        Get the appropriate installation command for a tool on this platform.
        
        Args:
            tool: Name of the tool to install.
            
        Returns:
            Command as list of strings, or None if not supported.
        """
        info = self.detect()
        
        # Platform-specific installation commands
        commands = {
            Platform.WINDOWS: {
                "git": ["winget", "install", "Git.Git"],
                "docker": ["winget", "install", "Docker.DockerDesktop"],
                "node": ["winget", "install", "OpenJS.NodeJS.LTS"],
            },
            Platform.LINUX: {
                "git": ["apt-get", "install", "-y", "git"],
                "docker": ["apt-get", "install", "-y", "docker.io"],
                "node": ["apt-get", "install", "-y", "nodejs", "npm"],
            },
            Platform.WSL: {
                "git": ["apt-get", "install", "-y", "git"],
                "docker": ["apt-get", "install", "-y", "docker.io"],
                "node": ["apt-get", "install", "-y", "nodejs", "npm"],
            },
            Platform.MACOS: {
                "git": ["brew", "install", "git"],
                "docker": ["brew", "install", "--cask", "docker"],
                "node": ["brew", "install", "node"],
            },
        }
        
        platform_commands = commands.get(info.platform, {})
        return platform_commands.get(tool.lower())
    
    def get_python_install_command(self) -> List[str]:
        """
        Get the command to install a Python package on this platform.
        
        Returns:
            Command as list of strings.
        """
        info = self.detect()
        
        # Prefer uv if available
        if PackageManager.UV in info.available_managers:
            return ["uv", "pip", "install"]
        
        return ["pip", "install"]
    
    def get_node_install_command(self) -> List[str]:
        """
        Get the command to install a Node package on this platform.
        
        Returns:
            Command as list of strings.
        """
        info = self.detect()
        
        # Prefer pnpm if available
        if PackageManager.PNPM in info.available_managers:
            return ["pnpm", "add"]
        elif PackageManager.NPM in info.available_managers:
            return ["npm", "install"]
        elif PackageManager.YARN in info.available_managers:
            return ["yarn", "add"]
        
        return ["npm", "install"]