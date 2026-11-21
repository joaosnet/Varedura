"""Validação e visualização de streams via ffmpeg (ffprobe/ffplay)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rtsp.log import obter_logger, redact_sensitive
from varedura.termux_env import is_android, open_file_or_url

_log = obter_logger("video")

ERRO_AUTH = "auth"
ERRO_BLOQUEIO = "bloqueio"
ERRO_CAMINHO = "caminho"
ERRO_REDE = "rede"
ERRO_FERRAMENTA = "ferramenta"
ERRO_OUTRO = "outro"


# --------------------------------------------------------------------------
# Detecção de player de vídeo (preferindo MPC-HC, depois ffplay, depois VLC)
# --------------------------------------------------------------------------

# Locais comuns de instalação no Windows/Android, além do PATH.
_LOCAIS_PLAYER: dict[str, list[str]] = {
    "mpc-hc": [
        r"C:\Program Files\MPC-HC\mpc-hc64.exe",
        r"C:\Program Files (x86)\MPC-HC\mpc-hc.exe",
        r"C:\Program Files\K-Lite Codec Pack\MPC-HC64\mpc-hc64.exe",
    ],
    "mpc-be": [
        r"C:\Program Files\MPC-BE\mpc-be64.exe",
        r"C:\Program Files\MPC-BE x64\mpc-be64.exe",
    ],
    "vlc": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "vlc-android": ["/system/bin/am"],
}

# Ordem de preferência no Android/Termux.
_PREFERENCIA_ANDROID: list[tuple[str, list[str]]] = [
    ("vlc-android", ["am"]),
    ("termux-open", ["termux-open"]),
    ("mpv-tct", ["mpv"]),
]

# Ordem de preferência desktop. (nome, lista de executáveis a procurar no PATH)
_PREFERENCIA: list[tuple[str, list[str]]] = [
    ("mpc-hc", ["mpc-hc64", "mpc-hc"]),
    ("mpc-be", ["mpc-be64", "mpc-be"]),
    ("ffplay", ["ffplay"]),
    ("vlc", ["vlc"]),
    ("mpv", ["mpv"]),
]


def _achar_exe(nome_familia: str, nomes_path: list[str]) -> str | None:
    """Procura o executável no PATH e nos locais comuns de instalação."""
    for n in nomes_path:
        achado = shutil.which(n)
        if achado:
            return achado
    for caminho in _LOCAIS_PLAYER.get(nome_familia, []):
        if Path(caminho).exists():
            return caminho
    return None


def detectar_player() -> tuple[str, str] | None:
    """Retorna (familia, caminho_exe) do primeiro player disponível, ou None."""
    ordem = _PREFERENCIA_ANDROID + _PREFERENCIA if is_android() else _PREFERENCIA
    for familia, nomes in ordem:
        exe = _achar_exe(familia, nomes)
        if exe:
            return (familia, exe)
    return None


def _montar_comando(
    familia: str, exe: str, url: str, titulo: str | None, largura: int, altura: int
) -> list[str]:
    """Monta a linha de comando específica para cada player."""
    if familia == "vlc-android":
        return [
            exe,
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            url,
            "-p",
            "org.videolan.vlc",
        ]
    if familia == "termux-open":
        return [exe, url]
    if familia == "mpv-tct":
        return [exe, "--vo=tct", "--rtsp-transport=tcp", "--profile=low-latency", url]
    if familia == "mpv":
        return [exe, "--rtsp-transport=tcp", "--profile=low-latency", url]
    if familia in ("mpc-hc", "mpc-be"):
        # /new força nova instância; /play começa a tocar automaticamente.
        return [exe, url, "/new", "/play"]
    if familia == "vlc":
        return [exe, url, "--no-video-title-show"]
    # ffplay
    return [
        exe,
        "-rtsp_transport", "tcp",
        "-x", str(largura),
        "-y", str(altura),
        "-window_title", titulo or url,
        url,
    ]


@dataclass
class InfoStream:
    """Resultado da validação de um stream de vídeo."""

    url: str
    funciona: bool
    codec: str | None = None
    largura: int | None = None
    altura: int | None = None
    mensagem: str = ""
    erro_tipo: str | None = None

    @property
    def resolucao(self) -> str:
        if self.largura and self.altura:
            return f"{self.largura}x{self.altura}"
        return "—"


def _ffprobe_disponivel() -> bool:
    return shutil.which("ffprobe") is not None


def _ffplay_disponivel() -> bool:
    return shutil.which("ffplay") is not None


_FFMPEG_VIDEO = re.compile(
    r"Stream #\d+:\d+[^\n]*?: Video: (?P<codec>[A-Za-z0-9_]+)[^\n]*?"
    r"\b(?P<w>\d{2,5})x(?P<h>\d{2,5})\b"
)

_RE_BLOQUEIO = (
    re.compile(r"\b429\s+too\s+many\b"),
    re.compile(r"(?:returned|failed:?)\s+429\b"),
    re.compile(r"\b503\s+service\s+unavailable\b"),
    re.compile(r"(?:returned|failed:?)\s+503\b"),
)
_TOKENS_BLOQUEIO = (
    "too many requests",
    "too many connections",
    "max connections",
    "account locked",
    "user locked",
    "ip locked",
    "locked out",
    "temporarily blocked",
    "try again later",
)
_RE_AUTH = (
    re.compile(r"\b401\s+unauthorized\b"),
    re.compile(r"(?:returned|failed:?)\s+401\b"),
    re.compile(r"\b403\s+forbidden\b"),
    re.compile(r"(?:returned|failed:?)\s+403\b"),
)
_TOKENS_AUTH = (
    "unauthorized",
    "authorization failed",
    "authentication failed",
    "forbidden",
)
_RE_CAMINHO = (
    re.compile(r"\b404\s+(?:stream\s+)?not\s+found\b"),
    re.compile(r"(?:returned|failed:?)\s+404\b"),
    re.compile(r"\b400\s+bad\s+request\b"),
    re.compile(r"(?:returned|failed:?)\s+400\b"),
    re.compile(r"\b454\s+session\s+not\s+found\b"),
    re.compile(r"(?:returned|failed:?)\s+454\b"),
)
_TOKENS_CAMINHO = (
    "stream not found",
    "not found",
)
_TOKENS_REDE = (
    "connection refused",
    "connection timed out",
    "timed out",
    "timeout",
    "no route to host",
    "network is unreachable",
    "host is down",
    "could not connect",
    "failed to resolve",
    "error number -10061",
    "error number -10060",
    "error number -138",
)
_TOKENS_REDE_FATAL = (
    "connection refused",
    "no route to host",
    "network is unreachable",
    "host is down",
    "could not connect",
    "failed to resolve",
    "error number -10061",
)
_TOKENS_RESUMO = (
    "server returned",
    "method describe failed",
    "401",
    "403",
    "404",
    "429",
    "503",
    "connection refused",
    "timed out",
    "no route",
)


def classificar_erro_rtsp(texto: str) -> str:
    """Classifica o motivo de falha do ffprobe/ffmpeg analisando todo o stderr."""
    baixo = (texto or "").lower()
    if any(r.search(baixo) for r in _RE_BLOQUEIO) or any(t in baixo for t in _TOKENS_BLOQUEIO):
        return ERRO_BLOQUEIO
    if any(r.search(baixo) for r in _RE_AUTH) or any(t in baixo for t in _TOKENS_AUTH):
        return ERRO_AUTH
    if any(r.search(baixo) for r in _RE_CAMINHO) or any(t in baixo for t in _TOKENS_CAMINHO):
        return ERRO_CAMINHO
    if any(t in baixo for t in _TOKENS_REDE):
        return ERRO_REDE
    return ERRO_OUTRO


def _eh_erro_rede_fatal(texto: str) -> bool:
    baixo = (texto or "").lower()
    return any(t in baixo for t in _TOKENS_REDE_FATAL)


def _resumir_erro_stderr(stderr: str, fallback: str) -> str:
    linhas = [linha.strip() for linha in (stderr or "").splitlines() if linha.strip()]
    if not linhas:
        return redact_sensitive(fallback)
    for linha in reversed(linhas):
        baixo = linha.lower()
        if any(tok in baixo for tok in _TOKENS_RESUMO):
            return redact_sensitive(linha)
    return redact_sensitive(linhas[-1])


def _validar_stream_ffmpeg(url: str, timeout: float) -> InfoStream:
    """Mesma checagem do ffprobe usando só o ffmpeg: lê 1 quadro do vídeo."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-rtsp_transport", "tcp",
        "-timeout", str(int(timeout * 1_000_000)),  # microssegundos
        "-i", url,
        "-map", "0:v:0",
        "-frames:v", "1",
        "-f", "null",
        "-",
    ]
    _log.debug("ffmpeg (sem ffprobe): %s", url)
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired:
        _log.warning("ffmpeg timeout: %s", url)
        return InfoStream(
            url, False, mensagem="Timeout ao ler o stream", erro_tipo=ERRO_REDE
        )
    except OSError as exc:
        _log.error("ffmpeg erro ao executar (%s): %s", url, exc)
        return InfoStream(
            url, False, mensagem=f"Erro ao executar ffmpeg: {exc}", erro_tipo=ERRO_FERRAMENTA
        )

    stderr = proc.stderr or ""
    achado = _FFMPEG_VIDEO.search(stderr)
    if proc.returncode != 0 or achado is None:
        erro_tipo = ERRO_OUTRO if proc.returncode == 0 else classificar_erro_rtsp(stderr)
        detalhe = _resumir_erro_stderr(stderr, "ffmpeg falhou")
        _log.info("ffmpeg falhou (%s) [%s]: %s", url, erro_tipo, detalhe)
        return InfoStream(url, False, mensagem=detalhe, erro_tipo=erro_tipo)

    largura, altura = int(achado.group("w")), int(achado.group("h"))
    _log.info("ffmpeg OK (%s): %s %sx%s", url, achado.group("codec"), largura, altura)
    return InfoStream(
        url=url,
        funciona=True,
        codec=achado.group("codec"),
        largura=largura,
        altura=altura,
        mensagem="OK",
    )


def validar_stream(url: str, timeout: float = 10.0) -> InfoStream:
    """Confirma que a URL entrega vídeo decodificável, lendo o stream de vídeo.

    Usa ffprobe: se houver um stream de vídeo com codec/resolução, a câmera
    está realmente funcionando (não só com a porta aberta).
    """
    if not _ffprobe_disponivel():
        # Instalações só com o ffmpeg (sem o ffprobe ao lado) são comuns: antes
        # isso reprovava toda credencial, e a câmera "nunca funcionava".
        if shutil.which("ffmpeg") is not None:
            return _validar_stream_ffmpeg(url, timeout)
        return InfoStream(
            url,
            False,
            mensagem="ffprobe/ffmpeg não encontrados no PATH",
            erro_tipo=ERRO_FERRAMENTA,
        )

    cmd = [
        "ffprobe",
        "-v", "error",
        "-rtsp_transport", "tcp",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height",
        "-of", "json",
        "-timeout", str(int(timeout * 1_000_000)),  # microssegundos
        url,
    ]
    _log.debug("ffprobe: %s", url)
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired:
        _log.warning("ffprobe timeout: %s", url)
        return InfoStream(
            url, False, mensagem="Timeout ao ler o stream", erro_tipo=ERRO_REDE
        )
    except OSError as exc:
        _log.error("ffprobe erro ao executar (%s): %s", url, exc)
        return InfoStream(
            url, False, mensagem=f"Erro ao executar ffprobe: {exc}", erro_tipo=ERRO_FERRAMENTA
        )

    if proc.returncode != 0:
        stderr = proc.stderr or ""
        erro_tipo = classificar_erro_rtsp(stderr)
        detalhe = _resumir_erro_stderr(stderr, "ffprobe falhou")
        _log.info("ffprobe falhou (%s) [%s]: %s", url, erro_tipo, detalhe)
        return InfoStream(url, False, mensagem=detalhe, erro_tipo=erro_tipo)

    try:
        dados = json.loads(proc.stdout or "{}")
        streams = dados.get("streams", [])
    except json.JSONDecodeError:
        streams = []

    if not streams:
        return InfoStream(
            url,
            False,
            mensagem="Nenhum stream de vídeo encontrado",
            erro_tipo=ERRO_OUTRO,
        )

    s = streams[0]
    _log.info(
        "ffprobe OK (%s): %s %sx%s",
        url, s.get("codec_name"), s.get("width"), s.get("height"),
    )
    return InfoStream(
        url=url,
        funciona=True,
        codec=s.get("codec_name"),
        largura=s.get("width"),
        altura=s.get("height"),
        mensagem="OK",
    )


def descobrir_stream(
    monta_url: Callable[[str], str],
    candidatos: list[str],
    timeout: float = 6.0,
    ao_tentar: Callable[[str], None] | None = None,
    *,
    max_timeouts: int = 2,
    diagnostico: dict[str, Any] | None = None,
) -> InfoStream | None:
    """Testa vários caminhos e retorna o primeiro que entrega vídeo.

    monta_url(caminho) -> URL completa (com host/porta/credenciais).
    ao_tentar(caminho) é chamado antes de cada teste (para feedback de progresso).
    Interrompe imediatamente ao receber erro de autenticação/bloqueio/ferramenta
    ou falha de rede definitiva, evitando tempestades de login na câmera.
    Retorna o InfoStream do caminho que funcionou, ou None se nenhum funcionar.
    """
    tentativas = 0
    timeouts_seguidos = 0
    viu_erro_caminho = False
    ultimo_erro: InfoStream | None = None
    caminho_auth: str | None = None

    for caminho in candidatos:
        if ao_tentar:
            ao_tentar(caminho)
        info = validar_stream(monta_url(caminho), timeout=timeout)
        tentativas += 1
        if info.funciona:
            if diagnostico is not None:
                diagnostico.update(
                    {
                        "tentativas": tentativas,
                        "ultimo_erro": None,
                        "erro_tipo": None,
                        "mensagem": "",
                        "caminho_auth": None,
                    }
                )
            return info

        ultimo_erro = info
        if info.erro_tipo == ERRO_AUTH:
            if viu_erro_caminho:
                caminho_auth = caminho
            break
        if info.erro_tipo in (ERRO_BLOQUEIO, ERRO_FERRAMENTA):
            break
        if info.erro_tipo == ERRO_REDE:
            if _eh_erro_rede_fatal(info.mensagem):
                break
            timeouts_seguidos += 1
            if timeouts_seguidos >= max_timeouts:
                break
        elif info.erro_tipo == ERRO_CAMINHO:
            viu_erro_caminho = True
            timeouts_seguidos = 0
        else:
            timeouts_seguidos = 0

    if diagnostico is not None:
        diagnostico["tentativas"] = tentativas
        diagnostico["ultimo_erro"] = ultimo_erro
        diagnostico["erro_tipo"] = ultimo_erro.erro_tipo if ultimo_erro else None
        diagnostico["mensagem"] = ultimo_erro.mensagem if ultimo_erro else ""
        diagnostico["caminho_auth"] = caminho_auth
    return None


def abrir_stream(
    url: str,
    titulo: str | None = None,
    largura: int = 960,
    altura: int = 540,
) -> subprocess.Popen | None:
    """Abre o stream ao vivo no melhor player disponível. Não bloqueia.

    Prefere MPC-HC/MPC-BE (mais compatível no Windows), depois ffplay, depois VLC.
    Abre numa janela normal (não em tela cheia).

    Retorna o processo (pra fechar depois) ou None se nenhum player for achado.
    """
    player = detectar_player()
    if player is None:
        _log.error("Nenhum player encontrado (MPC-HC, ffplay ou VLC)")
        return None
    familia, exe = player
    cmd = _montar_comando(familia, exe, url, titulo, largura, altura)
    _log.info("Abrindo no %s (%s): %s", familia, exe, url)
    # Players GUI (MPC/VLC) são desacoplados do terminal do Textual;
    # ffplay e launchers Android capturam stderr para diagnóstico.
    capture_err = familia in ("ffplay", "vlc-android", "termux-open")
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture_err else subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def erro_se_morreu(proc: subprocess.Popen, espera: float = 2.5) -> str | None:
    """Se o player morreu logo após abrir, retorna a última linha de erro.

    Retorna None se o player continua vivo (abriu com sucesso), se saiu com
    código 0 (launchers de Intent como am start / termux-open), ou se não há
    stderr capturado com falha.
    """
    try:
        proc.wait(timeout=espera)
    except subprocess.TimeoutExpired:
        return None  # ainda rodando = abriu
    if proc.returncode == 0:
        return None
    saida = (proc.stderr.read() if proc.stderr else "") or ""
    linhas = [ln for ln in saida.splitlines() if ln.strip()]
    erro = linhas[-1] if linhas else "player fechou imediatamente"
    _log.warning("player morreu: %s", erro)
    return erro


def comando_mpv_terminal(url: str) -> list[str] | None:
    """Retorna comando para reproduzir o stream no terminal via mpv --vo=tct."""
    exe = shutil.which("mpv")
    if not exe:
        return None
    return [exe, "--vo=tct", "--rtsp-transport=tcp", "--profile=low-latency", url]


def capturar_e_abrir_snapshot(
    url: str, destino: str, timeout: float = 10.0
) -> tuple[bool, str]:
    """Captura um frame JPEG/PNG via ffmpeg e tenta abrir no visualizador do sistema."""
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        return False, "ffmpeg não encontrado no PATH"
    if not salvar_snapshot(url, destino, timeout=timeout):
        return False, "Falha ao capturar snapshot do stream"
    open_file_or_url(destino)
    return True, destino


def salvar_snapshot(url: str, destino: str, timeout: float = 10.0) -> bool:
    """Captura um único frame do stream e salva como imagem (precisa de ffmpeg)."""
    if shutil.which("ffmpeg") is None:
        return False
    cmd = [
        "ffmpeg",
        "-y",
        "-rtsp_transport", "tcp",
        "-i", url,
        "-frames:v", "1",
        destino,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=timeout + 5
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
