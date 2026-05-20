import os
import glob
import datetime
from monitor.stalker import (
    prompt_export_report,
    full_ping_history,
    get_speed_tester,
)
from i18n import t


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
    assert t("stalker.export_cancelled") in res or "cancelada" in res.lower() or "cancelled" in res.lower()


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

    # Simulate confirmation
    res = prompt_export_report(simulated_choice="s")
    assert t("stalker.exporting_full") in res or "exportando" in res.lower() or "exporting" in res.lower()
    cleanup_exports()
