"""
V's Speed Tester - Monitor de Velocidade de Internet em Tempo Real

Funcionalidades:
    - Teste contínuo de velocidade de download/upload em background
    - Múltiplos provedores (Speedtest.net, Fast.com) com rotação automática
    - Comparação com velocidade contratada (regulamentação ANATEL - mínimo 80%)
    - Thread separada para não bloquear a interface
"""

import datetime
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Deque
from collections import deque


@dataclass
class SpeedTestResult:
    """Resultado de um teste de velocidade."""

    download_mbps: float
    upload_mbps: float
    ping_ms: float
    servidor: str
    timestamp: datetime.datetime
    provider_name: str = "Desconhecido"  # Identifica qual provedor fez o teste


@dataclass
class SpeedTestConfig:
    """Configuração de velocidade contratada."""

    velocidade_contratada_down: float = 500.0  # Mbps
    velocidade_contratada_up: float = 100.0  # Mbps
    percentual_minimo: float = 80.0  # ANATEL exige mínimo de 80%
    total_timeout_seconds: float = 180.0


@dataclass
class SpeedStats:
    """Estatísticas de histórico de velocidade com suporte a múltiplos provedores."""

    history_down: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    history_up: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    timestamps: Deque[datetime.datetime] = field(
        default_factory=lambda: deque(maxlen=50)
    )
    history_providers: Deque[str] = field(default_factory=lambda: deque(maxlen=50))
    last_result: Optional[SpeedTestResult] = None
    is_testing: bool = False
    test_count: int = 0
    last_error: Optional[str] = None
    current_provider: str = ""  # Provedor sendo testado atualmente

    # Resultados por provedor (para exibição alternada)
    results_by_provider: dict = field(default_factory=dict)
    provider_names: list = field(default_factory=list)

    def add(self, result: SpeedTestResult):
        self.history_down.append(result.download_mbps)
        self.history_up.append(result.upload_mbps)
        self.timestamps.append(result.timestamp)
        self.last_result = result

        # Armazenar provedor
        provider = getattr(result, "provider_name", "Desconhecido")
        self.history_providers.append(provider)

        self.test_count += 1

        # Armazenar por provedor
        self.results_by_provider[provider] = result
        if provider not in self.provider_names:
            self.provider_names.append(provider)


class ContinuousSpeedTester:
    """
    Testador de velocidade contínuo que roda em background.

    Executa testes de velocidade em loop numa thread separada,
    sem bloquear a interface principal. Usa múltiplos provedores
    com rotação automática (Speedtest.net, Fast.com).
    """

    def __init__(self, config: SpeedTestConfig):
        self.config = config
        self.stats = SpeedStats()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()  # Lock para thread-safety
        self._provider_lock = threading.Lock()
        self._provider_index = 0
        self._multi_provider = None
        self._stop_event = threading.Event()
        self._cancel_event = threading.Event()
        # A one-shot test is reserved on the UI thread before its worker is
        # scheduled.  Keeping the prepared and executing phases explicit closes
        # the small window where an immediate Cancel click used to see
        # ``stats.is_testing == False`` and get lost.
        self._test_prepared = False
        self._test_executing = False
        self._process_lock = threading.Lock()
        self._active_process: subprocess.Popen[str] | None = None

    @staticmethod
    def _available_provider_ids() -> list[tuple[str, str]]:
        candidates = (
            ("speedtest", "Speedtest.net", "speedtest"),
            ("fast", "Fast.com", "requests"),
            ("brasil_banda_larga", "BrasilBandaLarga", "selenium"),
            ("simet", "SIMET/NIC.br", "selenium"),
        )
        return [
            (provider_id, label)
            for provider_id, label, dependency in candidates
            if importlib.util.find_spec(dependency) is not None
        ]

    def _next_provider(self) -> tuple[str, str] | None:
        available = self._available_provider_ids()
        if not available:
            return None
        with self._provider_lock:
            selected = available[self._provider_index % len(available)]
            self._provider_index += 1
        return selected

    @staticmethod
    def _terminate_process_tree(
        process: subprocess.Popen[str], *, grace_seconds: float = 0.6
    ) -> None:
        if process.poll() is not None:
            return
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=grace_seconds)
                return
            except Exception:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except Exception:
                    pass
                return
        try:
            import psutil

            parent = psutil.Process(process.pid)
            descendants = parent.children(recursive=True)
            for child in descendants:
                try:
                    child.terminate()
                except psutil.Error:
                    pass
            try:
                process.terminate()
            except OSError:
                pass
            _, alive = psutil.wait_procs(
                descendants,
                timeout=grace_seconds,
            )
            for child in alive:
                try:
                    child.kill()
                except psutil.Error:
                    pass
            try:
                process.wait(timeout=grace_seconds)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        except Exception:
            try:
                process.kill()
            except OSError:
                pass

    def _run_provider_process(self, provider_id: str) -> Optional[SpeedTestResult]:
        if self._cancel_event.is_set():
            with self._lock:
                self.stats.last_error = "Teste cancelado"
            return None
        command = [
            sys.executable,
            "-m",
            "monitor.speed_worker",
            "--provider",
            provider_id,
        ]
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "stdin": subprocess.DEVNULL,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "shell": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            ) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(command, **kwargs)
        except OSError as exc:
            with self._lock:
                self.stats.last_error = str(exc)[:120]
            return None
        with self._process_lock:
            self._active_process = process
        deadline = time.monotonic() + max(1.0, self.config.total_timeout_seconds)
        stdout = ""
        stderr = ""
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    if self._cancel_event.is_set():
                        self._terminate_process_tree(process)
                        try:
                            stdout, stderr = process.communicate(timeout=1.0)
                        except (OSError, subprocess.TimeoutExpired):
                            stdout, stderr = "", ""
                        with self._lock:
                            self.stats.last_error = "Teste cancelado"
                        return None
                    if time.monotonic() >= deadline:
                        self._terminate_process_tree(process)
                        try:
                            stdout, stderr = process.communicate(timeout=1.0)
                        except (OSError, subprocess.TimeoutExpired):
                            stdout, stderr = "", ""
                        with self._lock:
                            self.stats.last_error = "Tempo limite total excedido"
                        return None
        finally:
            with self._process_lock:
                if self._active_process is process:
                    self._active_process = None
        payload = None
        for line in reversed(stdout.splitlines()):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                break
        if process.returncode != 0 or not isinstance(payload, dict):
            with self._lock:
                self.stats.last_error = (stderr.strip() or "Worker de banda falhou")[
                    :120
                ]
            return None
        if not payload.get("ok") or not isinstance(payload.get("result"), dict):
            with self._lock:
                self.stats.last_error = str(payload.get("error") or "provider-failed")[
                    :120
                ]
            return None
        data = payload["result"]
        try:
            timestamp = datetime.datetime.fromisoformat(str(data["timestamp"]))
            return SpeedTestResult(
                download_mbps=float(data["download_mbps"]),
                upload_mbps=float(data["upload_mbps"]),
                ping_ms=float(data["ping_ms"]),
                servidor=str(data["servidor"]),
                timestamp=timestamp,
                provider_name=str(data["provider_name"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            with self._lock:
                self.stats.last_error = f"Resultado inválido: {exc}"[:120]
            return None

    def _run_single_test(self) -> Optional[SpeedTestResult]:
        """Executa um único teste de velocidade usando múltiplos provedores."""
        provider = self._next_provider()
        if provider is None:
            with self._lock:
                self.stats.last_error = "Nenhum provedor disponível"
            return None
        provider_id, provider_name = provider

        try:
            with self._lock:
                self.stats.is_testing = True
                self.stats.last_error = None
                self.stats.current_provider = provider_name

            provider_result = self._run_provider_process(provider_id)

            if provider_result:
                # Converter para o formato local (compatibilidade)
                result = SpeedTestResult(
                    download_mbps=provider_result.download_mbps,
                    upload_mbps=provider_result.upload_mbps,
                    ping_ms=provider_result.ping_ms,
                    servidor=provider_result.servidor,
                    timestamp=provider_result.timestamp,
                    provider_name=provider_result.provider_name,
                )

                with self._lock:
                    self.stats.add(result)
                return result
            else:
                with self._lock:
                    if not self.stats.last_error:
                        self.stats.last_error = "Todos os provedores falharam"
                return None

        except Exception as e:
            with self._lock:
                self.stats.last_error = str(e)[:50]
            return None
        finally:
            with self._lock:
                self.stats.is_testing = False

    def _loop(self):
        """Loop contínuo de testes em background - alterna entre provedores."""
        while self._running:
            if not self.prepare_single_test():
                self._stop_event.wait(0.05)
                continue
            # ``stop()`` may race with the reservation above.  Arming the
            # cancellation before consuming it prevents a late provider spawn.
            if not self._running:
                self.cancel_current_test()
            self.run_once(prepared=True)
            # Pausa menor para rotação mais rápida entre provedores
            # Cada teste demora ~10-30s, pausa de 5s entre testes
            if self._running:
                self._stop_event.wait(5)

    def prepare_single_test(self) -> bool:
        """Reserve one test before scheduling its worker.

        The reservation itself is cancellable, so a UI can enable its Cancel
        action immediately without waiting for the worker thread to start.
        """
        with self._lock:
            if self._test_prepared or self._test_executing or self.stats.is_testing:
                return False
            self._cancel_event.clear()
            self._test_prepared = True
            return True

    def run_once(self, *, prepared: bool = False) -> Optional[SpeedTestResult]:
        """Run one provider test, optionally consuming a prior reservation."""
        with self._lock:
            if prepared:
                if not self._test_prepared or self._test_executing:
                    return None
                self._test_prepared = False
                self._test_executing = True
            else:
                if self._test_prepared or self._test_executing or self.stats.is_testing:
                    return None
                self._cancel_event.clear()
                self._test_executing = True
        try:
            if self._cancel_event.is_set():
                with self._lock:
                    self.stats.last_error = "Teste cancelado"
                return None
            return self._run_single_test()
        finally:
            with self._lock:
                self._test_executing = False

    def cancel_current_test(self) -> bool:
        """Cancel a prepared or running test; workers notice within 100 ms."""
        with self._lock:
            active = (
                self._test_prepared or self._test_executing or self.stats.is_testing
            )
            if active:
                self._cancel_event.set()
        return active

    def start(self):
        """Inicia o loop de testes em background."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Para o loop de testes.

        Força o fechamento de qualquer driver Selenium em uso para que um teste
        em andamento (BrasilBandaLarga/SIMET, que rodam num Chrome headless) não
        deixe processos chrome/chromedriver órfãos ao encerrar.
        """
        self._running = False
        self._stop_event.set()
        self.cancel_current_test()
        try:
            if self._multi_provider is not None:
                self._multi_provider.cleanup_active()
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=2)
        with self._process_lock:
            process = self._active_process
        if process is not None and process.poll() is None:
            self._terminate_process_tree(process)

    def check_compliance(self) -> tuple[bool, bool]:
        """
        Verifica se velocidade está conforme contrato.

        Retorna:
            (download_ok, upload_ok): tupla de bools
        """
        with self._lock:
            if not self.stats.last_result:
                return (True, True)  # Sem dados = assumir OK

            result = self.stats.last_result
            min_down = self.config.velocidade_contratada_down * (
                self.config.percentual_minimo / 100
            )
            min_up = self.config.velocidade_contratada_up * (
                self.config.percentual_minimo / 100
            )

            return (result.download_mbps >= min_down, result.upload_mbps >= min_up)

    def get_percentage(self) -> tuple[float, float]:
        """
        Retorna porcentagem da velocidade contratada.

        Retorna:
            (download_pct, upload_pct): porcentagens
        """
        with self._lock:
            if not self.stats.last_result:
                return (0.0, 0.0)

            result = self.stats.last_result
            down_pct = (
                result.download_mbps / self.config.velocidade_contratada_down
            ) * 100
            up_pct = (result.upload_mbps / self.config.velocidade_contratada_up) * 100

            return (down_pct, up_pct)

    def get_stats_snapshot(self) -> dict:
        """
        Retorna um snapshot thread-safe dos dados atuais.

        Inclui resultados por provedor e progresso em tempo real.
        """
        with self._lock:
            result = self.stats.last_result

            # Do not instantiate providers merely to render an idle table.
            return {
                "last_result": result,
                "is_testing": self.stats.is_testing,
                "test_count": self.stats.test_count,
                "last_error": self.stats.last_error,
                "history_down": list(self.stats.history_down),
                "history_up": list(self.stats.history_up),
                "timestamps": list(self.stats.timestamps),
                "results_by_provider": dict(self.stats.results_by_provider),
                "provider_names": list(self.stats.provider_names),
                "current_provider": self.stats.current_provider,
                # Progresso em tempo real
                "progress_mbps": 0.0,
                "progress_phase": "isolated_worker"
                if self.stats.is_testing
                else "idle",
                "progress_provider": self.stats.current_provider,
            }


# Instância global para uso no stalker
speed_config = SpeedTestConfig()
speed_tester: Optional[ContinuousSpeedTester] = None
_speed_tester_lock = threading.Lock()


def get_speed_tester() -> ContinuousSpeedTester:
    """Retorna a instância global do testador de velocidade."""
    global speed_tester
    if speed_tester is None:
        with _speed_tester_lock:
            if speed_tester is None:
                speed_tester = ContinuousSpeedTester(speed_config)
    return speed_tester


def start_continuous_testing():
    """Inicia testes contínuos de velocidade."""
    tester = get_speed_tester()
    tester.start()


def stop_continuous_testing():
    """Para testes de velocidade."""
    global speed_tester
    if speed_tester:
        speed_tester.stop()
