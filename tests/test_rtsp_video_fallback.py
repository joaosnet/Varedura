"""Validação de stream quando só o ffmpeg está instalado (sem ffprobe)."""

from __future__ import annotations

import types

import pytest

from rtsp import video

STDERR_OK = (
    "Input #0, rtsp, from 'rtsp://cam/stream1':\n"
    "  Stream #0:0: Video: h264 (High), yuvj420p(pc, bt709, progressive), "
    "1920x1080, 15 fps, 15 tbr, 90k tbn\n"
    "  Stream #0:1: Audio: pcm_alaw, 8000 Hz, mono, s16, 64 kb/s\n"
    "frame=    1 fps=0.0 q=-0.0 Lsize=N/A time=00:00:00.06 bitrate=N/A speed=0.4x\n"
)


def _only_ffmpeg(monkeypatch, returncode, stderr):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)

    monkeypatch.setattr(
        video.shutil, "which", lambda name: "/bin/ffmpeg" if name == "ffmpeg" else None
    )
    monkeypatch.setattr(video.subprocess, "run", fake_run)
    return calls


def test_validar_stream_usa_ffmpeg_quando_nao_ha_ffprobe(monkeypatch):
    calls = _only_ffmpeg(monkeypatch, 0, STDERR_OK)
    info = video.validar_stream("rtsp://cam/stream1", timeout=5)
    assert info.funciona and (info.codec, info.resolucao) == ("h264", "1920x1080")
    assert calls[0][0] == "ffmpeg" and "-frames:v" in calls[0]
    assert calls[0][calls[0].index("-rtsp_transport") + 1] == "tcp"


def test_validar_stream_ffmpeg_reporta_falha_de_autenticacao(monkeypatch):
    _only_ffmpeg(
        monkeypatch,
        1,
        "[rtsp @ 0x1] method DESCRIBE failed: 401 Unauthorized\n"
        "rtsp://cam/stream1: Server returned 401 Unauthorized (authorization failed)\n",
    )
    info = video.validar_stream("rtsp://cam/stream1", timeout=5)
    assert not info.funciona and "401" in info.mensagem


def test_validar_stream_sem_ffprobe_nem_ffmpeg(monkeypatch):
    monkeypatch.setattr(video.shutil, "which", lambda name: None)
    info = video.validar_stream("rtsp://cam/stream1")
    assert not info.funciona and "ffmpeg" in info.mensagem
    assert info.erro_tipo == video.ERRO_FERRAMENTA


def test_classificar_erro_rtsp_cobre_tipos_principais():
    assert video.classificar_erro_rtsp("Server returned 401 Unauthorized") == video.ERRO_AUTH
    assert video.classificar_erro_rtsp("HTTP error 403 Forbidden") == video.ERRO_AUTH
    assert video.classificar_erro_rtsp("method DESCRIBE failed: 404 Not Found") == video.ERRO_CAMINHO
    assert video.classificar_erro_rtsp("429 Too Many Requests") == video.ERRO_BLOQUEIO
    assert video.classificar_erro_rtsp("503 Service Unavailable") == video.ERRO_BLOQUEIO
    assert video.classificar_erro_rtsp("Connection refused") == video.ERRO_REDE
    assert video.classificar_erro_rtsp("Connection timed out") == video.ERRO_REDE


def test_validar_stream_ffmpeg_multiline_401_redige_segredo(monkeypatch):
    stderr_ffmpeg8 = (
        "[rtsp @ 0x1] method DESCRIBE failed: 401 Unauthorized\n"
        "[in#0 @ 0x2] Error opening input: Server returned 401 Unauthorized (authorization failed)\n"
        "Error opening input file rtsp://admin:SuperSecret123@192.168.18.82:554/stream1.\n"
        "Error opening input files: Server returned 401 Unauthorized (authorization failed)\n"
    )
    _only_ffmpeg(monkeypatch, 1, stderr_ffmpeg8)
    info = video.validar_stream(
        "rtsp://admin:SuperSecret123@192.168.18.82:554/stream1", timeout=5
    )
    assert not info.funciona
    assert info.erro_tipo == video.ERRO_AUTH
    assert "SuperSecret123" not in info.mensagem
    assert "401" in info.mensagem


def test_descobrir_stream_para_no_primeiro_401(monkeypatch):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        return video.InfoStream(
            url,
            False,
            mensagem="401 Unauthorized",
            erro_tipo=video.ERRO_AUTH,
        )

    monkeypatch.setattr(video, "validar_stream", fake_validar)
    diag: dict = {}
    res = video.descobrir_stream(
        lambda c: f"rtsp://admin:errada@192.168.1.10:554{c}",
        [f"/c{i}" for i in range(40)],
        diagnostico=diag,
    )
    assert res is None
    assert len(chamadas) == 1
    assert diag["erro_tipo"] == video.ERRO_AUTH
    assert diag["tentativas"] == 1
    assert diag["caminho_auth"] is None


def test_descobrir_stream_continua_apos_404_e_para_no_401_anotando_caminho(monkeypatch):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        if url.endswith("/stream1"):
            return video.InfoStream(
                url, False, mensagem="401 Unauthorized", erro_tipo=video.ERRO_AUTH
            )
        return video.InfoStream(
            url, False, mensagem="404 Not Found", erro_tipo=video.ERRO_CAMINHO
        )

    monkeypatch.setattr(video, "validar_stream", fake_validar)
    diag: dict = {}
    res = video.descobrir_stream(
        lambda c: f"rtsp://admin:errada@192.168.1.10:554{c}",
        ["/", "/live", "/stream1", "/stream2", "/onvif1"],
        diagnostico=diag,
    )
    assert res is None
    assert len(chamadas) == 3
    assert diag["erro_tipo"] == video.ERRO_AUTH
    assert diag["caminho_auth"] == "/stream1"


@pytest.mark.parametrize(
    ("erro_tipo", "mensagem"),
    [
        (video.ERRO_BLOQUEIO, "429 Too Many Requests"),
        (video.ERRO_FERRAMENTA, "ffprobe/ffmpeg não encontrados no PATH"),
        (video.ERRO_REDE, "Connection refused"),
    ],
)
def test_descobrir_stream_para_imediatamente_em_bloqueio_ferramenta_ou_rede_fatal(
    monkeypatch, erro_tipo, mensagem
):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        return video.InfoStream(url, False, mensagem=mensagem, erro_tipo=erro_tipo)

    monkeypatch.setattr(video, "validar_stream", fake_validar)
    res = video.descobrir_stream(
        lambda c: f"rtsp://192.168.1.10:554{c}",
        ["/", "/live", "/stream1", "/stream2"],
    )
    assert res is None
    assert len(chamadas) == 1


def test_descobrir_stream_tolera_um_timeout_e_para_no_limite(monkeypatch):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        return video.InfoStream(
            url, False, mensagem="Timeout ao ler o stream", erro_tipo=video.ERRO_REDE
        )

    monkeypatch.setattr(video, "validar_stream", fake_validar)
    res = video.descobrir_stream(
        lambda c: f"rtsp://192.168.1.10:554{c}",
        ["/", "/live", "/stream1", "/stream2"],
        max_timeouts=2,
    )
    assert res is None
    assert len(chamadas) == 2
