"""Funções para testar câmeras IP e streams RTSP usando apenas a stdlib."""

from __future__ import annotations

import base64
import ipaddress
import socket
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urlparse

from rtsp.log import obter_logger

_log = obter_logger("scanner")

# Portas comumente usadas por câmeras IP.
PORTAS_COMUNS_CAMERA = [554, 8554, 80, 8080, 88, 8000, 37777, 34567]

RTSP_PORTA_PADRAO = 554


@dataclass
class ResultadoRTSP:
    """Resultado de um teste de stream RTSP."""

    url: str
    acessivel: bool
    status_code: int | None = None
    mensagem: str = ""
    metodos: list[str] = field(default_factory=list)


def testar_porta(host: str, porta: int, timeout: float = 2.0) -> bool:
    """Retorna True se a porta TCP estiver aberta no host."""
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def escanear_portas_camera(
    host: str,
    portas: list[int] | None = None,
    timeout: float = 2.0,
) -> dict[int, bool]:
    """Testa as portas típicas de câmera IP num host e retorna {porta: aberta}."""
    portas = portas or PORTAS_COMUNS_CAMERA
    resultado: dict[int, bool] = {}
    with ThreadPoolExecutor(max_workers=min(len(portas), 16)) as pool:
        futuros = {
            pool.submit(testar_porta, host, p, timeout): p for p in portas
        }
        for fut, porta in futuros.items():
            resultado[porta] = fut.result()
    return dict(sorted(resultado.items()))


def _build_rtsp_request(
    metodo: str, url: str, cseq: int, usuario: str | None, senha: str | None
) -> bytes:
    """Monta uma requisição RTSP, com Basic Auth opcional."""
    linhas = [
        f"{metodo} {url} RTSP/1.0",
        f"CSeq: {cseq}",
        "User-Agent: varedura-rtsp/1.0",
    ]
    if usuario is not None:
        cred = base64.b64encode(f"{usuario}:{senha or ''}".encode()).decode()
        linhas.append(f"Authorization: Basic {cred}")
    return ("\r\n".join(linhas) + "\r\n\r\n").encode()


def testar_rtsp(
    url: str,
    usuario: str | None = None,
    senha: str | None = None,
    timeout: float = 5.0,
) -> ResultadoRTSP:
    """Faz handshake RTSP (OPTIONS) com a câmera e reporta o resultado.

    Exemplo de url: rtsp://192.168.1.10:554/stream1
    """
    parsed = urlparse(url)
    if parsed.scheme != "rtsp":
        return ResultadoRTSP(url, False, mensagem="URL não é rtsp://")

    host = parsed.hostname or ""
    porta = parsed.port or RTSP_PORTA_PADRAO
    # Embute credenciais da própria URL, se presentes.
    usuario = usuario or parsed.username
    senha = senha or parsed.password

    try:
        with socket.create_connection((host, porta), timeout=timeout) as sock:
            sock.settimeout(timeout)
            req = _build_rtsp_request("OPTIONS", url, 1, usuario, senha)
            sock.sendall(req)
            resposta = sock.recv(4096).decode(errors="replace")
    except (OSError, socket.timeout) as exc:
        return ResultadoRTSP(url, False, mensagem=f"Falha de conexão: {exc}")

    primeira_linha = resposta.splitlines()[0] if resposta else ""
    status_code = None
    partes = primeira_linha.split()
    if len(partes) >= 2 and partes[1].isdigit():
        status_code = int(partes[1])

    metodos: list[str] = []
    for linha in resposta.splitlines():
        if linha.lower().startswith("public:"):
            metodos = [m.strip() for m in linha.split(":", 1)[1].split(",")]

    acessivel = status_code == 200
    return ResultadoRTSP(
        url=url,
        acessivel=acessivel,
        status_code=status_code,
        mensagem=primeira_linha,
        metodos=metodos,
    )


def normalizar_faixa(faixa: str) -> str:
    """Valida uma faixa de rede e devolve a forma canônica.

    Aceita o prefixo legado "a.b.c" (/24 implícito) ou CIDR "a.b.c.d/nn".
    /24 é devolvido na forma curta "a.b.c"; outros tamanhos como CIDR.
    Levanta ValueError se inválida ou maior que /16.
    """
    txt = faixa.strip()
    if "/" not in txt:
        if txt.count(".") != 2:
            raise ValueError(
                f"'{faixa}' não é prefixo /24 (a.b.c) nem CIDR (a.b.c.d/nn)"
            )
        ipaddress.ip_network(f"{txt}.0/24")  # só valida
        return txt
    rede = ipaddress.ip_network(txt, strict=False)
    if rede.version != 4:
        raise ValueError("apenas faixas IPv4 são suportadas")
    if rede.prefixlen < 16:
        raise ValueError("faixa maior que /16 não é suportada (65k+ hosts)")
    if rede.prefixlen == 24:
        return str(rede.network_address).rsplit(".", 1)[0]
    return str(rede)


def hosts_da_faixa(faixa: str) -> list[str]:
    """Expande uma faixa (prefixo "a.b.c" ou CIDR) na lista de IPs a varrer."""
    txt = normalizar_faixa(faixa)
    if "/" not in txt:
        txt = f"{txt}.0/24"
    return [str(h) for h in ipaddress.ip_network(txt, strict=False).hosts()]


def escanear_rede(
    faixa: str,
    porta: int = RTSP_PORTA_PADRAO,
    timeout: float = 1.0,
    ao_progresso: Callable[[int, int, str | None], None] | None = None,
) -> list[str]:
    """Varre uma faixa de rede procurando hosts com a porta RTSP aberta.

    faixa: prefixo /24 ("192.168.1") ou CIDR ("10.0.0.0/22")
    ao_progresso(testados, total, ip_aberto_ou_None): chamado a cada host
        concluído. RODA NA THREAD do pool — quem usa para atualizar UI deve
        envolver em call_from_thread.
    Retorna lista de IPs com a porta aberta.
    """
    hosts = hosts_da_faixa(faixa)
    _log.info("Varrendo %s (%d hosts) na porta %d", faixa, len(hosts), porta)
    total = len(hosts)
    encontrados: list[str] = []
    testados = 0
    with ThreadPoolExecutor(max_workers=64) as pool:
        futuros = {
            pool.submit(testar_porta, h, porta, timeout): h for h in hosts
        }
        for fut in as_completed(futuros):
            host = futuros[fut]
            aberto = fut.result()
            if aberto:
                encontrados.append(host)
            testados += 1
            if ao_progresso is not None:
                try:
                    ao_progresso(testados, total, host if aberto else None)
                except Exception:  # callback de UI nunca aborta o scan
                    _log.exception("Erro no callback de progresso")
    _log.info("Varredura concluída: %d host(s) com %d aberto", len(encontrados), porta)
    return sorted(encontrados, key=ipaddress.IPv4Address)
