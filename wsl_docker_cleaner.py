
"""
Script para reduzir o tamanho do WSL Docker no Windows 11
Autor: Sistema de Limpeza WSL Docker
Versão: 1.0
Data: Setembro 2025
"""

import subprocess
import os
import sys
import time
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
import ctypes

class WSLDockerCleaner:
    def __init__(self):
        self.log_messages = []
        self.total_space_saved = 0
        self.console = Console()

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        self.console.print(f"[bold]{timestamp}[/bold] [{level}] {message}")
        self.log_messages.append(log_msg)

    def run_command(self, command, capture_output=True, shell=True):
        """Executa um comando e retorna o resultado"""
        try:
            self.log(f"Executando: {command}")
            result = subprocess.run(
                command, 
                capture_output=capture_output, 
                text=True, 
                shell=shell,
                timeout=300  # 5 minutos timeout
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

    def is_docker_running(self):
        """Verifica se o Docker está rodando"""
        # Verifica se o processo do Docker Desktop está rodando
        result = self.run_command('tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I "Docker Desktop.exe" >NUL', capture_output=True)
        if result and result.returncode != 0:
            return False
        
        # Verifica se o Docker daemon está respondendo
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
            # Obtém o caminho do Python atual
            python_exe = sys.executable
            script_path = os.path.abspath(__file__)
            
            # Parâmetros para o ShellExecute
            params = f'"{script_path}"'
            
            self.console.print("\n[yellow]Este script requer privilégios de administrador.[/yellow]")
            self.console.print("[yellow]Solicitando elevação de privilégios...[/yellow]\n")
            
            # Executa o script como administrador
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                python_exe, 
                params, 
                None, 
                1  # SW_SHOW
            )
            
            # Encerra o script atual
            sys.exit(0)
            
        except Exception as e:
            self.console.print(f"[bold red]Erro ao solicitar privilégios de administrador: {str(e)}[/bold red]")
            self.console.print("[bold red]Execute o script manualmente como administrador.[/bold red]")
            sys.exit(1)

    def get_docker_vhdx_size(self):
        """Obtém o tamanho atual dos arquivos VHDX do Docker"""
        vhdx_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\distro\ext4.vhdx"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Docker\wsl\data\ext4.vhdx"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Docker\wsl\distro\ext4.vhdx")
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
        """Executa limpeza completa do Docker"""
        if not self.is_docker_running():
            self.log("Docker não está rodando. Iniciando Docker Desktop...", "WARNING")
            # Tenta iniciar o Docker Desktop
            try:
                docker_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
                if not os.path.exists(docker_path):
                    self.log(f"Docker Desktop não encontrado em: {docker_path}", "ERROR")
                    self.log("Pulando limpeza do Docker. Execute o Docker Desktop manualmente e tente novamente.", "WARNING")
                    return False
                
                subprocess.Popen([docker_path], shell=True)
                self.log("Aguardando Docker Desktop inicializar (60 segundos)...")
                
                # Aguarda até 60 segundos verificando a cada 5 segundos
                max_wait = 60
                wait_interval = 5
                for i in range(0, max_wait, wait_interval):
                    time.sleep(wait_interval)
                    if self.is_docker_running():
                        self.log(f"Docker iniciado com sucesso após {i + wait_interval} segundos")
                        time.sleep(5)  # Aguarda mais um pouco para estabilizar
                        break
                    self.log(f"Aguardando... ({i + wait_interval}/{max_wait}s)")
                else:
                    self.log("Timeout ao iniciar Docker. Pulando limpeza Docker.", "ERROR")
                    return False
            except Exception as e:
                self.log(f"Erro ao iniciar Docker: {str(e)}", "ERROR")
                return False

        self.log("=== INICIANDO LIMPEZA DO DOCKER ===")

        # 1. Parar todos os containers
        self.log("Parando todos os containers...")
        # Usar PowerShell para parar containers
        containers_result = self.run_command("docker ps -q", capture_output=True)
        if containers_result and containers_result.stdout.strip():
            container_ids = containers_result.stdout.strip().split('\n')
            for container_id in container_ids:
                if container_id.strip():
                    self.run_command(f"docker stop {container_id.strip()}", capture_output=True)
                    self.log(f"Container {container_id.strip()} parado")
        else:
            self.log("Nenhum container em execução")

        # 2. Remover containers parados
        self.log("Removendo containers parados...")
        result = self.run_command("docker container prune -f")
        if result and "Total reclaimed space" in result.stdout:
            self.log(f"Espaço recuperado (containers): {result.stdout.split('Total reclaimed space:')[1].strip()}")

        # 3. Remover imagens não utilizadas (agressivo)
        self.log("Removendo imagens não utilizadas...")
        result = self.run_command("docker image prune -af")
        if result and "Total reclaimed space" in result.stdout:
            self.log(f"Espaço recuperado (imagens): {result.stdout.split('Total reclaimed space:')[1].strip()}")

        # 4. Remover volumes órfãos
        self.log("Removendo volumes não utilizados...")
        result = self.run_command("docker volume prune -f")
        if result and "Total reclaimed space" in result.stdout:
            self.log(f"Espaço recuperado (volumes): {result.stdout.split('Total reclaimed space:')[1].strip()}")

        # 5. Remover redes não utilizadas
        self.log("Removendo redes não utilizadas...")
        self.run_command("docker network prune -f")

        # 6. Limpeza completa do sistema (mais agressiva)
        self.log("Executando limpeza completa do sistema Docker...")
        result = self.run_command("docker system prune -af --volumes")
        if result and "Total reclaimed space" in result.stdout:
            self.log(f"Espaço total recuperado (sistema): {result.stdout.split('Total reclaimed space:')[1].strip()}")

        # 7. Limpar cache de build
        self.log("Limpando cache de build...")
        self.run_command("docker builder prune -af")

        return True

    def stop_docker_wsl(self):
        """Para o Docker e WSL"""
        self.log("=== PARANDO DOCKER E WSL ===")

        # Parar Docker Desktop
        self.log("Parando Docker Desktop...")
        # Listar todos os processos relacionados ao Docker
        docker_processes = [
            "Docker Desktop.exe",
            "Docker.exe",
            "com.docker.backend.exe",
            "com.docker.proxy.exe",
            "dockerd.exe",
            "vpnkit.exe"
        ]
        
        for process in docker_processes:
            result = self.run_command(f'taskkill /F /IM "{process}"', capture_output=True)
            if result and result.returncode == 0:
                self.log(f"Processo {process} finalizado")

        time.sleep(5)

        # Parar WSL
        self.log("Parando WSL...")
        result = self.run_command("wsl --shutdown", capture_output=True)
        if result:
            self.log("WSL desligado com sucesso")
        else:
            self.log("Erro ao desligar WSL", "ERROR")

        time.sleep(10)  # Aguarda WSL parar completamente
        return True

    def configure_wsl_sparse(self):
        """Configura o modo sparse no WSL para compactação automática"""
        self.log("=== CONFIGURANDO MODO SPARSE ===")

        # Verificar distribuições WSL
        result = self.run_command("wsl -l -v")
        if not result:
            return False

        # Configurar sparse para docker-desktop e docker-desktop-data
        distributions = ["docker-desktop", "docker-desktop-data"]

        for distro in distributions:
            self.log(f"Configurando sparse para {distro}...")
            self.run_command(f'wsl --manage "{distro}" --set-sparse true')

        # Criar/atualizar arquivo .wslconfig
        wslconfig_path = os.path.expanduser("~/.wslconfig")
        wslconfig_content = """[wsl2]
sparseVhd=true
memory=4GB
processors=4
swap=2GB
swapFile=%TEMP%\\wsl-swap.vhdx
"""

        try:
            with open(wslconfig_path, 'w', encoding='utf-8') as f:
                f.write(wslconfig_content)
            self.log(f"Arquivo .wslconfig atualizado: {wslconfig_path}")
        except Exception as e:
            self.log(f"Erro ao criar .wslconfig: {str(e)}", "ERROR")

        return True

    def compact_vhdx_files(self):
        """Compacta os arquivos VHDX usando Optimize-VHD"""
        if not self.is_admin():
            self.log("AVISO: Execução como administrador recomendada para compactação VHDX", "WARNING")
            return False

        self.log("=== COMPACTANDO ARQUIVOS VHDX ===")

        vhdx_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\distro\ext4.vhdx")
        ]

        success = False
        for vhdx_path in vhdx_paths:
            if os.path.exists(vhdx_path):
                size_before = os.path.getsize(vhdx_path)
                size_before_gb = size_before / (1024**3)

                self.log(f"Compactando {vhdx_path} ({size_before_gb:.2f} GB)...")

                # Usar PowerShell para executar Optimize-VHD
                ps_command = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                result = self.run_command(f'powershell -Command "{ps_command}"')

                if result and result.returncode == 0:
                    time.sleep(5)  # Aguarda compactação
                    if os.path.exists(vhdx_path):
                        size_after = os.path.getsize(vhdx_path)
                        size_after_gb = size_after / (1024**3)
                        space_saved = (size_before - size_after) / (1024**3)
                        self.total_space_saved += space_saved

                        self.log(f"Compactação concluída: {size_after_gb:.2f} GB (economizado: {space_saved:.2f} GB)")
                        success = True
                    else:
                        self.log(f"Arquivo não encontrado após compactação: {vhdx_path}", "ERROR")
                else:
                    self.log(f"Erro na compactação de {vhdx_path}", "ERROR")

        return success

    def cleanup_temp_files(self):
        """Limpa arquivos temporários relacionados ao Docker/WSL"""
        self.log("=== LIMPANDO ARQUIVOS TEMPORÁRIOS ===")

        temp_paths = [
            os.path.expandvars(r"%TEMP%"),
            os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\log")
        ]

        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                self.log(f"Limpando: {temp_path}")
                try:
                    # Remover arquivos .log e .tmp do Docker usando Python
                    import glob
                    patterns = ["*.log", "*.tmp", "*docker*.log", "*docker*.tmp"]
                    files_deleted = 0
                    for pattern in patterns:
                        search_pattern = os.path.join(temp_path, pattern)
                        for file_path in glob.glob(search_pattern):
                            try:
                                os.remove(file_path)
                                files_deleted += 1
                            except Exception:
                                pass  # Ignorar arquivos em uso
                    if files_deleted > 0:
                        self.log(f"{files_deleted} arquivo(s) temporário(s) removido(s) de {temp_path}")
                except Exception as e:
                    self.log(f"Erro limpando {temp_path}: {str(e)}", "ERROR")

    def generate_report(self):
        """Gera relatório final da limpeza"""
        self.log("=== RELATÓRIO FINAL ===")

        # Obter tamanho atual dos VHDX
        current_size, files = self.get_docker_vhdx_size()
        current_size_gb = current_size / (1024**3)

        report = f"""
RELATÓRIO DE LIMPEZA WSL DOCKER
{'='*50}
Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Espaço total economizado: {self.total_space_saved:.2f} GB
Tamanho atual dos VHDX: {current_size_gb:.2f} GB

Arquivos VHDX encontrados:
{chr(10).join([f"  - {f[0]} ({f[1]/(1024**3):.2f} GB)" for f in files])}

RECOMENDAÇÕES:
1. Execute este script regularmente (semanal/mensal)
2. Configure limpeza automática do Docker: docker system prune --schedule
3. Use imagens base menores (alpine, slim)
4. Configure .dockerignore para reduzir contexto de build
5. Monitore uso de espaço: docker system df

Log completo salvo em: wsl_docker_cleanup.log
        """

        print(report)

        # Salvar log em arquivo
        try:
            with open("wsl_docker_cleanup.log", "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_messages))
                f.write("\n\n" + report)
            self.log("Log salvo em: wsl_docker_cleanup.log")
        except Exception as e:
            self.log(f"Erro ao salvar log: {str(e)}", "ERROR")

    def run_full_cleanup_with_progress(self):
        """Executa limpeza completa com barra de progresso"""
        self.log("INICIANDO LIMPEZA COMPLETA DO WSL DOCKER")
        self.log(f"Executando como administrador: {'Sim' if self.is_admin() else 'Não'}")

        # Obter tamanho inicial
        initial_size, _ = self.get_docker_vhdx_size()
        initial_size_gb = initial_size / (1024**3)
        self.log(f"Tamanho inicial dos VHDX: {initial_size_gb:.2f} GB")

        # Criar diferentes barras de progresso para diferentes estágios
        overall_progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        
        current_task_progress = Progress(
            TextColumn("{task.description}"),
            console=self.console
        )
        
        # Agrupar as barras de progresso
        from rich.console import Group
        progress_group = Group(
            Panel(Group(current_task_progress)),
            overall_progress
        )
        
        # Adicionar tarefa geral
        overall_task = overall_progress.add_task("[cyan]Executando limpeza completa...", total=100)
        
        with Live(progress_group, refresh_per_second=10, console=self.console):
            try:
                # 1. Limpeza do Docker (30%)
                current_task = current_task_progress.add_task("Limpando Docker...")
                overall_progress.update(overall_task, description="[cyan]Limpando Docker...")
                if self.docker_cleanup():
                    self.log("Limpeza do Docker concluída com sucesso")
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=30)

                # 2. Parar Docker e WSL (15%)
                current_task = current_task_progress.add_task("Parando Docker e WSL...")
                overall_progress.update(overall_task, description="[cyan]Parando Docker e WSL...")
                self.stop_docker_wsl()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=15)

                # 3. Configurar sparse mode (15%)
                current_task = current_task_progress.add_task("Configurando sparse mode...")
                overall_progress.update(overall_task, description="[cyan]Configurando sparse mode...")
                self.configure_wsl_sparse()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=15)

                # 4. Compactar VHDX (25%)
                current_task = current_task_progress.add_task("Compactando arquivos VHDX...")
                overall_progress.update(overall_task, description="[cyan]Compactando arquivos VHDX...")
                self.compact_vhdx_files()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=25)

                # 5. Limpar arquivos temporários (10%)
                current_task = current_task_progress.add_task("Limpando arquivos temporários...")
                overall_progress.update(overall_task, description="[cyan]Limpando arquivos temporários...")
                self.cleanup_temp_files()
                current_task_progress.remove_task(current_task)
                overall_progress.update(overall_task, advance=10)
                overall_progress.update(overall_task, description="[green]Limpeza concluída!")

                # 6. Gerar relatório
                current_size, _ = self.get_docker_vhdx_size()
                current_size_gb = current_size / (1024**3)
                self.display_final_report(initial_size_gb, current_size_gb)

                self.log("LIMPEZA CONCLUÍDA COM SUCESSO!")
                
                return True

            except Exception as e:
                self.log(f"Erro durante limpeza: {str(e)}", "ERROR")
                return False

    def display_initial_info(self):
        """Exibe informações iniciais com rich"""
        table = Table(title="Informações Iniciais")
        table.add_column("Propriedade", style="cyan")
        table.add_column("Valor", style="magenta")

        table.add_row("Versão", "1.0")
        table.add_row("Data", "Setembro 2025")
        table.add_row("Executando como administrador", "Sim" if self.is_admin() else "Não")

        self.console.print(table)

    def display_final_report(self, initial_size_gb, current_size_gb):
        """Exibe relatório final com rich"""
        panel = Panel(
            f"""[bold]RELATÓRIO DE LIMPEZA WSL DOCKER[/bold]
            
Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
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
            expand=True
        )
        self.console.print(panel)

def main():
    """Função principal"""
    console = Console()
    console.print(Panel("[bold blue]WSL Docker Cleaner v1.0[/bold blue]", expand=False))

    # Verificar sistema
    if not sys.platform.startswith('win'):
        print("Este script é específico para Windows!")
        sys.exit(1)

    # Criar instância do limpador
    cleaner = WSLDockerCleaner()
    
    # Verificar se está rodando como administrador
    if not cleaner.is_admin():
        cleaner.run_as_admin()
        return

    # Exibir informações iniciais
    cleaner.display_initial_info()

    # Executar limpeza com barra de progresso
    success = cleaner.run_full_cleanup_with_progress()

    if success:
        console.print("\n[bold green]Limpeza concluída![/bold green] Reinicie o Docker Desktop para aplicar as alterações.")
        console.print("[bold]Pressione qualquer tecla para continuar...[/bold]")
        input()
    else:
        console.print("\n[bold red]Ocorreram erros durante a limpeza. Verifique o log para detalhes.[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
