import os
from datetime import datetime
from pathlib import Path

from cli.richlog import DailyLogWriter


def test_daily_writer_writes_file(tmp_path):
    # Arrange
    logs_dir = tmp_path / "logs"
    writer = DailyLogWriter(logs_dir=logs_dir, ui_write=None)

    # Act
    writer.write("Test message")
    writer.flush()

    # Assert file exists and contains message
    today = datetime.now().date().isoformat()
    expected_file = logs_dir / f"{today}.log"
    assert expected_file.exists()
    content = expected_file.read_text(encoding="utf-8")
    assert "Test message" in content


def test_daily_writer_ui_callback(tmp_path):
    captured = []

    def ui_write(text: str) -> None:
        captured.append(text)

    writer = DailyLogWriter(logs_dir=tmp_path / "logs2", ui_write=ui_write)
    writer.write("UI message")
    # The UI callback should have been run
    assert any("UI message" in c for c in captured)


def test_thread_exception_is_logged(tmp_path):
    # Set up writer and logging
    logs_dir = tmp_path / "logs_thread"
    writer = DailyLogWriter(logs_dir=logs_dir, ui_write=None)
    import logging
    handler = logging.StreamHandler(writer)
    logger = logging.getLogger("test-thread")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Thread that raises an uncaught exception
    import threading

    def raise_in_thread():
        raise RuntimeError("thread-failure")

    # Install threading excepthook that logs to our logger
    def thread_exhook(args):
        exc = getattr(args, "exc_value", None)
        if exc:
            logger.exception("Unhandled thread exception", exc_info=(type(exc), exc, getattr(exc, "__traceback__", None)))

    threading.excepthook = thread_exhook

    t = threading.Thread(target=raise_in_thread)
    t.start()
    t.join()

    # Assert file contains the exception message
    today = datetime.now().date().isoformat()
    expected_file = logs_dir / f"{today}.log"
    assert expected_file.exists()
    content = expected_file.read_text(encoding="utf-8")
    assert "thread-failure" in content


def test_stderr_redirection_writes_to_file(tmp_path):
    logs_dir = tmp_path / "logs_stderr"
    writer = DailyLogWriter(logs_dir=logs_dir, ui_write=None)
    import sys
    orig = sys.stderr
    try:
        sys.stderr = writer
        sys.stderr.write("stderr message\n")
        sys.stderr.flush()
        today = datetime.now().date().isoformat()
        expected_file = logs_dir / f"{today}.log"
        assert expected_file.exists()
        content = expected_file.read_text(encoding="utf-8")
        assert "stderr message" in content
    finally:
        sys.stderr = orig


def test_wsl_docker_cleaner_log_uses_python_logging(tmp_path):
    # Ensure WSLDockerCleaner.log forwards messages to the Python logging system
    logs_dir = tmp_path / "logs_wsl"
    writer = DailyLogWriter(logs_dir=logs_dir, ui_write=None)
    import logging
    handler = logging.StreamHandler(writer)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    from docker_cleaner.core import WSLDockerCleaner
    c = WSLDockerCleaner()
    c.log("Cleaner test error", level="ERROR")
    writer.flush()

    today = datetime.now().date().isoformat()
    expected_file = logs_dir / f"{today}.log"
    assert expected_file.exists()
    content = expected_file.read_text(encoding="utf-8")
    assert "Cleaner test error" in content


def test_daily_writer_handles_write_and_ui_exceptions(tmp_path):
    # Writer with file that raises on write and UI callback that raises
    logs_dir = tmp_path / "logs_ex"
    def ui_raise(text: str) -> None:
        raise RuntimeError("ui fail")
    writer = DailyLogWriter(logs_dir=logs_dir, ui_write=ui_raise)
    # Create dummy file-like object that raises on write
    class BrokenFP:
        def write(self, _):
            raise IOError("disk full")
        def flush(self):
            raise IOError("flush fail")
        def close(self):
            raise IOError("close fail")
    writer._current_fp = BrokenFP()
    # The write should not raise even if underlying operations fail
    writer.write("hello")
    # flush and close should be swallow exceptions
    writer.flush()
    writer.close()
