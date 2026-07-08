"""Port detection and conflict resolution."""

import socket
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class PortDetector:
    """Detects port availability and resolves conflicts."""

    @staticmethod
    def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
        """
        Check if a port is available for binding.

        Args:
            port: Port number to check
            host: Host address to bind to

        Returns:
            True if port is available, False otherwise
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.bind((host, port))
            sock.close()
            return True
        except (OSError, socket.error):
            return False

    @staticmethod
    def find_available_port(start_port: int, end_port: int = 65535, host: str = "127.0.0.1") -> Optional[int]:
        """
        Find an available port in the given range.

        Args:
            start_port: Starting port number
            end_port: Ending port number
            host: Host address to bind to

        Returns:
            Available port number or None if no port found
        """
        for port in range(start_port, end_port + 1):
            if PortDetector.is_port_available(port, host):
                return port
        return None

    @staticmethod
    def get_port_for_service(service_name: str, preferred_port: int, host: str = "127.0.0.1") -> Tuple[int, bool]:
        """
        Get the port for a service, using preferred port if available.

        Args:
            service_name: Name of the service
            preferred_port: Preferred port number
            host: Host address

        Returns:
            Tuple of (port, was_preferred_used)
        """
        if PortDetector.is_port_available(preferred_port, host):
            logger.info(f"Service '{service_name}' using preferred port {preferred_port}")
            return preferred_port, True

        # Try to find an alternative port
        alternative_port = PortDetector.find_available_port(preferred_port + 1, preferred_port + 100, host)
        if alternative_port:
            logger.warning(
                f"Service '{service_name}' preferred port {preferred_port} is in use, "
                f"using alternative port {alternative_port}"
            )
            return alternative_port, False

        # Last resort: find any available port
        alternative_port = PortDetector.find_available_port(8000, 9000, host)
        if alternative_port:
            logger.warning(
                f"Service '{service_name}' could not find port near {preferred_port}, "
                f"using {alternative_port}"
            )
            return alternative_port, False

        logger.error(f"Service '{service_name}' could not find any available port")
        return preferred_port, False

    @staticmethod
    def get_process_using_port(port: int, host: str = "127.0.0.1") -> Optional[int]:
        """
        Get the PID of the process using a specific port.

        Args:
            port: Port number
            host: Host address

        Returns:
            PID of the process using the port, or None
        """
        import subprocess
        import re

        try:
            # Windows: use netstat to find process
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stdout.split("\n"):
                if f":{port}" in line and host in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid_match = re.search(r'(\d+)$', line.strip())
                        if pid_match:
                            return int(pid_match.group(1))
        except Exception as e:
            logger.debug(f"Could not get process for port {port}: {e}")

        return None

    @staticmethod
    def scan_ports(start_port: int, end_port: int, host: str = "127.0.0.1") -> List[int]:
        """
        Scan a range of ports and return list of occupied ports.

        Args:
            start_port: Starting port
            end_port: Ending port
            host: Host address

        Returns:
            List of occupied ports
        """
        occupied = []
        for port in range(start_port, end_port + 1):
            if not PortDetector.is_port_available(port, host):
                occupied.append(port)
        return occupied