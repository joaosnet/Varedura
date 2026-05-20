from monitor.stalker import (
    set_allow_full_history_export,
    load_prefs,
    config,
    prompt_export_report,
    handle_key,
)
from i18n import t


def test_prefs_persistence(tmp_path):
    prefs_file = tmp_path / "prefs.json"
    config.prefs_file = str(prefs_file)

    # Garantir estado inicial
    set_allow_full_history_export(False)
    assert config.allow_full_history_export is False

    # Salvar como True
    set_allow_full_history_export(True)
    assert config.allow_full_history_export is True

    # Reset para False na memória e carregar do arquivo
    config.allow_full_history_export = False
    load_prefs()
    assert config.allow_full_history_export is True


def test_prompt_export_save_always(tmp_path):
    # Configurar prefs path
    prefs_file = tmp_path / "prefs2.json"
    config.prefs_file = str(prefs_file)

    # Garantir que está False
    set_allow_full_history_export(False)
    assert config.allow_full_history_export is False

    # Chamar prompt com 'sa' (simula confirmar e salvar)
    res = prompt_export_report(simulated_choice="sa")
    assert t("stalker.exporting_full") in res or "exportando" in res.lower() or "exporting" in res.lower()

    # Carregar do disco para garantir persistência
    config.allow_full_history_export = False
    load_prefs()
    assert config.allow_full_history_export is True


def test_handle_key_toggle_writes(tmp_path):
    prefs_file = tmp_path / "prefs3.json"
    config.prefs_file = str(prefs_file)

    # Iniciar False
    set_allow_full_history_export(False)
    assert config.allow_full_history_export is False

    # Chamar handle_key para alternar
    msg = handle_key("f")
    # Check that the toggle message contains the enabled status (language-agnostic)
    from i18n import t
    assert t("stalker.ports_enabled") in msg.lower() or "ativado" in msg.lower() or "enabled" in msg.lower()
    # Carregar do disco
    config.allow_full_history_export = False
    load_prefs()
    assert config.allow_full_history_export is True
