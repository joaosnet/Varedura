import pytest
from cli import admin_tasks
from docker_cleaner.core import WSLDockerCleaner


def test_admin_helper_requires_admin(monkeypatch):
    # Simulate not admin
    monkeypatch.setattr(WSLDockerCleaner, "is_admin", lambda self: False)
    rc = admin_tasks.main(["compact_vhdx"])
    assert rc == 1


def test_admin_helper_compact_runs(monkeypatch):
    # Simulate admin and fake compact returning True
    monkeypatch.setattr(WSLDockerCleaner, "is_admin", lambda self: True)
    monkeypatch.setattr(WSLDockerCleaner, "compact_vhdx_files", lambda self: True)
    rc = admin_tasks.main(["compact_vhdx"])
    assert rc == 0


def test_admin_helper_configure_sparse_runs(monkeypatch):
    # Simulate admin and fake configure returning True
    monkeypatch.setattr(WSLDockerCleaner, "is_admin", lambda self: True)
    monkeypatch.setattr(WSLDockerCleaner, "configure_wsl_sparse", lambda self: True)
    rc = admin_tasks.main(["configure_sparse"])
    assert rc == 0
