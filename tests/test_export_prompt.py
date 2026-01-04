import os
import glob
import datetime
from monitor.stalker import (
    prompt_export_report,
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


def test_prompt_export_cancel(tmp_path):
    os.makedirs("exports", exist_ok=True)
    cleanup_exports()

    # Ensure there is data
    now = datetime.datetime.now()
    full_ping_history.clear()
    full_ping_history.append((now, 10.0, 20.0))

    res = prompt_export_report(simulated_choice="n")
    assert "cancelada" in res.lower()


def test_prompt_export_confirm_triggers_export(tmp_path):
    os.makedirs("exports", exist_ok=True)
    cleanup_exports()

    now = datetime.datetime.now()
    full_ping_history.clear()
    for i in range(10):
        full_ping_history.append((now, 10.0 + i, 20.0 + i))

    tester = get_speed_tester()
    tester.stats.test_count = 0
    tester.stats.history_down.clear()
    tester.stats.history_up.clear()
    tester.stats.timestamps.clear()

    result = SpeedTestResult = None

    # Simulate confirmation
    res = prompt_export_report(simulated_choice="s")
    assert "exportando" in res.lower()
    cleanup_exports()