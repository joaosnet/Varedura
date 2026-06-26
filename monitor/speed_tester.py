"""
V's Speed Tester - Monitor de Velocidade de Internet em Tempo Real

Funcionalidades:
    - Teste contínuo de velocidade de download/upload em background
    - Múltiplos provedores (Speedtest.net, Fast.com) com rotação automática
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
    provider_name: str = "Desconhecido"  # Identifica qual provedor fez o teste


@dataclass
class SpeedTestConfig:
    """Configuração de velocidade contratada."""

    velocidade_contratada_down: float = 500.0  # Mbps
    velocidade_contratada_up: float = 100.0  # Mbps
    percentual_minimo: float = 80.0  # ANATEL exige mínimo de 80%


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

        # Usar sistema de múltiplos provedores
        from monitor.speed_providers import get_multi_provider

        self._multi_provider = get_multi_provider()

        # Verificar disponibilidade
        available = self._multi_provider.get_available_providers()
        if not available:
            self.stats.last_error = (
                "Nenhum provedor disponível (instale speedtest-cli ou requests)"
            )

    def _run_single_test(self) -> Optional[SpeedTestResult]:
        """Executa um único teste de velocidade usando múltiplos provedores."""
        available = self._multi_provider.get_available_providers()
        if not available:
            return None

        try:
            with self._lock:
                self.stats.is_testing = True
                self.stats.last_error = None
                # Pegar o nome do próximo provedor que será testado
                next_provider = self._multi_provider.get_next_provider()
                if next_provider:
                    self.stats.current_provider = next_provider.name
                    # Voltar o índice pois get_next_provider incrementa
                    self._multi_provider._current_index -= 1

            # Usar sistema de rotação com fallback (atualiza current_testing_provider internamente)
            provider_result = self._multi_provider.run_test_with_fallback()

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
            self._run_single_test()
            # Pausa menor para rotação mais rápida entre provedores
            # Cada teste demora ~10-30s, pausa de 5s entre testes
            if self._running:
                import time

                time.sleep(5)

    def start(self):
        """Inicia o loop de testes em background."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Para o loop de testes.

        Força o fechamento de qualquer driver Selenium em uso para que um teste
        em andamento (BrasilBandaLarga/SIMET, que rodam num Chrome headless) não
        deixe processos chrome/chromedriver órfãos ao encerrar.
        """
        self._running = False
        try:
            self._multi_provider.cleanup_active()
        except Exception:
            pass
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

        Inclui resultados por provedor e progresso em tempo real.
        """
        with self._lock:
            result = self.stats.last_result

            # Pegar progresso em tempo real do multi_provider
            progress = self._multi_provider.progress

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
                "progress_mbps": progress.current_mbps,
                "progress_phase": progress.phase,
                "progress_provider": progress.provider_name,
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
