"""Pacote rtsp: lógica do scanner de câmeras IP / streams RTSP.

Portado do app standalone scan_rsp. Os módulos deste pacote importam
``DATA_DIR`` daqui para resolver arquivos de estado/dados na raiz do projeto.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]  # the Varedura project root
