"""Caminhos RTSP conhecidos pela comunidade, por fabricante.

Baseado em listas públicas (iSpyConnect, ffmpeg, fóruns). Usados para
descobrir automaticamente o stream de uma câmera quando o caminho é desconhecido.
Os mais prováveis vêm primeiro para acelerar a descoberta.
"""

from __future__ import annotations

# (fabricante, caminho). Ordenados do mais comum para o menos comum.
CAMINHOS_RTSP: list[tuple[str, str]] = [
    # Genéricos / ONVIF — cobrem boa parte das câmeras
    ("Genérico", "/"),
    ("Genérico", "/live"),
    ("Genérico", "/live.sdp"),
    ("Genérico", "/stream"),
    ("Genérico", "/stream1"),
    ("Genérico", "/stream2"),
    ("Genérico", "/11"),
    ("Genérico", "/12"),
    ("Genérico", "/ch0"),
    ("Genérico", "/ch01.264"),
    ("Genérico", "/video1"),
    ("Genérico", "/media/video1"),
    ("ONVIF", "/onvif1"),
    ("ONVIF", "/onvif-media/media.amp"),

    # Hikvision (e OEMs)
    ("Hikvision", "/Streaming/Channels/101"),
    ("Hikvision", "/Streaming/Channels/102"),
    ("Hikvision", "/Streaming/Channels/1"),
    ("Hikvision", "/h264/ch1/main/av_stream"),
    ("Hikvision", "/h264/ch1/sub/av_stream"),

    # Dahua (e OEMs: Intelbras, Amcrest)
    ("Dahua", "/cam/realmonitor?channel=1&subtype=0"),
    ("Dahua", "/cam/realmonitor?channel=1&subtype=1"),

    # Intelbras
    ("Intelbras", "/onvif1"),
    ("Intelbras", "/cam/realmonitor?channel=1&subtype=0"),

    # Axis
    ("Axis", "/axis-media/media.amp"),
    ("Axis", "/mpeg4/media.amp"),

    # Foscam
    ("Foscam", "/videoMain"),
    ("Foscam", "/videoSub"),

    # Reolink
    ("Reolink", "/h264Preview_01_main"),
    ("Reolink", "/h264Preview_01_sub"),

    # Vivotek
    ("Vivotek", "/live.sdp"),
    ("Vivotek", "/live2.sdp"),

    # TP-Link / Tapo
    ("TP-Link Tapo", "/stream1"),
    ("TP-Link Tapo", "/stream2"),

    # Ubiquiti UniFi
    ("UniFi", "/s0"),
    ("UniFi", "/s1"),

    # Wyze (firmware RTSP)
    ("Wyze", "/live"),

    # D-Link
    ("D-Link", "/play1.sdp"),
    ("D-Link", "/live1.sdp"),

    # Panasonic
    ("Panasonic", "/MediaInput/h264"),

    # Sony
    ("Sony", "/media/video1"),

    # Bosch
    ("Bosch", "/rtsp_tunnel"),

    # V380 / V380 Pro (P2P por UID; RTSP exposto na LAN)
    ("V380", "/live/ch00_0"),
    ("V380", "/live/ch00_1"),
    ("V380", "/live/ch01_0"),

    # iCSee / XMEye / Xiongmai (chipset Sofia; RTSP na LAN)
    ("iCSee/XMEye", "/user=admin&password=&channel=1&stream=0.sdp?"),
    ("iCSee/XMEye", "/user=admin&password=&channel=1&stream=1.sdp?"),

    # Yoosee / Gwell (P2P por UID; RTSP exposto na LAN)
    ("Yoosee", "/onvif1"),
    ("Yoosee", "/onvif2"),
]


def caminhos(marca: str | None = None) -> list[str]:
    """Retorna os caminhos a testar; filtra por marca se informada."""
    if marca:
        m = marca.strip().lower()
        filtrados = [p for fab, p in CAMINHOS_RTSP if m in fab.lower()]
        if filtrados:
            return _dedup(filtrados)
    return _dedup([p for _, p in CAMINHOS_RTSP])


def _dedup(itens: list[str]) -> list[str]:
    """Remove duplicatas preservando a ordem."""
    visto: set[str] = set()
    saida: list[str] = []
    for i in itens:
        if i not in visto:
            visto.add(i)
            saida.append(i)
    return saida
