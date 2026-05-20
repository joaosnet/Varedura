import os
import glob
import datetime
from monitor.stalker import (
    _generate_combined_pdf_worker,
    full_ping_history,
    get_speed_tester,
    config,
)
from monitor.speed_tester import SpeedTestResult


def cleanup_exports():
    for p in glob.glob("exports/relatorio_formal_*.pdf"):
        try:
            os.remove(p)
        except Exception:
            pass
    for p in glob.glob("exports/ping_history_*.csv"):
        try:
            os.remove(p)
        except Exception:
            pass
    for p in glob.glob("exports/speed_history_*.csv"):
        try:
            os.remove(p)
        except Exception:
            pass


def test_generate_small_pdf(tmp_path):
    # Preparar ambiente
    os.makedirs("exports", exist_ok=True)
    cleanup_exports()

    # Popular histórico reduzido
    now = datetime.datetime.now()
    full_ping_history.clear()
    for i in range(20):
        ts = now - datetime.timedelta(seconds=(20 - i))
        local = 10.0 + i * 0.5
        ext = 20.0 + i * 0.3
        full_ping_history.append((ts, local, ext))

    # Criar um resultado de velocidade para que stats.test_count > 0
    tester = get_speed_tester()
    tester.stats.test_count = 0
    tester.stats.history_down.clear()
    tester.stats.history_up.clear()
    tester.stats.timestamps.clear()

    result = SpeedTestResult(
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=15.0,
        servidor="test",
        timestamp=now,
    )
    tester.stats.add(result)

    # Executar worker (síncrono) e verificar arquivo
    _generate_combined_pdf_worker()

    files = glob.glob("exports/relatorio_formal_*.pdf")
    assert files, "Nenhum PDF gerado"

    newest = max(files, key=os.path.getmtime)
    size = os.path.getsize(newest)

    # Limite conservador para garantir que não é 0KB
    assert size > 100, f"Arquivo gerado muito pequeno: {size} bytes"

    # Limpeza
    cleanup_exports()


def test_large_history_downsampling_and_full_flag(tmp_path):
    """Testa que o downsampling ocorre por padrão e que full_history True ainda gera arquivo."""
    os.makedirs("exports", exist_ok=True)
    cleanup_exports()

    # Preparar histórico grande
    now = datetime.datetime.now()
    full_ping_history.clear()
    for i in range(1200):
        ts = now - datetime.timedelta(seconds=(1200 - i))
        local = 10.0 + (i % 100) * 0.1
        ext = 20.0 + (i % 100) * 0.05
        full_ping_history.append((ts, local, ext))

    # Ajustar config para forçar downsampling quando full_history=False
    old_max = config.export_max_points
    config.export_max_points = 500

    tester = get_speed_tester()
    tester.stats.test_count = 0
    tester.stats.history_down.clear()
    tester.stats.history_up.clear()
    tester.stats.timestamps.clear()

    # Adicionar um resultado de velocidade
    result = SpeedTestResult(
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=15.0,
        servidor="test",
        timestamp=now,
    )
    tester.stats.add(result)

    # Gerar com downsampling (padrão)
    _generate_combined_pdf_worker(full_history=False)
    files = glob.glob("exports/relatorio_formal_*.pdf")
    assert files, "Nenhum PDF gerado com downsampling"
    newest = max(files, key=os.path.getmtime)
    size_ds = os.path.getsize(newest)
    assert size_ds > 100, "Arquivo gerado com downsampling é muito pequeno"
    cleanup_exports()

    # Gerar forçando histórico completo
    _generate_combined_pdf_worker(full_history=True)
    files = glob.glob("exports/relatorio_formal_*.pdf")
    assert files, "Nenhum PDF gerado com full_history"
    newest = max(files, key=os.path.getmtime)
    size_full = os.path.getsize(newest)
    assert size_full > 100, "Arquivo gerado com full_history é muito pequeno"

    # Restaurar config
    config.export_max_points = old_max
    cleanup_exports()
