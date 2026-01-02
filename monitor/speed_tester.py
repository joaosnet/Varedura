"""
V's Speed Tester - Monitor de Velocidade de Internet em Tempo Real

Funcionalidades:
    - Teste contínuo de velocidade de download/upload em background
    - Comparação com velocidade contratada (regulamentação ANATEL - mínimo 80%)
    - Thread separada para não bloquear a interface
"""

import threading
import datetime
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


@dataclass
class SpeedTestConfig:
    """Configuração de velocidade contratada."""

    velocidade_contratada_down: float = 500.0  # Mbps
    velocidade_contratada_up: float = 100.0  # Mbps
    percentual_minimo: float = 80.0  # ANATEL exige mínimo de 80%


@dataclass
class SpeedStats:
    """Estatísticas de histórico de velocidade."""

    history_down: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    history_up: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    timestamps: Deque[datetime.datetime] = field(
        default_factory=lambda: deque(maxlen=50)
    )
    last_result: Optional[SpeedTestResult] = None
    is_testing: bool = False
    test_count: int = 0
    last_error: Optional[str] = None

    def add(self, result: SpeedTestResult):
        self.history_down.append(result.download_mbps)
        self.history_up.append(result.upload_mbps)
        self.timestamps.append(result.timestamp)
        self.last_result = result
        self.test_count += 1


class ContinuousSpeedTester:
    """
    Testador de velocidade contínuo que roda em background.

    Executa testes de velocidade em loop numa thread separada,
    sem bloquear a interface principal.
    """

    def __init__(self, config: SpeedTestConfig):
        self.config = config
        self.stats = SpeedStats()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._speedtest_available = True
        self._lock = threading.Lock()  # Lock para thread-safety

        # Verificar se speedtest está disponível
        try:
            import speedtest

            self._speedtest = speedtest
        except ImportError:
            self._speedtest_available = False
            self.stats.last_error = "speedtest-cli não instalado (uv add speedtest-cli)"

    def _run_single_test(self) -> Optional[SpeedTestResult]:
        """Executa um único teste de velocidade."""
        if not self._speedtest_available:
            return None

        try:
            with self._lock:
                self.stats.is_testing = True
                self.stats.last_error = None

            st = self._speedtest.Speedtest()
            st.get_best_server()

            # Download
            download_bps = st.download()
            download_mbps = download_bps / 1_000_000

            # Upload
            upload_bps = st.upload()
            upload_mbps = upload_bps / 1_000_000

            # Ping
            ping_ms = st.results.ping

            # Servidor
            servidor = st.results.server.get("sponsor", "Desconhecido")

            result = SpeedTestResult(
                download_mbps=download_mbps,
                upload_mbps=upload_mbps,
                ping_ms=ping_ms,
                servidor=servidor,
                timestamp=datetime.datetime.now(),
            )

            with self._lock:
                self.stats.add(result)
            return result

        except Exception as e:
            with self._lock:
                self.stats.last_error = str(e)[:50]
            return None
        finally:
            with self._lock:
                self.stats.is_testing = False

    def _loop(self):
        """Loop contínuo de testes em background."""
        while self._running:
            self._run_single_test()
            # Pausa maior entre testes - cada teste demora ~20-40s
            # então 30s de pausa dá tempo suficiente pra interface respirar
            if self._running:
                import time

                time.sleep(30)

    def start(self):
        """Inicia o loop de testes em background."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Para o loop de testes."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

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

        Use isso pra acessar os dados sem race conditions.
        """
        with self._lock:
            result = self.stats.last_result
            return {
                "last_result": result,
                "is_testing": self.stats.is_testing,
                "test_count": self.stats.test_count,
                "last_error": self.stats.last_error,
                "history_down": list(self.stats.history_down),
                "history_up": list(self.stats.history_up),
                "timestamps": list(self.stats.timestamps),
            }


# Instância global para uso no stalker
speed_config = SpeedTestConfig()
speed_tester: Optional[ContinuousSpeedTester] = None


def get_speed_tester() -> ContinuousSpeedTester:
    """Retorna a instância global do testador de velocidade."""
    global speed_tester
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
