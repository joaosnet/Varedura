import pytest

from main import CommandRunnerApp


def test_progress_methods_no_errors():
    app = CommandRunnerApp()
    # Methods should be callable even if app is not mounted; they handle missing widget gracefully
    app.start_progress("test", 100)
    app.update_progress(50)
    app.advance_progress(10)
    app.finish_progress()
    assert hasattr(app, "start_progress")
    assert hasattr(app, "update_progress")
    assert hasattr(app, "finish_progress")
