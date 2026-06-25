"""Catálogo de portas → serviço amigável para usuários leigos.

Módulo **puro** (sem psutil/rede): apenas tabelas e funções de classificação.
As funções retornam **chaves de i18n**, não textos literais — a tradução vive
em ``i18n/pt.json`` / ``i18n/en.json``. Isso mantém o catálogo enxuto (várias
portas compartilham a mesma explicação) e tudo traduzível.
"""

from __future__ import annotations

# porta -> (label_key, expl_key)
# Explicações são compartilhadas de propósito (todos os bancos -> port.database.expl)
# para manter o número de chaves de i18n baixo.
PORT_CATALOG: dict[int, tuple[str, str]] = {
    20: ("port.ftp", "port.ftp.expl"),
    21: ("port.ftp", "port.ftp.expl"),
    22: ("port.ssh", "port.ssh.expl"),
    23: ("port.telnet", "port.telnet.expl"),
    25: ("port.smtp", "port.email_send.expl"),
    53: ("port.dns", "port.dns.expl"),
    67: ("port.dhcp", "port.dhcp.expl"),
    68: ("port.dhcp", "port.dhcp.expl"),
    80: ("port.http", "port.http.expl"),
    110: ("port.pop3", "port.email_recv.expl"),
    123: ("port.ntp", "port.ntp.expl"),
    135: ("port.msrpc", "port.windows_rpc.expl"),
    137: ("port.netbios", "port.windows_share.expl"),
    138: ("port.netbios", "port.windows_share.expl"),
    139: ("port.netbios", "port.windows_share.expl"),
    143: ("port.imap", "port.email_recv.expl"),
    161: ("port.snmp", "port.snmp.expl"),
    389: ("port.ldap", "port.ldap.expl"),
    443: ("port.https", "port.https.expl"),
    445: ("port.smb", "port.windows_share.expl"),
    465: ("port.smtps", "port.email_send.expl"),
    514: ("port.syslog", "port.syslog.expl"),
    587: ("port.smtp_sub", "port.email_send.expl"),
    631: ("port.printer", "port.printer.expl"),
    993: ("port.imaps", "port.email_recv.expl"),
    995: ("port.pop3s", "port.email_recv.expl"),
    1433: ("port.mssql", "port.database.expl"),
    1521: ("port.oracle", "port.database.expl"),
    1883: ("port.mqtt", "port.iot.expl"),
    1900: ("port.ssdp", "port.discovery.expl"),
    2049: ("port.nfs", "port.file_share.expl"),
    3000: ("port.devserver", "port.devserver.expl"),
    3306: ("port.mysql", "port.database.expl"),
    3389: ("port.rdp", "port.remote_desktop.expl"),
    5000: ("port.devserver", "port.devserver.expl"),
    5060: ("port.sip", "port.voip.expl"),
    5173: ("port.devserver", "port.devserver.expl"),
    5353: ("port.mdns", "port.discovery.expl"),
    5432: ("port.postgres", "port.database.expl"),
    5900: ("port.vnc", "port.remote_desktop.expl"),
    5938: ("port.teamviewer", "port.remote_desktop.expl"),
    6379: ("port.redis", "port.cache.expl"),
    8000: ("port.devserver", "port.devserver.expl"),
    8080: ("port.http_alt", "port.http.expl"),
    8443: ("port.https_alt", "port.https.expl"),
    9000: ("port.devserver", "port.devserver.expl"),
    9090: ("port.devserver", "port.devserver.expl"),
    9200: ("port.elastic", "port.database.expl"),
    11434: ("port.ollama", "port.ai_local.expl"),
    27017: ("port.mongo", "port.database.expl"),
}

# Limite inferior da faixa dinâmica/efêmera (IANA): 49152–65535.
EPHEMERAL_START = 49152

# Endereços de bind que significam "todas as interfaces" (exposto à rede).
_ALL_INTERFACES = {"0.0.0.0", "::", "*", "todas", "all"}
# Endereços que significam "somente este computador" (loopback).
_LOCAL_ONLY = {"127.0.0.1", "::1", "localhost"}


def describe_port(porta: int, protocolo: str = "TCP") -> tuple[str, str]:
    """Retorna ``(label_key, expl_key)`` para uma porta. O chamador aplica ``t()``.

    Fallbacks pensados para não assustar leigos:
    - portas dinâmicas/efêmeras (>= ``EPHEMERAL_START``) -> ``port.ephemeral``
      ("conexão temporária", texto tranquilizador);
    - demais desconhecidas -> ``port.unknown`` ("Serviço (porta {porta})").
    """
    hit = PORT_CATALOG.get(porta)
    if hit is not None:
        return hit
    if porta >= EPHEMERAL_START:
        return ("port.ephemeral", "port.ephemeral.expl")
    return ("port.unknown", "port.unknown.expl")


def classify_exposure(endereco: str) -> tuple[str, str]:
    """Retorna ``(chip_key, color)`` indicando o quão exposto está o socket.

    O campo ``endereco`` do scanner é apenas o IP de bind (``"Todas"`` quando é
    ``0.0.0.0``), nunca ``host:porta`` — então classificamos direto, sem parsing.

    - exposto à rede (todas as interfaces): ``0.0.0.0`` / ``::`` / ``"Todas"``;
    - só neste PC (loopback): ``127.0.0.1`` / ``::1`` / ``localhost``;
    - rede local: qualquer outro IP concreto.

    As cores reaproveitam a linguagem dos cards de ping (verde = ok/seguro,
    laranja = atenção).
    """
    norm = (endereco or "").strip().lower()
    if norm in _ALL_INTERFACES:
        return ("ports.exposure_all", "orange1")
    if norm in _LOCAL_ONLY or norm.startswith("127."):
        return ("ports.exposure_local", "green")
    return ("ports.exposure_lan", "cyan")


def is_exposed(endereco: str) -> bool:
    """Conveniência: True se o socket escuta em todas as interfaces (exposto)."""
    return (endereco or "").strip().lower() in _ALL_INTERFACES
