"""Lógica principal do limpador WSL Docker (módulo)."""

from __future__ import annotations

import asyncio
import subprocess
import os
import sys
import time
from datetime import datetime
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
import ctypes


class WSLDockerCleaner:
    def __init__(self):
        self.log_messages = []
        self.total_space_saved = 0
        self.console = Console()
        self.logger = logging.getLogger(__name__)

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
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
            self.log(f"Executando: {command}")
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                shell=shell,
                timeout=300,  # 5 minutos timeout
            )
            if result.returncode != 0 and result.stderr:
                self.log(f"Erro: {result.stderr}", "ERROR")
            return result
        except subprocess.TimeoutExpired:
            self.log(f"Timeout ao executar: {command}", "ERROR")
            return None
        except Exception as e:
            self.log(f"Erro ao executar comando: {str(e)}", "ERROR")
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
                stream_callback(f"Executando: {command}\n")
            else:
                self.log(f"Executando: {command}")

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
                    stream_callback(f"Erro (código {returncode}): {error_msg}\n")
                else:
                    self.log(f"Erro: {error_msg}", "ERROR")

            # Retornar CompletedProcess compatível
            return subprocess.CompletedProcess(
                args=command,
                returncode=returncode,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
            )

        except asyncio.TimeoutError:
            msg = f"Timeout ao executar: {command}\n"
            if stream_callback:
                stream_callback(msg)
            else:
                self.log(f"Timeout ao executar: {command}", "ERROR")
            return subprocess.CompletedProcess(command, -1, "", "Timeout")
        except Exception as e:
            msg = f"Erro ao executar comando: {str(e)}\n"
            if stream_callback:
                stream_callback(msg)
            else:
                self.log(f"Erro ao executar comando: {str(e)}", "ERROR")
            return subprocess.CompletedProcess(command, -1, "", str(e))

    async def run_elevated_command_async(
        self, command: str, stream_callback: Optional[Callable[[str], None]] = None
    ) -> subprocess.CompletedProcess:
        """Executa comando elevated (admin) via PowerShell Start-Process RunAs hidden, sem janela visível."""
        if stream_callback:
            stream_callback("Solicitando privilégios admin (UAC)...\n")

        # Escape para PS
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

        self.log(f"Executando elevated: {command}")
        return self.run_command(ps_cmd)

    def is_docker_running(self):
        """Verifica se o Docker está rodando"""
        result = self.run_command(
            'tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I "Docker Desktop.exe" >NUL',
            capture_output=True,
        )
        if result and result.returncode != 0:
            return False

        result = self.run_command("docker ps", capture_output=True)
        return result and result.returncode == 0

    def is_admin(self):
        """Verifica se o script está rodando como administrador"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

    def run_as_admin(self):
        """Reinicia o script com privilégios de administrador"""
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
                "\n[yellow]Este script requer privilégios de administrador.[/yellow]"
            )
            self.console.print(
                "[yellow]Solicitando elevação de privilégios...[/yellow]\n"
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
                f"[bold red]Erro ao solicitar privilégios de administrador: {str(e)}[/bold red]"
            )
            self.console.print(
                "[bold red]Execute o script manualmente como administrador.[/bold red]"
            )
            sys.exit(1)

    # --- Relacionados ao VHDX e Docker (copiado e mantido) ---
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
        # Include all known Docker VHDX locations (varies by Docker Desktop version)
        vhdx_paths = [
            # Newer Docker Desktop versions use 'main' subfolder
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\main\ext4.vhdx"),
            # Older Docker Desktop versions use 'data' and 'distro' subfolders
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\distro\ext4.vhdx"),
            # Alternative paths using USERPROFILE
            os.path.expandvars(
                r"%USERPROFILE%\AppData\Local\Docker\wsl\main\ext4.vhdx"
            ),
            os.path.expandvars(
                r"%USERPROFILE%\AppData\Local\Docker\wsl\data\ext4.vhdx"
            ),
            os.path.expandvars(
                r"%USERPROFILE%\AppData\Local\Docker\wsl\distro\ext4.vhdx"
            ),
        ]

        total_size = 0
        existing_files = []
        for path in vhdx_paths:
            if os.path.exists(path):
                size = os.path.getsize(path)
                total_size += size
                existing_files.append((path, size))
                size_gb = size / (1024**3)
                self.log(f"VHDX encontrado: {path} ({size_gb:.2f} GB)")
        return total_size, existing_files

    def docker_cleanup(self):
        if not self.is_docker_running():
            self.log("Docker não está rodando. Iniciando Docker Desktop...", "WARNING")
            try:
                docker_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
                if not os.path.exists(docker_path):
                    self.log(
                        f"Docker Desktop não encontrado em: {docker_path}", "ERROR"
                    )
                    self.log(
                        "Pulando limpeza do Docker. Execute o Docker Desktop manualmente e tente novamente.",
                        "WARNING",
                    )
                    return False

                subprocess.Popen([docker_path], shell=True)
                self.log("Aguardando Docker Desktop inicializar (60 segundos)...")
                max_wait = 60
                wait_interval = 5
                for i in range(0, max_wait, wait_interval):
                    time.sleep(wait_interval)
                    if self.is_docker_running():
                        self.log(
                            f"Docker iniciado com sucesso após {i + wait_interval} segundos"
                        )
                        time.sleep(5)
                        break
                    self.log(f"Aguardando... ({i + wait_interval}/{max_wait}s)")
                else:
                    self.log(
                        "Timeout ao iniciar Docker. Pulando limpeza Docker.", "ERROR"
                    )
                    return False
            except Exception as e:
                self.log(f"Erro ao iniciar Docker: {str(e)}", "ERROR")
                return False

        self.log("=== INICIANDO LIMPEZA DO DOCKER ===")

        self.log("Parando todos os containers...")
        containers_result = self.run_command("docker ps -q", capture_output=True)
        if containers_result and containers_result.stdout.strip():
            container_ids = containers_result.stdout.strip().split("\n")
            for container_id in container_ids:
                if container_id.strip():
                    self.run_command(
                        f"docker stop {container_id.strip()}", capture_output=True
                    )
                    self.log(f"Container {container_id.strip()} parado")
        else:
            self.log("Nenhum container em execução")

        self.log("Removendo containers parados...")
        result = self.run_command("docker container prune -f")
        space = self._parse_reclaimed_space(result)
        self.log(f"Espaço recuperado (containers): {space}")

        self.log("Removendo imagens não utilizadas...")
        result = self.run_command("docker image prune -af")
        space = self._parse_reclaimed_space(result)
        self.log(f"Espaço recuperado (imagens): {space}")

        self.log("Removendo volumes não utilizados...")
        result = self.run_command("docker volume prune -f")
        space = self._parse_reclaimed_space(result)
        self.log(f"Espaço recuperado (volumes): {space}")

        self.log("Removendo redes não utilizadas...")
        self.run_command("docker network prune -f")

        self.log("Executando limpeza completa do sistema Docker...")
        result = self.run_command("docker system prune -af --volumes")
        space = self._parse_reclaimed_space(result)
        self.log(f"Espaço total recuperado (sistema): {space}")

        self.log("Limpando cache de build...")
        self.run_command("docker builder prune -af")

        return True

    def stop_docker_wsl(self):
        self.log("=== PARANDO DOCKER E WSL ===")
        self.log("Parando Docker Desktop...")
        docker_processes = [
            "Docker Desktop.exe",
            "Docker.exe",
            "com.docker.backend.exe",
            "com.docker.proxy.exe",
            "dockerd.exe",
            "vpnkit.exe",
        ]
        for process in docker_processes:
            result = self.run_command(
                f'taskkill /F /IM "{process}"', capture_output=True
            )
            if result and result.returncode == 0:
                self.log(f"Processo {process} finalizado")
        time.sleep(5)

        self.log("Parando WSL...")
        result = self.run_command("wsl --shutdown", capture_output=True)
        if result:
            self.log("WSL desligado com sucesso")
        else:
            self.log("Erro ao desligar WSL", "ERROR")

        time.sleep(10)
        return True

    def configure_wsl_sparse(self):
        self.log("=== CONFIGURANDO MODO SPARSE ===")
        result = self.run_command("wsl -l -v")
        if not result:
            return False
        distributions = ["docker-desktop", "docker-desktop-data"]
        for distro in distributions:
            self.log(f"Configurando sparse para {distro}...")
            self.run_command(f'wsl --manage "{distro}" --set-sparse true')
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
            self.log(f"Arquivo .wslconfig atualizado: {wslconfig_path}")
        except Exception as e:
            self.log(f"Erro ao criar .wslconfig: {str(e)}", "ERROR")
        return True

    def compact_vhdx_files(self):
        if not self.is_admin():
            self.log("Execução como administrador recomendada", "WARNING")
            return False
        self.log("=== COMPACTANDO ARQUIVOS VHDX ===")
        # Include all known Docker VHDX locations (varies by Docker Desktop version)
        vhdx_paths = [
            # Newer Docker Desktop versions use 'main' subfolder
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\main\ext4.vhdx"),
            # Older Docker Desktop versions use 'data' and 'distro' subfolders
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\distro\ext4.vhdx"),
        ]
        success = False
        for vhdx_path in vhdx_paths:
            if os.path.exists(vhdx_path):
                size_before = os.path.getsize(vhdx_path)
                size_before_gb = size_before / (1024**3)
                self.log(f"Compactando {vhdx_path} ({size_before_gb:.2f} GB)...")
                ps_command = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                result = self.run_elevated_command(ps_command)
                if result and result.returncode == 0:
                    time.sleep(5)
                    if os.path.exists(vhdx_path):
                        size_after = os.path.getsize(vhdx_path)
                        size_after_gb = size_after / (1024**3)
                        space_saved = (size_before - size_after) / (1024**3)
                        self.total_space_saved += space_saved
                        self.log(
                            f"Compactação concluída: {size_after_gb:.2f} GB (economizado: {space_saved:.2f} GB)"
                        )
                        success = True
                    else:
                        self.log(
                            f"Arquivo não encontrado após compactação: {vhdx_path}",
                            "ERROR",
                        )
                else:
                    self.log(f"Erro na compactação de {vhdx_path}", "ERROR")
        return success

    def cleanup_temp_files(self):
        self.log("=== LIMPANDO ARQUIVOS TEMPORÁRIOS ===")
        temp_paths = [
            os.path.expandvars(r"%TEMP%"),
            os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\log"),
            r"C:\Windows\Temp",  # System temp folder
        ]

        total_files_deleted = 0
        total_bytes_deleted = 0

        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                self.log(f"Limpando: {temp_path}")
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
                            f"{files_deleted} arquivo(s) removido(s) de {temp_path} ({bytes_mb:.2f} MB)"
                        )

                    total_files_deleted += files_deleted
                    total_bytes_deleted += bytes_deleted

                except Exception as e:
                    self.log(f"Erro limpando {temp_path}: {str(e)}", "ERROR")

        if total_files_deleted > 0:
            total_mb = total_bytes_deleted / (1024 * 1024)
            self.log(
                f"Total limpo: {total_files_deleted} arquivo(s), {total_mb:.2f} MB"
            )

        return True

    def cleanup_recycle_bin(self):
        """Esvazia a lixeira do Windows."""
        self.log("=== ESVAZIANDO LIXEIRA ===")
        try:
            # Use PowerShell to clear the recycle bin silently
            ps_command = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
            result = self.run_command(f'powershell -NoProfile -Command "{ps_command}"')

            if result and result.returncode == 0:
                self.log("Lixeira esvaziada com sucesso")
                return True
            else:
                # Clear-RecycleBin might fail if bin is already empty, that's okay
                self.log("Lixeira já estava vazia ou não pôde ser esvaziada")
                return True
        except Exception as e:
            self.log(f"Erro ao esvaziar lixeira: {str(e)}", "ERROR")
            return False

    async def cleanup_recycle_bin_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de cleanup_recycle_bin com streaming."""
        if stream_callback:
            stream_callback("=== ESVAZIANDO LIXEIRA ===\n")

        try:
            ps_command = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
            result = await self.run_command_async(
                f'powershell -NoProfile -Command "{ps_command}"',
                shell=True,
                stream_callback=stream_callback,
            )

            if result and result.returncode == 0:
                if stream_callback:
                    stream_callback("Lixeira esvaziada com sucesso\n")
                return True
            else:
                if stream_callback:
                    stream_callback(
                        "Lixeira já estava vazia ou não pôde ser esvaziada\n"
                    )
                return True
        except Exception as e:
            if stream_callback:
                stream_callback(f"Erro ao esvaziar lixeira: {str(e)}\n")
            return False

    async def cleanup_temp_files_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de cleanup_temp_files com streaming."""
        if stream_callback:
            stream_callback("=== LIMPANDO ARQUIVOS TEMPORÁRIOS ===\n")

        temp_paths = [
            os.path.expandvars(r"%TEMP%"),
            os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\log"),
            r"C:\Windows\Temp",  # System temp folder
        ]

        total_deleted = 0
        total_bytes = 0

        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                if stream_callback:
                    stream_callback(f"Limpando: {temp_path}\n")

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
                            f"{files_deleted} arquivo(s) removido(s) ({bytes_mb:.2f} MB)\n"
                        )

                    total_deleted += files_deleted
                    total_bytes += bytes_deleted

                except Exception as e:
                    if stream_callback:
                        stream_callback(f"Erro limpando {temp_path}: {str(e)}\n")

        if stream_callback and total_deleted > 0:
            total_mb = total_bytes / (1024 * 1024)
            stream_callback(
                f"Total limpo: {total_deleted} arquivo(s), {total_mb:.2f} MB\n"
            )

        return total_deleted > 0

    # ========== MÉTODOS ASYNC COM STREAMING ==========

    async def docker_cleanup_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de docker_cleanup com streaming de saída em tempo real."""
        if stream_callback:
            stream_callback("=== INICIANDO LIMPEZA DO DOCKER ===\n")
        else:
            self.log("=== INICIANDO LIMPEZA DO DOCKER ===")

        # Parar containers
        if stream_callback:
            stream_callback("Parando todos os containers...\n")

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
            stream_callback("Removendo containers parados...\n")
        await self.run_command_async(
            "docker container prune -f", shell=True, stream_callback=stream_callback
        )

        # Prune images
        if stream_callback:
            stream_callback("Removendo imagens não utilizadas...\n")
        await self.run_command_async(
            "docker image prune -af", shell=True, stream_callback=stream_callback
        )

        # Prune volumes
        if stream_callback:
            stream_callback("Removendo volumes não utilizados...\n")
        await self.run_command_async(
            "docker volume prune -f", shell=True, stream_callback=stream_callback
        )

        # Prune networks
        if stream_callback:
            stream_callback("Removendo redes não utilizadas...\n")
        await self.run_command_async(
            "docker network prune -f", shell=True, stream_callback=stream_callback
        )

        # System prune completo
        if stream_callback:
            stream_callback("Executando limpeza completa do sistema Docker...\n")
        await self.run_command_async(
            "docker system prune -af --volumes",
            shell=True,
            stream_callback=stream_callback,
        )

        # Build cache
        if stream_callback:
            stream_callback("Limpando cache de build...\n")
        await self.run_command_async(
            "docker builder prune -af", shell=True, stream_callback=stream_callback
        )

        if stream_callback:
            stream_callback("=== LIMPEZA DO DOCKER CONCLUÍDA ===\n")

        return True

    async def stop_docker_wsl_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de stop_docker_wsl com batch elevated único."""
        if stream_callback:
            stream_callback("=== PARANDO DOCKER E WSL (batch elevated) ===\n")

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
            stream_callback("Executando batch kill + wsl shutdown...\n")
            stream_callback("Solicitando privilégios admin (UAC único)...\n")

        result = await self.run_elevated_command_async(
            ps_batch_cmd, stream_callback=stream_callback
        )

        await asyncio.sleep(10)

        if stream_callback:
            stream_callback("=== DOCKER E WSL PARADOS ===\n")

        return result.returncode == 0 if result else False

    async def configure_wsl_sparse_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async com batch elevated."""
        if stream_callback:
            stream_callback("=== CONFIGURANDO MODO SPARSE ===\n")

        # List distros first (non-elevated)
        result = await self.run_command_async(
            "wsl -l -v", shell=True, stream_callback=stream_callback
        )
        if not result or result.returncode != 0:
            if stream_callback:
                stream_callback("Erro listando WSL distros.\n")
            return False

        distributions = ["docker-desktop", "docker-desktop-data"]
        sparse_cmds = "; ".join(
            [f'wsl --manage "{distro}" --set-sparse true' for distro in distributions]
        )

        if stream_callback:
            stream_callback(f"Configurando sparse para {', '.join(distributions)}...\n")
            stream_callback("Solicitando privilégios admin (UAC único)...\n")

        result = await self.run_elevated_command_async(
            sparse_cmds, stream_callback=stream_callback
        )

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
                stream_callback(f".wslconfig atualizado: {wslconfig_path}\n")
        except Exception as e:
            if stream_callback:
                stream_callback(f"Erro .wslconfig: {str(e)}\n")

        return True

    async def compact_vhdx_files_async(
        self, stream_callback: Optional[Callable[[str], None]] = None
    ):
        """Versão async de compact_vhdx_files com streaming."""

        if stream_callback:
            stream_callback("=== COMPACTANDO ARQUIVOS VHDX ===\n")

        vhdx_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\distro\ext4.vhdx"),
        ]

        success = False
        for vhdx_path in vhdx_paths:
            if os.path.exists(vhdx_path):
                size_before = os.path.getsize(vhdx_path)
                size_before_gb = size_before / (1024**3)

                if stream_callback:
                    stream_callback(
                        f"Compactando {vhdx_path} ({size_before_gb:.2f} GB)...\n"
                    )

                ps_command = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                result = await self.run_elevated_command_async(
                    ps_command, stream_callback=stream_callback
                )

                if result and result.returncode == 0:
                    await asyncio.sleep(5)
                    if os.path.exists(vhdx_path):
                        size_after = os.path.getsize(vhdx_path)
                        size_after_gb = size_after / (1024**3)
                        space_saved = (size_before - size_after) / (1024**3)
                        self.total_space_saved += space_saved

                        if stream_callback:
                            stream_callback(
                                f"Compactação concluída: {size_after_gb:.2f} GB (economizado: {space_saved:.2f} GB)\n"
                            )
                        success = True
                    else:
                        if stream_callback:
                            stream_callback(
                                f"Arquivo não encontrado após compactação: {vhdx_path}\n"
                            )
                else:
                    if stream_callback:
                        stream_callback(f"Erro na compactação de {vhdx_path}\n")

        return success

    def generate_report(self):
        self.log("=== RELATÓRIO FINAL ===")
        current_size, files = self.get_docker_vhdx_size()
        current_size_gb = current_size / (1024**3)
        report = f"""
RELATÓRIO DE LIMPEZA WSL DOCKER
{"=" * 50}
Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Espaço total economizado: {self.total_space_saved:.2f} GB
Tamanho atual dos VHDX: {current_size_gb:.2f} GB

Arquivos VHDX encontrados:
{chr(10).join([f"  - {f[0]} ({f[1] / (1024**3):.2f} GB)" for f in files])}

RECOMENDAÇÕES:
1. Execute este script regularmente (semanal/mensal)
2. Configure limpeza automática do Docker: docker system prune --schedule
3. Use imagens base menores (alpine, slim)
4. Configure .dockerignore para reduzir contexto de build
5. Monitore uso de espaço: docker system df

Log completo salvo em: wsl_docker_cleanup.log
        """
        print(report)
        try:
            with open("wsl_docker_cleanup.log", "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_messages))
                f.write("\n\n" + report)
            self.log("Log salvo em: wsl_docker_cleanup.log")
        except Exception as e:
            self.log(f"Erro ao salvar log: {str(e)}", "ERROR")

    def run_full_cleanup_with_progress(self):
        self.log("INICIANDO LIMPEZA COMPLETA DO WSL DOCKER")
        self.log(
            f"Executando como administrador: {'Sim' if self.is_admin() else 'Não'}"
        )
        initial_size, _ = self.get_docker_vhdx_size()
        initial_size_gb = initial_size / (1024**3)
        self.log(f"Tamanho inicial dos VHDX: {initial_size_gb:.2f} GB")
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
            "[cyan]Executando limpeza completa...", total=100
        )
        with Live(progress_group, refresh_per_second=10, console=self.console):
            try:
                current_task = current_task_progress.add_task("Limpando Docker...")
                overall_progress.update(
                    overall_task, description="[cyan]Limpando Docker..."
                )
                if self.docker_cleanup():
                    self.log("Limpeza do Docker concluída com sucesso")
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=30)

                current_task = current_task_progress.add_task("Parando Docker e WSL...")
                overall_progress.update(
                    overall_task, description="[cyan]Parando Docker e WSL..."
                )
                self.stop_docker_wsl()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=15)

                current_task = current_task_progress.add_task(
                    "Configurando sparse mode..."
                )
                overall_progress.update(
                    overall_task, description="[cyan]Configurando sparse mode..."
                )
                self.configure_wsl_sparse()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=15)

                current_task = current_task_progress.add_task(
                    "Compactando arquivos VHDX..."
                )
                overall_progress.update(
                    overall_task, description="[cyan]Compactando arquivos VHDX..."
                )
                self.compact_vhdx_files()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=20)

                current_task = current_task_progress.add_task(
                    "Limpando arquivos temporários..."
                )
                overall_progress.update(
                    overall_task, description="[cyan]Limpando arquivos temporários..."
                )
                self.cleanup_temp_files()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=10)

                current_task = current_task_progress.add_task("Esvaziando lixeira...")
                overall_progress.update(
                    overall_task, description="[cyan]Esvaziando lixeira..."
                )
                self.cleanup_recycle_bin()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=5)

                overall_progress.update(
                    overall_task, description="[green]Limpeza concluída!"
                )

                current_size, _ = self.get_docker_vhdx_size()
                current_size_gb = current_size / (1024**3)
                self.display_final_report(initial_size_gb, current_size_gb)
                self.log("LIMPEZA CONCLUÍDA COM SUCESSO!")
                return True
            except Exception as e:
                self.log(f"Erro durante limpeza: {str(e)}", "ERROR")
                return False

    def display_initial_info(self):
        table = Table(title="Informações Iniciais")
        table.add_column("Propriedade", style="cyan")
        table.add_column("Valor", style="magenta")
        table.add_row("Versão", "1.0")
        table.add_row("Data", "Setembro 2025")
        table.add_row(
            "Executando como administrador", "Sim" if self.is_admin() else "Não"
        )
        self.console.print(table)

    def display_final_report(self, initial_size_gb, current_size_gb):
        panel = Panel(
            f"""[bold]RELATÓRIO DE LIMPEZA WSL DOCKER[/bold]
            
Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Espaço total economizado: {self.total_space_saved:.2f} GB
Tamanho inicial dos VHDX: {initial_size_gb:.2f} GB
Tamanho atual dos VHDX: {current_size_gb:.2f} GB

[bold]RECOMENDAÇÕES:[/bold]
1. Execute este script regularmente (semanal/mensal)
2. Configure limpeza automática do Docker: docker system prune --schedule
3. Use imagens base menores (alpine, slim)
4. Configure .dockerignore para reduzir contexto de build
5. Monitore uso de espaço: docker system df

Log completo salvo em: wsl_docker_cleanup.log""",
            title="Relatório Final",
            expand=True,
        )
        self.console.print(panel)


def main():
    console = Console()
    console.print(Panel("[bold blue]WSL Docker Cleaner v1.0[/bold blue]", expand=False))
    if not sys.platform.startswith("win"):
        print("Este script é específico para Windows!")
        sys.exit(1)
    cleaner = WSLDockerCleaner()
    if not cleaner.is_admin():
        cleaner.run_as_admin()
        return
    cleaner.display_initial_info()
    success = cleaner.run_full_cleanup_with_progress()
    if success:
        console.print(
            "\n[bold green]Limpeza concluída![/bold green] Reinicie o Docker Desktop para aplicar as alterações."
        )
        console.print("[bold]Pressione qualquer tecla para continuar...[/bold]")
        input()
    else:
        console.print(
            "\n[bold red]Ocorreram erros durante a limpeza. Verifique o log para detalhes.[/bold red]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
