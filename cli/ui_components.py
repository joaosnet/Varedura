from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import reactive

class StatCard(Container):
    """A dashboard statistic card."""
    
    DEFAULT_CSS = """
    StatCard {
        layout: vertical;
        align: center middle;
    }
    """
    
    value = reactive("")
    
    def __init__(self, title: str, value: str = "", id: str | None = None, classes: str | None = None):
        super().__init__(id=id, classes=classes)
        self.title = title
        self.value = value

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="stat-title")
        yield Static(self.value, classes="stat-value", id=f"{self.id}-value" if self.id else None)

    def watch_value(self, new_value: str) -> None:
        try:
            val_widget = self.query_one(f"#{self.id}-value", Static) if self.id else self.query_one(".stat-value", Static)
            val_widget.update(new_value)
        except Exception:
            pass
