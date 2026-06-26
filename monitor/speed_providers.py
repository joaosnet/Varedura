"""
V's Speed Test Providers - Múltiplos provedores de teste de velocidade

Provedores implementados:
    - SpeedtestNetProvider: Ookla Speedtest.net (speedtest-cli)
    - FastComProvider: Netflix Fast.com
"""

import atexit
import datetime
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import threading


@dataclass
class ProgressState:
    """Estado de progresso em tempo real do teste de velocidade."""

    provider_name: str = ""
    phase: str = ""  # "download", "upload", "ping", "idle"
    current_mbps: float = 0.0
    elapsed_seconds: float = 0.0
    bytes_transferred: int = 0


@dataclass
class SpeedTestResult:
    """Resultado de um teste de velocidade."""

    download_mbps: float
    upload_mbps: float
    ping_ms: float
    servidor: str
    timestamp: datetime.datetime
    provider_name: str  # Identifica qual provedor fez o teste


def _chrome_service():
    """Cria um Service do chromedriver que NÃO abre janela de console no Windows.

    Sem isto, o Selenium inicia o chromedriver.exe com um console preto visível
    (a "cabeça" que aparece mesmo com o Chrome em --headless). O CREATE_NO_WINDOW
    é repassado ao subprocess.Popen do chromedriver pelo próprio Selenium.
    """
    from selenium.webdriver.chrome.service import Service

    service = Service()
    service.creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return service


def _safe_quit(driver) -> None:
    """Fecha um driver Selenium sem nunca propagar erro.

    Tenta `driver.quit()` (encerra o Chrome e o chromedriver). Se falhar,
    mata diretamente o processo do chromedriver para não deixá-lo órfão.
    """
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        try:
            proc = getattr(getattr(driver, "service", None), "process", None)
            if proc is not None:
                proc.kill()
        except Exception:
            pass


class SpeedTestProvider(ABC):
    """Classe base abstrata para provedores de teste de velocidade."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do provedor."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provedor está disponível (dependências instaladas)."""
        pass

    @abstractmethod
    def run_test(self) -> Optional[SpeedTestResult]:
        """Executa o teste de velocidade. Retorna None em caso de erro."""
        pass

    def cleanup(self) -> None:
        """Libera recursos do provedor (ex.: fechar driver Selenium).

        No-op por padrão; provedores Selenium sobrescrevem para fechar o driver.
        """
        return


class SpeedtestNetProvider(SpeedTestProvider):
    """Provedor Ookla Speedtest.net usando speedtest-cli."""

    def __init__(self):
        self._speedtest = None
        self._available = False
        self._error: Optional[str] = None

        try:
            import speedtest

            self._speedtest = speedtest
            self._available = True
        except ImportError:
            self._error = "speedtest-cli não instalado (uv add speedtest-cli)"

    @property
    def name(self) -> str:
        return "Speedtest.net"

    def is_available(self) -> bool:
        return self._available

    def run_test(self) -> Optional[SpeedTestResult]:
        if not self._available or self._speedtest is None:
            return None

        try:
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

            return SpeedTestResult(
                download_mbps=download_mbps,
                upload_mbps=upload_mbps,
                ping_ms=ping_ms,
                servidor=servidor,
                timestamp=datetime.datetime.now(),
                provider_name=self.name,
            )
        except Exception as e:
            self._error = str(e)[:50]
            return None


class FastComProvider(SpeedTestProvider):
    """Provedor Netflix Fast.com usando requests."""

    def __init__(self, progress: Optional[ProgressState] = None):
        self._available = False
        self._error: Optional[str] = None
        self._progress = progress  # Referência para atualizar progresso em tempo real

        try:
            import requests

            self._requests = requests
            self._available = True
        except ImportError:
            self._error = "requests não instalado (uv add requests)"

    @property
    def name(self) -> str:
        return "Fast.com"

    def is_available(self) -> bool:
        return self._available

    def run_test(self) -> Optional[SpeedTestResult]:
        """
        Executa teste usando a API do Fast.com (Netflix).

        A API do Fast.com requer:
        1. Obter token da página
        2. Baixar chunks de teste dos servidores Netflix
        3. Medir velocidade baseada no tempo de download
        """
        if not self._available:
            return None

        try:
            import time
            import re

            # Pegar token da página do Fast.com
            response = self._requests.get("https://fast.com", timeout=10)
            if response.status_code != 200:
                return None

            # Extrair script URL para pegar o token
            script_match = re.search(r'<script src="(/app-[^"]+\.js)"', response.text)
            if not script_match:
                return None

            script_url = "https://fast.com" + script_match.group(1)
            script_response = self._requests.get(script_url, timeout=10)

            # Extrair token do script
            token_match = re.search(r'token:"([^"]+)"', script_response.text)
            if not token_match:
                return None

            token = token_match.group(1)

            # Obter URLs de teste
            api_url = f"https://api.fast.com/netflix/speedtest/v2?https=true&token={token}&urlCount=3"
            api_response = self._requests.get(api_url, timeout=10)
            data = api_response.json()

            if "targets" not in data or not data["targets"]:
                return None

            # Testar download com múltiplos targets
            total_bytes = 0
            start_time = time.time()

            for target in data["targets"][:3]:  # Usar até 3 servidores
                url = target["url"]
                try:
                    chunk_response = self._requests.get(
                        url,
                        timeout=15,
                        stream=True,
                        headers={"Range": "bytes=0-26214400"},  # ~25MB
                    )
                    for chunk in chunk_response.iter_content(chunk_size=131072):
                        total_bytes += len(chunk)
                        elapsed = time.time() - start_time

                        # Atualizar progresso em tempo real
                        if elapsed > 0.1 and self._progress:
                            current_mbps = (total_bytes * 8 / 1_000_000) / elapsed
                            self._progress.current_mbps = current_mbps
                            self._progress.bytes_transferred = total_bytes
                            self._progress.elapsed_seconds = elapsed
                            self._progress.phase = "download"

                        # Limitar a ~5 segundos por servidor
                        if elapsed > 5:
                            break
                except Exception:
                    continue

            elapsed = time.time() - start_time
            if elapsed < 0.1:
                return None

            # Calcular velocidade final
            download_mbps = (total_bytes * 8 / 1_000_000) / elapsed

            # Atualizar progresso para upload (estimado)
            if self._progress:
                self._progress.phase = "upload"

            # Fast.com não testa upload facilmente, estimar baseado em download
            upload_mbps = download_mbps * 0.4

            # Ping
            ping_start = time.time()
            try:
                self._requests.head(data["targets"][0]["url"], timeout=5)
                ping_ms = (time.time() - ping_start) * 1000
            except Exception:
                ping_ms = 0

            servidor = data.get("client", {}).get("isp", "Netflix CDN")

            # Limpar progresso
            if self._progress:
                self._progress.phase = "idle"

            return SpeedTestResult(
                download_mbps=download_mbps,
                upload_mbps=upload_mbps,
                ping_ms=ping_ms,
                servidor=servidor,
                timestamp=datetime.datetime.now(),
                provider_name=self.name,
            )

        except Exception as e:
            self._error = str(e)[:50]
            return None


class BrasilBandaLargaProvider(SpeedTestProvider):
    """Provedor Brasil Banda Larga (ESAQ/Anatel) usando Selenium."""

    def __init__(self, progress: Optional[ProgressState] = None):
        self._available = False
        self._error: Optional[str] = None
        self._progress = progress
        self._driver = None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            self._webdriver = webdriver
            self._Options = Options
            self._available = True
        except ImportError:
            self._error = "selenium não instalado (uv add selenium)"

    @property
    def name(self) -> str:
        return "BrasilBandaLarga"

    def is_available(self) -> bool:
        return self._available

    def cleanup(self) -> None:
        """Fecha o driver Selenium em aberto (chamado no encerramento/parada)."""
        drv, self._driver = self._driver, None
        _safe_quit(drv)

    def run_test(self) -> Optional[SpeedTestResult]:
        if not self._available:
            return None

        try:
            # Configurar Chrome headless
            options = self._Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            driver = self._webdriver.Chrome(service=_chrome_service(), options=options)
            self._driver = driver
            driver.set_page_load_timeout(60)

            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                # Navegar para o site
                driver.get("https://www.brasilbandalarga.com.br/bbl/")
                time.sleep(4)  # Aguardar carregamento completo

                # CORREÇÃO: Remover overlays que bloqueiam cliques
                # - Sticky footer de cookies (LGPD)
                # - Widget VLibras (acessibilidade)
                driver.execute_script("""
                    // Remover/ocultar cookie consent footer
                    const cookieBanners = document.querySelectorAll(
                        '[class*="cookie"], [class*="lgpd"], [id*="cookie"], [id*="lgpd"], ' +
                        '.footer-fixed, .sticky-footer, [class*="consent"]'
                    );
                    cookieBanners.forEach(el => el.style.display = 'none');
                    
                    // Remover widget VLibras (barra de acessibilidade)
                    const vLibras = document.querySelectorAll(
                        '[class*="vlibras"], [id*="vlibras"], [class*="vw-"], .vw-plugin-wrapper'
                    );
                    vLibras.forEach(el => el.style.display = 'none');
                    
                    // Remover qualquer elemento com z-index muito alto que possa sobrepor
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const zIndex = parseInt(style.zIndex);
                        if (zIndex > 9999 && !el.id.includes('btn')) {
                            el.style.display = 'none';
                        }
                    });
                """)
                time.sleep(1)

                # Aguardar botão e scrollar para o centro
                start_btn = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "btnIniciar"))
                )

                # Scrollar o botão para o centro da viewport
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    start_btn,
                )
                time.sleep(0.5)

                # CORREÇÃO: Usar JavaScript click para evitar interceptação
                driver.execute_script("arguments[0].click();", start_btn)

                # Aguardar teste começar
                if self._progress:
                    self._progress.phase = "download"
                    self._progress.provider_name = self.name

                # Polling para verificar resultados
                max_wait = 90
                start_time = time.time()
                download_mbps = 0.0
                upload_mbps = 0.0
                ping_ms = 0.0

                while time.time() - start_time < max_wait:
                    try:
                        # Usar seletores corretos descobertos no debug
                        # Download: ícone FontAwesome + próximo elemento .textao
                        try:
                            download_el = driver.find_element(
                                By.XPATH,
                                "//i[contains(@class, 'fa-cloud-download')]/following-sibling::div[@class='textao'] | //i[contains(@class, 'fa-cloud-download')]/..//div[@class='textao']",
                            )
                            text = download_el.text.strip().replace(",", ".")
                            if text and text.replace(".", "").isdigit():
                                download_mbps = float(text)
                                if self._progress:
                                    self._progress.current_mbps = download_mbps
                        except Exception:
                            pass

                        # Upload
                        try:
                            upload_el = driver.find_element(
                                By.XPATH,
                                "//i[contains(@class, 'fa-cloud-upload')]/following-sibling::div[@class='textao'] | //i[contains(@class, 'fa-cloud-upload')]/..//div[@class='textao']",
                            )
                            text = upload_el.text.strip().replace(",", ".")
                            if text and text.replace(".", "").isdigit():
                                upload_mbps = float(text)
                                if self._progress and upload_mbps > 0:
                                    self._progress.phase = "upload"
                        except Exception:
                            pass

                        # Latência
                        try:
                            latency_el = driver.find_element(
                                By.XPATH,
                                "//div[text()='Latência']/following-sibling::div",
                            )
                            text = (
                                latency_el.text.strip()
                                .replace(" ms", "")
                                .replace(",", ".")
                            )
                            if text and text.replace(".", "").isdigit():
                                ping_ms = float(text)
                        except Exception:
                            pass

                        # Verificar se teste terminou
                        if download_mbps > 0 and upload_mbps > 0:
                            break
                    except Exception:
                        pass
                    time.sleep(2)

                if self._progress:
                    self._progress.phase = "idle"

                if download_mbps == 0:
                    return None

                return SpeedTestResult(
                    download_mbps=download_mbps,
                    upload_mbps=upload_mbps,
                    ping_ms=ping_ms,
                    servidor="ESAQ/Anatel",
                    timestamp=datetime.datetime.now(),
                    provider_name=self.name,
                )

            finally:
                _safe_quit(driver)
                self._driver = None

        except Exception as e:
            self._error = str(e)[:50]
            if self._progress:
                self._progress.phase = "idle"
            return None


class SimetProvider(SpeedTestProvider):
    """
    Provedor NIC.br SIMET usando Selenium.

    IMPORTANTE: O SIMET usa Flutter Web que renderiza em canvas.
    Para extrair dados, precisamos habilitar o modo de acessibilidade
    clicando no flt-semantics-placeholder, que expõe elementos via aria-label.
    """

    def __init__(self, progress: Optional[ProgressState] = None):
        self._available = False
        self._error: Optional[str] = None
        self._progress = progress
        self._webdriver = None
        self._Options = None
        self._driver = None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            self._webdriver = webdriver
            self._Options = Options
            self._available = True
        except ImportError:
            self._error = "selenium não instalado (uv add selenium)"

    @property
    def name(self) -> str:
        return "SIMET/NIC.br"

    def is_available(self) -> bool:
        return self._available

    def cleanup(self) -> None:
        """Fecha o driver Selenium em aberto (chamado no encerramento/parada)."""
        drv, self._driver = self._driver, None
        _safe_quit(drv)

    def run_test(self) -> Optional[SpeedTestResult]:
        """
        Executa teste no SIMET usando Flutter Web.
        Flutter renderiza em canvas, não no DOM tradicional.
        Precisamos habilitar acessibilidade e buscar no Shadow DOM.
        """
        if not self._available:
            return None

        try:
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains

            options = self._Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            # Habilitar acessibilidade via flag
            options.add_argument("--force-renderer-accessibility")

            driver = self._webdriver.Chrome(service=_chrome_service(), options=options)
            self._driver = driver
            driver.set_page_load_timeout(120)

            try:
                # Navegar para o app com auto-measure (inicia teste automaticamente)
                driver.get("https://simet.nic.br/app/?auto-measure=true")
                time.sleep(8)  # Flutter precisa mais tempo para carregar

                # CORREÇÃO: Forçar habilitação de acessibilidade do Flutter
                # Pressionar Tab para ativar modo de acessibilidade
                try:
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.TAB).perform()
                    time.sleep(1)
                except Exception:
                    pass

                # Tentar clicar no placeholder de semântica
                try:
                    driver.execute_script("""
                        // Forçar modo de acessibilidade do Flutter
                        const placeholder = document.querySelector('flt-semantics-placeholder');
                        if (placeholder) {
                            placeholder.click();
                            placeholder.focus();
                        }
                        // Também tentar via role
                        const semanticsHost = document.querySelector('[role="application"]');
                        if (semanticsHost) semanticsHost.click();
                    """)
                    time.sleep(2)
                except Exception:
                    pass

                if self._progress:
                    self._progress.phase = "download"
                    self._progress.provider_name = self.name

                # Polling para resultados - com múltiplas estratégias
                max_wait = 150  # SIMET pode demorar bastante
                start_time = time.time()
                download_mbps = 0.0
                upload_mbps = 0.0
                ping_ms = 0.0

                while time.time() - start_time < max_wait:
                    try:
                        # Estratégia 1: Buscar no Shadow DOM do flt-glass-pane
                        result = driver.execute_script("""
                            // Função para buscar recursivamente em shadow roots
                            function searchInShadow(root, results) {
                                if (!root) return;
                                
                                // Buscar em elementos com texto/aria-label
                                const elements = root.querySelectorAll ? 
                                    root.querySelectorAll('*') : [];
                                
                                for (const el of elements) {
                                    const text = (el.textContent || '') + ' ' + 
                                                 (el.getAttribute('aria-label') || '') + ' ' +
                                                 (el.getAttribute('aria-valuetext') || '');
                                    
                                    // Patterns mais flexíveis
                                    let match;
                                    
                                    // Download: procurar por padrões como "Download 123.45 Mbps" ou "123.45 Mbps Download"
                                    match = text.match(/Download[:\\s]*([\\d.,]+)\\s*M/i) ||
                                            text.match(/([\\d.,]+)\\s*Mbps?\\s*Download/i) ||
                                            text.match(/↓\\s*([\\d.,]+)/);
                                    if (match && !results.download) {
                                        results.download = match[1].replace(',', '.');
                                    }
                                    
                                    // Upload
                                    match = text.match(/Upload[:\\s]*([\\d.,]+)\\s*M/i) ||
                                            text.match(/([\\d.,]+)\\s*Mbps?\\s*Upload/i) ||
                                            text.match(/↑\\s*([\\d.,]+)/);
                                    if (match && !results.upload) {
                                        results.upload = match[1].replace(',', '.');
                                    }
                                    
                                    // Latência
                                    match = text.match(/Lat[êe]ncia[:\\s]*([\\d.,]+)\\s*ms/i) ||
                                            text.match(/Ping[:\\s]*([\\d.,]+)\\s*ms/i) ||
                                            text.match(/([\\d.,]+)\\s*ms/i);
                                    if (match && !results.latencia && parseFloat(match[1].replace(',', '.')) < 1000) {
                                        results.latencia = match[1].replace(',', '.');
                                    }
                                    
                                    // Buscar em shadow roots aninhados
                                    if (el.shadowRoot) {
                                        searchInShadow(el.shadowRoot, results);
                                    }
                                }
                            }
                            
                            const results = { download: null, upload: null, latencia: null };
                            
                            // Buscar em flt-glass-pane
                            const glassPane = document.querySelector('flt-glass-pane');
                            if (glassPane && glassPane.shadowRoot) {
                                searchInShadow(glassPane.shadowRoot, results);
                            }
                            
                            // Fallback: buscar no documento todo
                            if (!results.download) {
                                searchInShadow(document, results);
                            }
                            
                            return results;
                        """)

                        if result:
                            if result.get("download"):
                                try:
                                    download_mbps = float(result["download"])
                                    if self._progress:
                                        self._progress.current_mbps = download_mbps
                                except ValueError:
                                    pass
                            if result.get("upload"):
                                try:
                                    upload_mbps = float(result["upload"])
                                    if self._progress:
                                        self._progress.phase = "upload"
                                except ValueError:
                                    pass
                            if result.get("latencia"):
                                try:
                                    ping_ms = float(result["latencia"])
                                except ValueError:
                                    pass

                        if download_mbps > 0 and upload_mbps > 0:
                            break
                    except Exception as e:
                        self._error = str(e)[:50]
                    time.sleep(3)

                if self._progress:
                    self._progress.phase = "idle"

                if download_mbps == 0:
                    self._error = "Não foi possível extrair resultados do Flutter"
                    return None

                return SpeedTestResult(
                    download_mbps=download_mbps,
                    upload_mbps=upload_mbps,
                    ping_ms=ping_ms,
                    servidor="NIC.br",
                    timestamp=datetime.datetime.now(),
                    provider_name=self.name,
                )

            finally:
                _safe_quit(driver)
                self._driver = None

        except Exception as e:
            self._error = str(e)[:50]
            if self._progress:
                self._progress.phase = "idle"
            return None


class MultiProviderSpeedTester:
    """Gerenciador de múltiplos provedores de teste de velocidade."""

    def __init__(self):
        # Progresso em tempo real
        self.progress = ProgressState()

        # Lista de provedores (com referência ao progresso para updates em tempo real)
        self.providers: list[SpeedTestProvider] = [
            SpeedtestNetProvider(),
            FastComProvider(progress=self.progress),
            BrasilBandaLargaProvider(progress=self.progress),
            SimetProvider(progress=self.progress),
        ]
        self._current_index = 0
        self._lock = threading.Lock()
        self.current_testing_provider: str = ""  # Provedor sendo testado agora

    def get_available_providers(self) -> list[SpeedTestProvider]:
        """Retorna lista de provedores disponíveis."""
        return [p for p in self.providers if p.is_available()]

    def cleanup_active(self) -> None:
        """Fecha qualquer driver Selenium em aberto (parada/encerramento).

        Seguro chamar de outra thread: força o fim de um teste em andamento
        para não deixar processos chrome/chromedriver órfãos.
        """
        for provider in self.providers:
            try:
                provider.cleanup()
            except Exception:
                pass

    def get_next_provider(self) -> Optional[SpeedTestProvider]:
        """Retorna o próximo provedor disponível (rotação round-robin)."""
        available = self.get_available_providers()
        if not available:
            return None

        with self._lock:
            provider = available[self._current_index % len(available)]
            self._current_index += 1

        return provider

    def run_test_with_fallback(self) -> Optional[SpeedTestResult]:
        """
        Executa teste com o próximo provedor na rotação.
        Cada chamada testa apenas UM provedor - a rotação é mantida entre chamadas.
        Isso garante que todos os provedores sejam testados ao longo do tempo.
        """
        available = self.get_available_providers()
        if not available:
            self.current_testing_provider = ""
            return None

        # Tentar próximo provedor na rotação (SEM fallback imediato)
        # Isso garante que BrasilBandaLarga e SIMET sejam tentados na sua vez
        provider = self.get_next_provider()
        if provider:
            # Atualizar indicador de progresso
            self.current_testing_provider = provider.name
            self.progress.provider_name = provider.name
            result = provider.run_test()
            self.current_testing_provider = ""

            if result:
                return result
            else:
                # Se falhou, retorna None mas o índice já avançou
                # Na próxima chamada, o próximo provedor será tentado
                return None

        self.current_testing_provider = ""
        return None


# Instância global do gerenciador
_multi_provider: Optional[MultiProviderSpeedTester] = None


def get_multi_provider() -> MultiProviderSpeedTester:
    """Retorna a instância global do gerenciador de provedores."""
    global _multi_provider
    if _multi_provider is None:
        _multi_provider = MultiProviderSpeedTester()
        # Rede de segurança: fecha drivers Selenium ao encerrar o processo,
        # mesmo que stop() não seja chamado (evita chrome/chromedriver órfãos).
        atexit.register(_multi_provider.cleanup_active)
    return _multi_provider
