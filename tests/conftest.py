import pytest
from unittest.mock import MagicMock, patch
from textual.app import App

@pytest.fixture
def textual_app():
    """Fixture providing a Textual app with mocked external dependencies for safe testing."""
    with patch('subprocess.run') as mock_subprocess, \
         patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=True), \
         patch('ctypes.windll.shell32.ShellExecuteW') as mock_shell_execute:
        
        # Configure mocks
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_shell_execute.return_value = 0
        
        # Yield a generic App instance (subclass in tests as needed)
        app = App()
        yield app