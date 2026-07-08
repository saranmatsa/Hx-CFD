"""Process management for local services."""

import os
import sys
import signal
import subprocess
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages local service processes."""

    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}
        self._start_times: Dict[str, datetime] = {}

    def start_process(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        port: Optional[int] = None,
    ) -> Optional[subprocess.Popen]:
        """
        Start a new process.

        Args:
            name: Service name
            command: Command to execute
            args: Command arguments
            env: Environment variables
            working_dir: Working directory
            port: Port the service will use

        Returns:
            Process object or None if failed
        """
        if name in self._processes:
            logger.warning(f"Process '{name}' is already running")
            return self._processes[name]

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        if port:
            process_env["PORT"] = str(port)
            process_env["CFD_SERVICE_PORT"] = str(port)

        # Prepare command
        cmd = [command] + (args or [])

        try:
            logger.info(f"Starting process '{name}': {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                env=process_env,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )

            self._processes[name] = process
            self._start_times[name] = datetime.now(timezone.utc)

            logger.info(f"Process '{name}' started with PID {process.pid}")
            return process

        except Exception as e:
            logger.exception(f"Failed to start process '{name}': {e}")
            return None

    def stop_process(self, name: str, timeout: int = 30) -> bool:
        """
        Stop a running process gracefully.

        Args:
            name: Service name
            timeout: Timeout in seconds

        Returns:
            True if stopped successfully
        """
        if name not in self._processes:
            logger.warning(f"Process '{name}' is not running")
            return True

        process = self._processes[name]

        try:
            logger.info(f"Stopping process '{name}' (PID {process.pid})")

            # Try graceful shutdown first
            if sys.platform == "win32":
                # Windows: send Ctrl+BREAK signal
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # Unix: send SIGTERM
                process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                logger.warning(f"Process '{name}' did not stop gracefully, forcing...")
                process.kill()
                process.wait(timeout=5)

            del self._processes[name]
            if name in self._start_times:
                del self._start_times[name]

            logger.info(f"Process '{name}' stopped successfully")
            return True

        except Exception as e:
            logger.exception(f"Failed to stop process '{name}': {e}")
            return False

    def restart_process(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        port: Optional[int] = None,
    ) -> Optional[subprocess.Popen]:
        """
        Restart a process.

        Args:
            name: Service name
            command: Command to execute
            args: Command arguments
            env: Environment variables
            working_dir: Working directory
            port: Port the service will use

        Returns:
            New process object or None if failed
        """
        self.stop_process(name)
        time.sleep(1)  # Brief pause before restart
        return self.start_process(name, command, args, env, working_dir, port)

    def get_process_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a running process.

        Args:
            name: Service name

        Returns:
            Dictionary with process info or None
        """
        if name not in self._processes:
            return None

        process = self._processes[name]

        # Check if process is still running
        poll_result = process.poll()
        if poll_result is not None:
            # Process has exited
            return {
                "name": name,
                "pid": process.pid,
                "running": False,
                "exit_code": poll_result,
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "uptime_seconds": None,
            }

        # Get CPU and memory usage
        cpu_percent = 0.0
        memory_mb = 0.0

        try:
            import psutil
            proc = psutil.Process(process.pid)
            cpu_percent = proc.cpu_percent(interval=0.1)
            memory_mb = proc.memory_info().rss / (1024 * 1024)
        except ImportError:
            # psutil not available, use basic info
            pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        # Calculate uptime
        uptime_seconds = None
        if name in self._start_times:
            uptime_seconds = (datetime.now(timezone.utc) - self._start_times[name]).total_seconds()

        return {
            "name": name,
            "pid": process.pid,
            "running": True,
            "exit_code": None,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "uptime_seconds": uptime_seconds,
        }

    def is_running(self, name: str) -> bool:
        """Check if a process is running."""
        if name not in self._processes:
            return False
        return self._processes[name].poll() is None

    def get_all_processes(self) -> Dict[str, subprocess.Popen]:
        """Get all managed processes."""
        return self._processes.copy()

    def cleanup_dead_processes(self) -> List[str]:
        """Remove dead processes from tracking."""
        dead = []
        for name in self._processes.keys():
            if self._processes[name].poll() is not None:
                del self._processes[name]
                if name in self._start_times:
                    del self._start_times[name]
                dead.append(name)
        return dead