"""Lógica principal do limpador WSL Docker (módulo)."""

from __future__ import annotations

import asyncio
import subprocess
import os
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import logging
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from i18n import t

IS_WINDOWS = sys.platform.startswith("win")

DOCKER_WSL_ROOT_TEMPLATES = (
    r"%LOCALAPPDATA%\Docker\wsl",
    r"%USERPROFILE%\AppData\Local\Docker\wsl",
)

DOCKER_VHDX_FILENAMES = ("docker_data.vhdx", "ext4.vhdx")


def get_docker_vhdx_paths() -> list[str]:
    """Discover Docker WSL VHDX files across supported layouts."""
    if not IS_WINDOWS:
        return []

    paths: list[str] = []
    for root_template in DOCKER_WSL_ROOT_TEMPLATES:
        root = Path(os.path.expandvars(root_template))
        if not root.exists():
            continue

        for filename in DOCKER_VHDX_FILENAMES:
            matches = sorted(
                (path for path in root.rglob(filename) if path.is_file()),
                key=lambda path: str(path).lower(),
            )
            paths.extend(str(path) for path in matches)

    return list(dict.fromkeys(paths))

if IS_WINDOWS:
    import ctypes


class WSLDockerCleaner:
    def __init__(self, console: Optional[Console] = None):
        self.log_messages = []
        self.total_space_saved = 0
        self.console = console or Console()
        self.logger = logging.getLogger(__name__)
        self.silent_console = False

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        if not getattr(self, 'silent_console', False):
            self.console.print(f"[bold]{timestamp}[/bold] [{level}] {message}")
        self.log_messages.append(log_msg)
        # Also log via standard logging so the UI logger captures it
        try:
            if level.upper() == "ERROR":
                self.logger.error(message)
            elif level.upper() == "WARNING":
                self.logger.warning(message)
            else:
                self.logger.info(message)
        except Exception:
            pass

    def run_command(self, command, capture_output=True, shell=True):
        """Executa um comando e retorna o resultado"""
        try:
            self.log(t("cleanup.executing", cmd=command))
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                shell=shell,
                timeout=300,  # 5 minutos timeout
            )
            if result.returncode != 0 and result.stderr:
                self.log(t("cleanup.error", error=result.stderr), "ERROR")
            return result
        except subprocess.TimeoutExpired:
            self.log(t("cleanup.timeout", cmd=command), "ERROR")
            return None
        except Exception as e:
            self.log(t("cleanup.error_executing", error=str(e)), "ERROR")
            return None

    async def run_command_async(
        self,
        command: str,
        shell: bool = True,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> subprocess.CompletedProcess:
        """Executa um comando async com streaming de saída em tempo real.

        Args:
            command: Comando a ser executado
            shell: Se True, executa via shell; se False, comando deve ser lista
            stream_callback: Função chamada para cada linha de saída (stdout/stderr)

        Returns:
            CompletedProcess com returncode, stdout e stderr
        """
        try:
            if stream_callback:
                stream_callback(f"{t('cleanup.executing', cmd=command)}\n")
            else:
                self.log(t("cleanup.executing", cmd=command))

            # Criar subprocess baseado no tipo (shell ou exec)
            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # Se não for shell, command deve ser uma lista
                cmd_list = command if isinstance(command, list) else command.split()
                process = await asyncio.create_subprocess_exec(
                    *cmd_list,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            # Funções para ler streams em tempo real
            stdout_lines = []
            stderr_lines = []

            async def stream_reader(stream, is_stderr=False):
                """Lê stream linha por linha e chama callback."""
                lines_list = stderr_lines if is_stderr else stdout_lines
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip("\n")
                    lines_list.append(text)
                    if stream_callback and text:
                        prefix = "[stderr] " if is_stderr else ""
                        stream_callback(f"{prefix}{text}\n")

            # Executar leitores em paralelo
            await asyncio.gather(
                stream_reader(process.stdout, is_stderr=False),
                stream_reader(process.stderr, is_stderr=True),
                return_exceptions=True,
            )

            # Aguardar término do processo
            returncode = await process.wait()

            # Log de erros se houver
            if returncode != 0 and stderr_lines:
                error_msg = "\n".join(stderr_lines)
                if stream_callback:
                    stream_callback(f"{t('cleanup.error_code', code=returncode, error=error_msg)}\n")
                else:
                    self.log(t("cleanup.error", error=error_msg), "ERROR")

            # Retornar CompletedProcess compatível
            return subprocess.CompletedProcess(
                args=command,
                returncode=returncode,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
            )

        except asyncio.TimeoutError:
            msg = f"{t('cleanup.timeout', cmd=command)}\n"
            if stream_callback:
                stream_callback(msg)
            else:
                self.log(t("cleanup.timeout", cmd=command), "ERROR")
            return subprocess.CompletedProcess(command, -1, "", "Timeout")
        except Exception as e:
            msg = f"{t('cleanup.error_executing', error=str(e))}\n"
            if stream_callback:
                stream_callback(msg)
            else:
                self.log(t("cleanup.error_executing", error=str(e)), "ERROR")
            return subprocess.CompletedProcess(command, -1, "", str(e))

    async def run_elevated_command_async(
        self, command: str, stream_callback: Optional[Callable[[str], None]] = None
    ) -> subprocess.CompletedProcess:
        """Executa comando elevated (admin/root)."""
        if stream_callback:
            stream_callback(f"{t('cleanup.requesting_admin')}\n")

        if not IS_WINDOWS:
            return await self.run_command_async(
                f"sudo bash -c '{command}'", shell=True, stream_callback=stream_callback
            )

        # Windows: PowerShell Start-Process RunAs
        escaped_cmd = (
            command.replace("'", "'\"'\"'").replace('"', '\\"').replace("\n", "`n")
        )

        ps_script = f'''
$outFile = [System.IO.Path]::GetTempFileName().Replace(".tmp", ".txt")
$errFile = [System.IO.Path]::GetTempFileName().Replace(".tmp", ".txt")
try {{
    $proc = Start-Process powershell -ArgumentList "-NoProfile", "-Command", "{escaped_cmd}" -Verb RunAs -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile
    Get-Content $outFile -Raw -Encoding UTF8
    if (Test-Path $errFile) {{ "[stderr]`n" + (Get-Content $errFile -Raw -Encoding UTF8) }}
}} finally {{
    if (Test-Path $outFile) {{ Remove-Item $outFile -Force }}
    if (Test-Path $errFile) {{ Remove-Item $errFile -Force }}
}}
'''
        ps_cmd = (
            f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{ps_script}"'
        )

        return await self.run_command_async(
            ps_cmd, shell=True, stream_callback=stream_callback
        )

    def run_elevated_command(self, command: str) -> subprocess.CompletedProcess | None:
        """Versão sync para CLI."""
        if not IS_WINDOWS:
            self.log(t("cleanup.executing_elevated", cmd=command))
            return self.run_command(f"sudo bash -c '{command}'")

        escaped_cmd = command.replace("'", "'\"'\"'").replace('"', '\\"')

        ps_script = f'''
$outFile = [System.IO.Path]::GetTempFileName().Replace(".tmp", ".txt")
$errFile = [System.IO.Path]::GetTempFileName().Replace(".tmp", ".txt")
try {{
    Start-Process powershell -ArgumentList "-NoProfile", "-Command", "{escaped_cmd}" -Verb RunAs -WindowStyle Hidden -Wait -RedirectStandardOutput $outFile -RedirectStandardError $errFile
    Get-Content $outFile -Raw -Encoding UTF8
    if (Test-Path $errFile) {{ Get-Content $errFile -Raw -Encoding UTF8 }}
}} finally {{
    Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue
}}
'''
        ps_cmd = (
            f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{ps_script}"'
        )

        self.log(t("cleanup.executing_elevated", cmd=command))
        return self.run_command(ps_cmd)

    def is_docker_running(self):
        """Verifica se o Docker está rodando"""
        if IS_WINDOWS:
            result = self.run_command(
                'tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I "Docker Desktop.exe" >NUL',
                capture_output=True,
            )
            if result and result.returncode != 0:
                return False

        result = self.run_command("docker ps", capture_output=True)
        return result and result.returncode == 0

    def is_admin(self):
        """Verifica se o script está rodando como administrador/root"""
        if IS_WINDOWS:
            try:
                return ctypes.windll.shell32.IsUserAnAdmin()
            except Exception:
                return False
        else:
            return os.geteuid() == 0

    def run_as_admin(self):
        """Reinicia o script com privilégios de administrador/root"""
        if not IS_WINDOWS:
            self.console.print(
                f"\n[yellow]{t('cleanup.requires_root')}[/yellow]"
            )
            sys.exit(1)

        try:
            python_exe = sys.executable
            # Tenta usar argv[0] para preservar o script que foi invocado
            script_path = (
                os.path.abspath(sys.argv[0])
                if len(sys.argv) > 0
                else os.path.abspath(__file__)
            )
            params = f'"{script_path}"'

            self.console.print(
                f"\n[yellow]{t('cleanup.requires_admin')}[/yellow]"
            )
            self.console.print(
                f"[yellow]{t('cleanup.requesting_elevation')}[/yellow]\n"
            )

            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                python_exe,
                params,
                None,
                1,  # SW_SHOW
            )

            sys.exit(0)

        except Exception as e:
            self.console.print(
                f"[bold red]{t('cleanup.admin_error', error=str(e))}[/bold red]"
            )
            self.console.print(
                f"[bold red]{t('cleanup.run_as_admin_manual')}[/bold red]"
            )
            sys.exit(1)

    # --- Relacionados ao VHDX e Docker (copiado e mantido) ---
    def _get_all_vhdx_paths(self) -> list[str]:
        return get_docker_vhdx_paths()

    def _wait_for_vhdx_unlock(self, path: str, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(path, "a+b"):
                    pass
                return True
            except PermissionError:
                time.sleep(2)
            except FileNotFoundError:
                return False
        return False

    async def _wait_for_vhdx_unlock_async(self, path: str, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(path, "a+b"):
                    pass
                return True
            except PermissionError:
                await asyncio.sleep(2)
            except FileNotFoundError:
                return False
        return False

    def _parse_reclaimed_space(self, result) -> str:
        """Parse the reclaimed space from Docker prune command output.

        Handles both English and Portuguese Docker locales.
        """
        if not result or not result.stdout:
            return "0B"

        output = result.stdout

        # Try English format first: "Total reclaimed space: X"
        if "Total reclaimed space:" in output:
            try:
                return output.split("Total reclaimed space:")[1].strip().split("\n")[0]
            except (IndexError, AttributeError):
                pass

        # Try Portuguese format: "Espaço total recuperado:" or similar
        if "Espaço" in output and "recuperado" in output.lower():
            try:
                for line in output.split("\n"):
                    if "recuperado" in line.lower():
                        # Try to extract size value (e.g., "1.5GB", "500MB", etc.)
                        parts = line.split(":")
                        if len(parts) > 1:
                            return parts[-1].strip()
            except Exception:
                pass

        # Look for size patterns in output (e.g., "1.5GB", "500MB", "0B")
        import re

        size_pattern = r"\b(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|kB)\b"
        matches = re.findall(size_pattern, output, re.IGNORECASE)
        if matches:
            # Return the last match which is typically the total
            size, unit = matches[-1]
            return f"{size}{unit.upper()}"

        return "0B"

    def get_docker_vhdx_size(self):
        if not IS_WINDOWS:
            return 0, []
        
        vhdx_paths = self._get_all_vhdx_paths()

        total_size = 0
        existing_files = []
        for path in vhdx_paths:
            if os.path.exists(path):
                size = os.path.getsize(path)
                total_size += size
                existing_files.append((path, size))
                size_gb = size / (1024**3)
                self.log(t("cleanup.vhdx_found", path=path, size=f"{size_gb:.2f}"))
        return total_size, existing_files

    def docker_cleanup(self, prune_only: str | None = None):
        """Run Docker cleanup. If prune_only is set, only that specific step runs."""
        if not self.is_docker_running():
            self.log(t("cleanup.docker_not_running"), "WARNING")
            try:
                if IS_WINDOWS:
                    docker_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
                    if not os.path.exists(docker_path):
                        self.log(
                            t("cleanup.docker_not_found", path=docker_path), "WARNING"
                        )
                        self.log(
                            t("cleanup.skip_docker"),
                            "WARNING",
                        )
                        return False
                    subprocess.Popen([docker_path], shell=False)
                else:
                    # Linux/macOS: try to start Docker daemon
                    if shutil.which("docker") is None:
                        self.log(t("cleanup.docker_not_installed"), "ERROR")
                        return False
                    # Try systemctl first (Linux), then open (macOS)
                    if shutil.which("systemctl"):
                        subprocess.Popen(["sudo", "systemctl", "start", "docker"])
                    elif sys.platform == "darwin" and os.path.exists("/Applications/Docker.app"):
                        subprocess.Popen(["open", "/Applications/Docker.app"])
                    else:
                        self.log(t("cleanup.skip_docker"), "WARNING")
                        return False

                self.log(t("cleanup.waiting_docker"))
                max_wait = 60
                wait_interval = 5
                for i in range(0, max_wait, wait_interval):
                    time.sleep(wait_interval)
                    if self.is_docker_running():
                        self.log(
                            t("cleanup.docker_started", seconds=i + wait_interval)
                        )
                        time.sleep(5)
                        break
                    self.log(t("cleanup.waiting_progress", current=i + wait_interval, max=max_wait))
                else:
                    self.log(
                        t("cleanup.docker_timeout"), "ERROR"
                    )
                    return False
            except Exception as e:
                self.log(t("cleanup.docker_start_error", error=str(e)), "ERROR")
                return False

        self.log(t("cleanup.starting_docker_cleanup"))

        # If prune_only is set, run only that specific step
        if prune_only == "containers":
            self.log(t("cleanup.stopping_containers"))
            containers_result = self.run_command("docker ps -q", capture_output=True)
            if containers_result and containers_result.stdout.strip():
                for cid in containers_result.stdout.strip().split("\n"):
                    if cid.strip():
                        self.run_command(f"docker stop {cid.strip()}", capture_output=True)
                        self.log(t("cleanup.container_stopped", id=cid.strip()))
            self.log(t("cleanup.removing_containers"))
            result = self.run_command("docker container prune -f")
            space = self._parse_reclaimed_space(result)
            self.log(t("cleanup.space_containers", space=space))
            return True
        elif prune_only == "images":
            self.log(t("cleanup.removing_images"))
            result = self.run_command("docker image prune -af")
            space = self._parse_reclaimed_space(result)
            self.log(t("cleanup.space_images", space=space))
            return True
        elif prune_only == "volumes":
            self.log(t("cleanup.removing_volumes"))
            result = self.run_command("docker volume prune -f")
            space = self._parse_reclaimed_space(result)
            self.log(t("cleanup.space_volumes", space=space))
            return True
        elif prune_only == "networks":
            self.log(t("cleanup.removing_networks"))
            self.run_command("docker network prune -f")
            return True
        elif prune_only == "builder":
            self.log(t("cleanup.clearing_build_cache"))
            self.run_command("docker builder prune -af")
            return True

        # Full cleanup (original behavior when prune_only is None)
        self.log(t("cleanup.stopping_containers"))
        containers_result = self.run_command("docker ps -q", capture_output=True)
        if containers_result and containers_result.stdout.strip():
            container_ids = containers_result.stdout.strip().split("\n")
            for container_id in container_ids:
                if container_id.strip():
                    self.run_command(
                        f"docker stop {container_id.strip()}", capture_output=True
                    )
                    self.log(t("cleanup.container_stopped", id=container_id.strip()))
        else:
            self.log(t("cleanup.no_containers"))

        self.log(t("cleanup.removing_containers"))
        result = self.run_command("docker container prune -f")
        space = self._parse_reclaimed_space(result)
        self.log(t("cleanup.space_containers", space=space))

        self.log(t("cleanup.removing_images"))
        result = self.run_command("docker image prune -af")
        space = self._parse_reclaimed_space(result)
        self.log(t("cleanup.space_images", space=space))

        self.log(t("cleanup.removing_volumes"))
        result = self.run_command("docker volume prune -f")
        space = self._parse_reclaimed_space(result)
        self.log(t("cleanup.space_volumes", space=space))

        self.log(t("cleanup.removing_networks"))
        self.run_command("docker network prune -f")

        self.log(t("cleanup.full_system_cleanup"))
        result = self.run_command("docker system prune -af --volumes")
        space = self._parse_reclaimed_space(result)
        self.log(t("cleanup.space_system", space=space))

        self.log(t("cleanup.clearing_build_cache"))
        self.run_command("docker builder prune -af")

        return True

    def stop_docker_wsl(self):
        self.log(t("cleanup.stopping_docker_wsl"))
        result = None
        if IS_WINDOWS:
            self.log(t("cleanup.stopping_docker_desktop"))
            docker_processes = [
                "Docker Desktop.exe",
                "Docker.exe",
                "com.docker.backend.exe",
                "com.docker.proxy.exe",
                "dockerd.exe",
                "vpnkit.exe",
            ]
            kill_commands = " & ".join(
                [f'taskkill /F /IM "{process}" /T 2>nul' for process in docker_processes]
            )
            batch_command = f"{kill_commands} & wsl --shutdown"

            if not self.is_admin():
                self.log(t("cleanup.requesting_admin"))
            result = self.run_elevated_command(batch_command)
            if result and result.returncode == 0:
                self.log(t("cleanup.wsl_stopped"))
            else:
                self.log(t("cleanup.wsl_error"), "ERROR")
        else:
            # Linux/macOS: stop Docker daemon
            self.log(t("cleanup.stopping_docker_linux"))
            if shutil.which("systemctl"):
                result = self.run_command("sudo systemctl stop docker", capture_output=True)
            else:
                result = self.run_command("sudo killall Docker com.docker.hyperkit dockerd 2>/dev/null || true", capture_output=True)
            if result and result.returncode == 0:
                self.log(t("cleanup.docker_stopped_linux"))
            else:
                self.log(t("cleanup.docker_stop_error_linux", error=""), "WARNING")

        time.sleep(10)
        return bool(result and result.returncode == 0)

    def configure_wsl_sparse(self):
        if not IS_WINDOWS:
            self.log(t("cleanup.sparse_windows_only"), "INFO")
            return True
        self.log(t("cleanup.configuring_sparse"))
        result = self.run_command("wsl -l -v")
        if not result:
            return False
        distributions = ["docker-desktop", "docker-desktop-data"]
        sparse_commands = "; ".join(
            [f'wsl --manage "{distro}" --set-sparse true' for distro in distributions]
        )
        for distro in distributions:
            self.log(t("cleanup.sparse_distro", distro=distro))
        if not self.is_admin():
            self.log(t("cleanup.requesting_admin"))
        result = self.run_elevated_command(sparse_commands)
        wslconfig_path = os.path.expanduser("~/.wslconfig")
        wslconfig_content = """[wsl2]
sparseVhd=true
memory=4GB
processors=4
swap=2GB
swapFile=%TEMP%\\wsl-swap.vhdx
"""
        try:
            with open(wslconfig_path, "w", encoding="utf-8") as f:
                f.write(wslconfig_content)
            self.log(t("cleanup.wslconfig_updated", path=wslconfig_path))
        except Exception as e:
            self.log(t("cleanup.wslconfig_error", error=str(e)), "ERROR")
        return bool(result and result.returncode == 0)

    def compact_vhdx_files(self):
        if not IS_WINDOWS:
            self.log(t("cleanup.vhdx_windows_only"), "INFO")
            return True
        needs_elevation = not self.is_admin()
        if needs_elevation:
            self.log(t("cleanup.requesting_admin"))
        self.log(t("cleanup.compacting_vhdx"))
        
        vhdx_paths = self._get_all_vhdx_paths()
        success = False
        
        for vhdx_path in vhdx_paths:
            if os.path.exists(vhdx_path):
                size_before = os.path.getsize(vhdx_path)
                size_before_gb = size_before / (1024**3)
                self.log(t("cleanup.compacting_file", path=vhdx_path, size=f"{size_before_gb:.2f}"))
                
                # Try to shutdown wsl again just in case
                self.run_command("wsl --shutdown", capture_output=True)
                
                if not self._wait_for_vhdx_unlock(vhdx_path, timeout=90):
                    self.log(f"Timeout waiting for lock release: {vhdx_path}. O arquivo pode estar sendo usado por outro processo. Pulando compactação.", "ERROR")
                    continue
                
                # Diskpart approach
                diskpart_script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "compact_vhdx.txt")
                diskpart_script = f'select vdisk file="{vhdx_path}"\nattach vdisk readonly\ncompact vdisk\ndetach vdisk\n'
                
                try:
                    with open(diskpart_script_path, "w", encoding="utf-8") as f:
                        f.write(diskpart_script)
                    
                    cmd = f'diskpart /s "{diskpart_script_path}"'
                    result = self.run_elevated_command(cmd)
                    
                    if result and result.returncode == 0:
                        time.sleep(2)
                        if os.path.exists(vhdx_path):
                            size_after = os.path.getsize(vhdx_path)
                            size_after_gb = size_after / (1024**3)
                            space_saved = (size_before - size_after) / (1024**3)
                            self.total_space_saved += max(0, space_saved)
                            self.log(
                                t("cleanup.compact_done", size=f"{size_after_gb:.2f}", saved=f"{space_saved:.2f}")
                            )
                            success = True
                        else:
                            self.log(t("cleanup.file_not_found_after", path=vhdx_path), "ERROR")
                    else:
                        error_msg = result.stderr if result and hasattr(result, "stderr") and result.stderr else "Unknown error"
                        self.log(f"Diskpart failed: {error_msg}. Falling back to Optimize-VHD...", "WARNING")
                        
                        ps_command = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                        result2 = self.run_elevated_command(ps_command)
                        if result2 and result2.returncode == 0:
                            time.sleep(2)
                            size_after = os.path.getsize(vhdx_path)
                            size_after_gb = size_after / (1024**3)
                            space_saved = (size_before - size_after) / (1024**3)
                            self.total_space_saved += max(0, space_saved)
                            self.log(
                                t("cleanup.compact_done", size=f"{size_after_gb:.2f}", saved=f"{space_saved:.2f}")
                            )
                            success = True
                        else:
                            err2 = result2.stderr if result2 and hasattr(result2, "stderr") and result2.stderr else "Unknown error"
                            self.log(t("cleanup.compact_error", path=vhdx_path) + f" - {err2}", "ERROR")
                finally:
                    if os.path.exists(diskpart_script_path):
                        try:
                            os.remove(diskpart_script_path)
                        except Exception:
                            pass
        return success

    def cleanup_temp_files(self):
        self.log(t("cleanup.cleaning_temp"))
        if IS_WINDOWS:
            temp_paths = [
                os.path.expandvars(r"%TEMP%"),
                os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
                os.path.expandvars(r"%LOCALAPPDATA%\Docker\log"),
                r"C:\Windows\Temp",
            ]
        else:
            import tempfile
            temp_paths = [
                tempfile.gettempdir(),
                os.path.expanduser("~/.docker"),
                "/var/tmp",
            ]
            # Docker logs on Linux/macOS
            docker_log = "/var/lib/docker/containers"
            if os.path.exists(docker_log):
                temp_paths.append(docker_log)

        total_files_deleted = 0
        total_bytes_deleted = 0

        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                self.log(t("cleanup.cleaning_path", path=temp_path))
                files_deleted = 0
                bytes_deleted = 0

                try:
                    # Walk through all files in the temp directory
                    for root, dirs, files in os.walk(temp_path, topdown=False):
                        # Delete files
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                files_deleted += 1
                                bytes_deleted += file_size
                            except (PermissionError, OSError):
                                # Skip files that are in use or protected
                                pass

                        # Try to remove empty directories
                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            try:
                                os.rmdir(dir_path)
                            except (PermissionError, OSError):
                                # Skip directories that are in use or not empty
                                pass

                    if files_deleted > 0:
                        bytes_mb = bytes_deleted / (1024 * 1024)
                        self.log(
                            t("cleanup.files_removed", count=files_deleted, path=temp_path, size=f"{bytes_mb:.2f}")
                        )

                    total_files_deleted += files_deleted
                    total_bytes_deleted += bytes_deleted

                except Exception as e:
                    self.log(t("cleanup.error_cleaning", path=temp_path, error=str(e)), "ERROR")

        if total_files_deleted > 0:
            total_mb = total_bytes_deleted / (1024 * 1024)
            self.log(
                t("cleanup.total_cleaned", count=total_files_deleted, size=f"{total_mb:.2f}")
            )

        return True

    def cleanup_recycle_bin(self):
        """Esvazia a lixeira."""
        if not IS_WINDOWS:
            self.log(t("cleanup.recycle_bin_linux"), "INFO")
            return True
        self.log(t("cleanup.emptying_recycle_bin"))
        try:
            # Use PowerShell to clear the recycle bin silently
            ps_command = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
            result = self.run_command(f'powershell -NoProfile -Command "{ps_command}"')

            if result and result.returncode == 0:
                self.log(t("cleanup.recycle_bin_done"))
                return True
            else:
                # Clear-RecycleBin might fail if bin is already empty, that's okay
                self.log(t("cleanup.recycle_bin_empty"))
                return True
        except Exception as e:
            self.log(t("cleanup.recycle_bin_error", error=str(e)), "ERROR")
            return False

    async def cleanup_recycle_bin_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de cleanup_recycle_bin com streaming."""
        if not IS_WINDOWS:
            if stream_callback:
                stream_callback(f"{t('cleanup.recycle_bin_linux')}\n")
            return True

        if stream_callback:
            stream_callback(f"{t('cleanup.emptying_recycle_bin')}\n")

        try:
            ps_command = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
            result = await self.run_command_async(
                f'powershell -NoProfile -Command "{ps_command}"',
                shell=True,
                stream_callback=stream_callback,
            )

            if result and result.returncode == 0:
                if stream_callback:
                    stream_callback(f"{t('cleanup.recycle_bin_done')}\n")
                return True
            else:
                if stream_callback:
                    stream_callback(
                        f"{t('cleanup.recycle_bin_empty')}\n"
                    )
                return True
        except Exception as e:
            if stream_callback:
                stream_callback(f"{t('cleanup.recycle_bin_error', error=str(e))}\n")
            return False

    async def cleanup_temp_files_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de cleanup_temp_files com streaming."""
        if stream_callback:
            stream_callback(f"{t('cleanup.cleaning_temp')}\n")

        if IS_WINDOWS:
            temp_paths = [
                os.path.expandvars(r"%TEMP%"),
                os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
                os.path.expandvars(r"%LOCALAPPDATA%\Docker\log"),
                r"C:\Windows\Temp",
            ]
        else:
            import tempfile
            temp_paths = [
                tempfile.gettempdir(),
                os.path.expanduser("~/.docker"),
                "/var/tmp",
            ]

        total_deleted = 0
        total_bytes = 0

        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                if stream_callback:
                    stream_callback(f"{t('cleanup.cleaning_path', path=temp_path)}\n")

                files_deleted = 0
                bytes_deleted = 0

                try:
                    # Walk through all files in the temp directory
                    for root, dirs, files in os.walk(temp_path, topdown=False):
                        # Delete files
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                files_deleted += 1
                                bytes_deleted += file_size
                            except (PermissionError, OSError):
                                # Skip files that are in use or protected
                                pass

                        # Try to remove empty directories
                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            try:
                                os.rmdir(dir_path)
                            except (PermissionError, OSError):
                                pass

                    if files_deleted > 0 and stream_callback:
                        bytes_mb = bytes_deleted / (1024 * 1024)
                        stream_callback(
                            f"{t('cleanup.files_removed_short', count=files_deleted, size=f'{bytes_mb:.2f}')}\n"
                        )

                    total_deleted += files_deleted
                    total_bytes += bytes_deleted

                except Exception as e:
                    if stream_callback:
                        stream_callback(f"{t('cleanup.error_cleaning', path=temp_path, error=str(e))}\n")

        if stream_callback and total_deleted > 0:
            total_mb = total_bytes / (1024 * 1024)
            stream_callback(
                f"{t('cleanup.total_cleaned', count=total_deleted, size=f'{total_mb:.2f}')}\n"
            )

        return total_deleted > 0

    # ========== MÉTODOS ASYNC COM STREAMING ==========

    async def docker_cleanup_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de docker_cleanup com streaming de saída em tempo real."""
        if stream_callback:
            stream_callback(f"{t('cleanup.starting_docker_cleanup')}\n")
        else:
            self.log(t("cleanup.starting_docker_cleanup"))

        # Parar containers
        if stream_callback:
            stream_callback(f"{t('cleanup.stopping_containers')}\n")

        containers_result = await self.run_command_async(
            "docker ps -q", shell=True, stream_callback=stream_callback
        )
        if containers_result and containers_result.stdout.strip():
            container_ids = containers_result.stdout.strip().split("\n")
            for container_id in container_ids:
                if container_id.strip():
                    await self.run_command_async(
                        f"docker stop {container_id.strip()}",
                        shell=True,
                        stream_callback=stream_callback,
                    )

        # Prune containers
        if stream_callback:
            stream_callback(f"{t('cleanup.removing_containers')}\n")
        await self.run_command_async(
            "docker container prune -f", shell=True, stream_callback=stream_callback
        )

        # Prune images
        if stream_callback:
            stream_callback(f"{t('cleanup.removing_images')}\n")
        await self.run_command_async(
            "docker image prune -af", shell=True, stream_callback=stream_callback
        )

        # Prune volumes
        if stream_callback:
            stream_callback(f"{t('cleanup.removing_volumes')}\n")
        await self.run_command_async(
            "docker volume prune -f", shell=True, stream_callback=stream_callback
        )

        # Prune networks
        if stream_callback:
            stream_callback(f"{t('cleanup.removing_networks')}\n")
        await self.run_command_async(
            "docker network prune -f", shell=True, stream_callback=stream_callback
        )

        # System prune completo
        if stream_callback:
            stream_callback(f"{t('cleanup.full_system_cleanup')}\n")
        await self.run_command_async(
            "docker system prune -af --volumes",
            shell=True,
            stream_callback=stream_callback,
        )

        # Build cache
        if stream_callback:
            stream_callback(f"{t('cleanup.clearing_build_cache')}\n")
        await self.run_command_async(
            "docker builder prune -af", shell=True, stream_callback=stream_callback
        )

        if stream_callback:
            stream_callback(f"{t('cleanup.docker_cleanup_done')}\n")

        return True

    async def stop_docker_wsl_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de stop_docker_wsl."""
        if IS_WINDOWS:
            if stream_callback:
                stream_callback(f"{t('cleanup.stopping_docker_wsl_batch')}\n")

            docker_processes = [
                "Docker Desktop.exe",
                "Docker.exe",
                "com.docker.backend.exe",
                "com.docker.proxy.exe",
                "dockerd.exe",
                "vpnkit.exe",
            ]
            processes_str = " ".join([f'/IM "{p}"' for p in docker_processes])

            ps_batch_cmd = f"""
taskkill /F {processes_str} 2>nul; 
wsl --shutdown
"""

            if stream_callback:
                stream_callback(f"{t('cleanup.batch_kill')}\n")
                stream_callback(f"{t('cleanup.admin_single_uac')}\n")

            result = await self.run_elevated_command_async(
                ps_batch_cmd, stream_callback=stream_callback
            )
        else:
            if stream_callback:
                stream_callback(f"{t('cleanup.stopping_docker_linux')}\n")
            if shutil.which("systemctl"):
                result = await self.run_command_async(
                    "sudo systemctl stop docker", shell=True, stream_callback=stream_callback
                )
            else:
                result = await self.run_command_async(
                    "sudo killall Docker com.docker.hyperkit dockerd 2>/dev/null || true",
                    shell=True, stream_callback=stream_callback
                )
            if stream_callback:
                stream_callback(f"{t('cleanup.docker_stopped_linux')}\n")

        await asyncio.sleep(10)

        if stream_callback:
            stream_callback(f"{t('cleanup.docker_wsl_stopped')}\n")

        return result.returncode == 0 if result else False

    async def configure_wsl_sparse_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async com batch elevated."""
        if not IS_WINDOWS:
            if stream_callback:
                stream_callback(f"{t('cleanup.sparse_windows_only')}\n")
            return True

        if stream_callback:
            stream_callback(f"{t('cleanup.configuring_sparse')}\n")

        # List distros first (non-elevated)
        result = await self.run_command_async(
            "wsl -l -v", shell=True, stream_callback=stream_callback
        )
        if not result or result.returncode != 0:
            if stream_callback:
                stream_callback(f"{t('cleanup.wsl_distro_error')}\n")
            return False

        distributions = ["docker-desktop", "docker-desktop-data"]
        sparse_cmds = "; ".join(
            [f'wsl --manage "{distro}" --set-sparse true' for distro in distributions]
        )

        if stream_callback:
            stream_callback(f"{t('cleanup.sparse_distros', distros=', '.join(distributions))}\n")
            stream_callback(f"{t('cleanup.admin_single_uac')}\n")

        try:
            result = await self.run_elevated_command_async(
                sparse_cmds, stream_callback=stream_callback
            )
        except Exception as e:
            if stream_callback:
                stream_callback(f"[WARNING] set-sparse failed: {e}\n")

        # .wslconfig (non-elevated)
        wslconfig_path = os.path.expanduser("~/.wslconfig")
        wslconfig_content = """[wsl2]
sparseVhd=true
memory=4GB
processors=4
swap=2GB
swapFile=%TEMP%\\wsl-swap.vhdx
"""
        try:
            with open(wslconfig_path, "w", encoding="utf-8") as f:
                f.write(wslconfig_content)
            if stream_callback:
                stream_callback(f"{t('cleanup.wslconfig_updated', path=wslconfig_path)}\n")
        except Exception as e:
            if stream_callback:
                stream_callback(f"{t('cleanup.wslconfig_error', error=str(e))}\n")

        return True

    async def compact_vhdx_files_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de compact_vhdx_files com streaming."""
        if not IS_WINDOWS:
            if stream_callback:
                stream_callback(f"{t('cleanup.vhdx_windows_only')}\n")
            return True

        if stream_callback:
            stream_callback(f"{t('cleanup.compacting_vhdx')}\n")

        vhdx_paths = self._get_all_vhdx_paths()

        success = False
        for vhdx_path in vhdx_paths:
            if os.path.exists(vhdx_path):
                size_before = os.path.getsize(vhdx_path)
                size_before_gb = size_before / (1024**3)

                if stream_callback:
                    stream_callback(
                        f"{t('cleanup.compacting_file', path=vhdx_path, size=f'{size_before_gb:.2f}')}\n"
                    )
                
                # Try to shutdown wsl again just in case
                await self.run_command_async("wsl --shutdown", shell=True)
                
                unlocked = await self._wait_for_vhdx_unlock_async(vhdx_path, timeout=90)
                if not unlocked:
                    if stream_callback:
                        stream_callback(f"[ERROR] Timeout waiting for lock release: {vhdx_path}. O arquivo pode estar sendo usado. Pulando.\n")
                    continue

                diskpart_script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "compact_vhdx_async.txt")
                diskpart_script = f'select vdisk file="{vhdx_path}"\nattach vdisk readonly\ncompact vdisk\ndetach vdisk\n'
                
                try:
                    with open(diskpart_script_path, "w", encoding="utf-8") as f:
                        f.write(diskpart_script)
                    
                    cmd = f'diskpart /s "{diskpart_script_path}"'
                    result = await self.run_elevated_command_async(
                        cmd, stream_callback=stream_callback
                    )
                    
                    if result and result.returncode == 0:
                        await asyncio.sleep(2)
                        if os.path.exists(vhdx_path):
                            size_after = os.path.getsize(vhdx_path)
                            size_after_gb = size_after / (1024**3)
                            space_saved = (size_before - size_after) / (1024**3)
                            self.total_space_saved += max(0, space_saved)

                            if stream_callback:
                                stream_callback(
                                    f"{t('cleanup.compact_done', size=f'{size_after_gb:.2f}', saved=f'{space_saved:.2f}')}\n"
                                )
                            success = True
                        else:
                            if stream_callback:
                                stream_callback(
                                    f"{t('cleanup.file_not_found_after', path=vhdx_path)}\n"
                                )
                    else:
                        error_msg = result.stderr if result and hasattr(result, "stderr") and result.stderr else "Unknown error"
                        if stream_callback:
                            stream_callback(f"[WARNING] Diskpart failed: {error_msg}. Falling back to Optimize-VHD...\n")
                            
                        ps_command = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                        result2 = await self.run_elevated_command_async(
                            ps_command, stream_callback=stream_callback
                        )

                        if result2 and result2.returncode == 0:
                            await asyncio.sleep(2)
                            size_after = os.path.getsize(vhdx_path)
                            size_after_gb = size_after / (1024**3)
                            space_saved = (size_before - size_after) / (1024**3)
                            self.total_space_saved += max(0, space_saved)

                            if stream_callback:
                                stream_callback(
                                    f"{t('cleanup.compact_done', size=f'{size_after_gb:.2f}', saved=f'{space_saved:.2f}')}\n"
                                )
                            success = True
                        else:
                            err2 = result2.stderr if result2 and hasattr(result2, "stderr") and result2.stderr else "Unknown error"
                            if stream_callback:
                                stream_callback(f"{t('cleanup.compact_error', path=vhdx_path)} - {err2}\n")
                finally:
                    if os.path.exists(diskpart_script_path):
                        try:
                            os.remove(diskpart_script_path)
                        except Exception:
                            pass

        return success

    def generate_report(self):
        self.log(t("cleanup.final_report"))
        current_size, files = self.get_docker_vhdx_size()
        current_size_gb = current_size / (1024**3)
        report = f"""
{t("cleanup.report_title")}
{"=" * 50}
{t("cleanup.report_datetime", datetime=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))}
{t("cleanup.report_space_saved", size=f"{self.total_space_saved:.2f}")}
{t("cleanup.report_current_size", size=f"{current_size_gb:.2f}")}

{t("cleanup.report_vhdx_files")}
{chr(10).join([f"  - {f[0]} ({f[1] / (1024**3):.2f} GB)" for f in files])}

{t("cleanup.report_recommendations")}
{t("cleanup.report_rec_1")}
{t("cleanup.report_rec_2")}
{t("cleanup.report_rec_3")}
{t("cleanup.report_rec_4")}
{t("cleanup.report_rec_5")}

{t("cleanup.report_log_saved", path="wsl_docker_cleanup.log")}
        """
        print(report)
        try:
            with open("wsl_docker_cleanup.log", "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_messages))
                f.write("\n\n" + report)
            self.log(t("cleanup.log_saved", path="wsl_docker_cleanup.log"))
        except Exception as e:
            self.log(t("cleanup.log_save_error", error=str(e)), "ERROR")

    def run_full_cleanup_with_progress(self):
        self.log(t("cleanup.starting_full"))
        self.log(
            t("cleanup.running_as_admin", status=t("cleanup.admin_yes") if self.is_admin() else t("cleanup.admin_no"))
        )
        initial_size, _ = self.get_docker_vhdx_size()
        initial_size_gb = initial_size / (1024**3)
        self.log(t("cleanup.initial_vhdx_size", size=f"{initial_size_gb:.2f}"))
        
        self.silent_console = True

        overall_progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )
        current_task_progress = Progress(
            TextColumn("{task.description}"), console=self.console
        )
        from rich.console import Group

        progress_group = Group(Panel(Group(current_task_progress)), overall_progress)
        overall_task = overall_progress.add_task(
            f"[cyan]{t('cleanup.running_full_cleanup')}", total=100
        )
        
        success = False
        with Live(progress_group, refresh_per_second=10, console=self.console):
            try:
                current_task = current_task_progress.add_task(t("cleanup.cleaning_docker"))
                overall_progress.update(
                    overall_task, description=f"[cyan]{t('cleanup.cleaning_docker')}"
                )
                if self.docker_cleanup():
                    self.log(t("cleanup.docker_cleanup_success"))
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=30)

                current_task = current_task_progress.add_task(t("cleanup.stopping_docker_wsl_task"))
                overall_progress.update(
                    overall_task, description=f"[cyan]{t('cleanup.stopping_docker_wsl_task')}"
                )
                self.stop_docker_wsl()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=15)

                current_task = current_task_progress.add_task(
                    t("cleanup.configuring_sparse_task")
                )
                overall_progress.update(
                    overall_task, description=f"[cyan]{t('cleanup.configuring_sparse_task')}"
                )
                self.configure_wsl_sparse()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=15)

                current_task = current_task_progress.add_task(
                    t("cleanup.compacting_vhdx_task")
                )
                overall_progress.update(
                    overall_task, description=f"[cyan]{t('cleanup.compacting_vhdx_task')}"
                )
                self.compact_vhdx_files()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=20)

                current_task = current_task_progress.add_task(
                    t("cleanup.cleaning_temp_task")
                )
                overall_progress.update(
                    overall_task, description=f"[cyan]{t('cleanup.cleaning_temp_task')}"
                )
                self.cleanup_temp_files()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=10)

                current_task = current_task_progress.add_task(t("cleanup.emptying_recycle_task"))
                overall_progress.update(
                    overall_task, description=f"[cyan]{t('cleanup.emptying_recycle_task')}"
                )
                self.cleanup_recycle_bin()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=5)

                overall_progress.update(
                    overall_task, description=f"[green]{t('cleanup.cleanup_done')}"
                )
                success = True
            except Exception as e:
                self.log(t("cleanup.cleanup_error", error=str(e)), "ERROR")
                success = False

        self.silent_console = False

        if success:
            current_size, _ = self.get_docker_vhdx_size()
            current_size_gb = current_size / (1024**3)
            self.display_final_report(initial_size_gb, current_size_gb)
            self.log(t("cleanup.cleanup_complete_success"))
            return True
        else:
            return False

    def display_initial_info(self):
        table = Table(title=t("cleanup.initial_info_title"))
        table.add_column(t("cleanup.property"), style="cyan")
        table.add_column(t("cleanup.value"), style="magenta")
        table.add_row(t("cleanup.version_label"), "1.0")
        table.add_row(t("cleanup.date_label"), "Setembro 2025")
        table.add_row(
            t("cleanup.running_as_admin_label"), t("cleanup.admin_yes") if self.is_admin() else t("cleanup.admin_no")
        )
        self.console.print(table)

    def display_final_report(self, initial_size_gb, current_size_gb):
        panel = Panel(
            f"""[bold]{t("cleanup.report_title")}[/bold]
            
{t("cleanup.report_datetime", datetime=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))}
{t("cleanup.report_space_saved", size=f"{self.total_space_saved:.2f}")}
{t("cleanup.report_initial_size", size=f"{initial_size_gb:.2f}")}
{t("cleanup.report_current_size", size=f"{current_size_gb:.2f}")}

[bold]{t("cleanup.report_recommendations")}[/bold]
{t("cleanup.report_rec_1")}
{t("cleanup.report_rec_2")}
{t("cleanup.report_rec_3")}
{t("cleanup.report_rec_4")}
{t("cleanup.report_rec_5")}

{t("cleanup.report_log_saved", path="wsl_docker_cleanup.log")}""",
            title=t("cleanup.report_panel_title"),
            expand=True,
        )
        self.console.print(panel)


def main():
    console = Console()
    console.print(Panel(f"[bold blue]{t('cleanup.cleaner_title')}[/bold blue]", expand=False))
    cleaner = WSLDockerCleaner()
    if not cleaner.is_admin():
        cleaner.run_as_admin()
        return
    cleaner.display_initial_info()
    success = cleaner.run_full_cleanup_with_progress()
    if success:
        console.print(
            f"\n[bold green]{t('cleanup.cleanup_done')}[/bold green] {t('cleanup.restart_docker')}"
        )
        console.print(f"[bold]{t('cleanup.press_any_key')}[/bold]")
        input()
    else:
        console.print(
            f"\n[bold red]{t('cleanup.errors_occurred')}[/bold red]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
