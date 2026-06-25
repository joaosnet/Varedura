"""Validação e visualização de streams via ffmpeg (ffprobe/ffplay)."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rtsp.log import obter_logger

_log = obter_logger("video")


# --------------------------------------------------------------------------
# Detecção de player de vídeo (preferindo MPC-HC, depois ffplay, depois VLC)
# --------------------------------------------------------------------------

# Locais comuns de instalação no Windows, além do PATH.
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
}

# Ordem de preferência. (nome, lista de executáveis a procurar no PATH)
_PREFERENCIA: list[tuple[str, list[str]]] = [
    ("mpc-hc", ["mpc-hc64", "mpc-hc"]),
    ("mpc-be", ["mpc-be64", "mpc-be"]),
    ("ffplay", ["ffplay"]),
    ("vlc", ["vlc"]),
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
    for familia, nomes in _PREFERENCIA:
        exe = _achar_exe(familia, nomes)
        if exe:
            return (familia, exe)
    return None


def _montar_comando(
    familia: str, exe: str, url: str, titulo: str | None, largura: int, altura: int
) -> list[str]:
    """Monta a linha de comando específica para cada player."""
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

    @property
    def resolucao(self) -> str:
        if self.largura and self.altura:
            return f"{self.largura}x{self.altura}"
        return "—"


def _ffprobe_disponivel() -> bool:
    return shutil.which("ffprobe") is not None


def _ffplay_disponivel() -> bool:
    return shutil.which("ffplay") is not None


def validar_stream(url: str, timeout: float = 10.0) -> InfoStream:
    """Confirma que a URL entrega vídeo decodificável, lendo o stream de vídeo.

    Usa ffprobe: se houver um stream de vídeo com codec/resolução, a câmera
    está realmente funcionando (não só com a porta aberta).
    """
    if not _ffprobe_disponivel():
        return InfoStream(url, False, mensagem="ffprobe não encontrado no PATH")

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
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired:
        _log.warning("ffprobe timeout: %s", url)
        return InfoStream(url, False, mensagem="Timeout ao ler o stream")
    except OSError as exc:
        _log.error("ffprobe erro ao executar (%s): %s", url, exc)
        return InfoStream(url, False, mensagem=f"Erro ao executar ffprobe: {exc}")

    if proc.returncode != 0:
        msg = proc.stderr.strip().splitlines()
        detalhe = msg[-1] if msg else "ffprobe falhou"
        _log.info("ffprobe falhou (%s): %s", url, detalhe)
        return InfoStream(url, False, mensagem=detalhe)

    try:
        dados = json.loads(proc.stdout or "{}")
        streams = dados.get("streams", [])
    except json.JSONDecodeError:
        streams = []

    if not streams:
        return InfoStream(url, False, mensagem="Nenhum stream de vídeo encontrado")

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
) -> InfoStream | None:
    """Testa vários caminhos e retorna o primeiro que entrega vídeo.

    monta_url(caminho) -> URL completa (com host/porta/credenciais).
    ao_tentar(caminho) é chamado antes de cada teste (para feedback de progresso).
    Retorna o InfoStream do caminho que funcionou, ou None se nenhum funcionar.
    """
    for caminho in candidatos:
        if ao_tentar:
            ao_tentar(caminho)
        info = validar_stream(monta_url(caminho), timeout=timeout)
        if info.funciona:
            return info
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
    # Players GUI (MPC/VLC) são desacoplados do terminal do Textual; só o
    # ffplay (SDL) precisa do stderr capturado para diagnóstico.
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE if familia == "ffplay" else subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def erro_se_morreu(proc: subprocess.Popen, espera: float = 2.5) -> str | None:
    """Se o player morreu logo após abrir, retorna a última linha de erro.

    Retorna None se o player continua vivo (abriu com sucesso) ou se não há
    stderr capturado (players GUI como MPC-HC/VLC).
    """
    try:
        proc.wait(timeout=espera)
    except subprocess.TimeoutExpired:
        return None  # ainda rodando = abriu
    saida = (proc.stderr.read() if proc.stderr else "") or ""
    linhas = [ln for ln in saida.splitlines() if ln.strip()]
    erro = linhas[-1] if linhas else "player fechou imediatamente"
    _log.warning("player morreu: %s", erro)
    return erro


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
