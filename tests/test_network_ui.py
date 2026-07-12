from cli.network_ui import merge_visible_selection


def test_filtered_target_changes_preserve_hidden_selections():
    current = {"cloudflare_ipv4", "google_ipv4"}
    visible = {"cloudflare_ipv4"}

    assert merge_visible_selection(current, visible, set()) == {"google_ipv4"}
    assert merge_visible_selection(current, visible, visible) == current
