import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, LoadingIndicator
from textual.containers import Container, Vertical
from textual.message import Message
from rich.text import Text

def get_recursive_size(path: Path) -> int:
    """Calculate the size of a file or directory recursively without following symlinks."""
    try:
        if path.is_symlink():
            return 0 # Or symlink size if preferred, usually negligible
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total_size = 0
            for entry in os.scandir(path):
                try:
                    p = Path(entry.path)
                    if p.is_symlink():
                        continue
                    if entry.is_file():
                        total_size += entry.stat().st_size
                    elif entry.is_dir():
                        total_size += get_recursive_size(p)
                except (PermissionError, FileNotFoundError):
                    continue
            return total_size
    except (PermissionError, FileNotFoundError):
        pass
    return 0

def format_size(size: int) -> str:
    """Format size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

class SizeUpdate(Message):
    """Message sent when sizes are calculated."""
    def __init__(self, current_path: Path, items: List[Tuple[str, int, str]]):
        self.current_path = current_path
        self.items = items
        super().__init__()

class DiskViewer(App):
    """A CUI disk space visualization tool."""

    CSS = """
    DataTable {
        height: 100%;
    }
    #loading-container {
        height: 1fr;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("enter", "enter_dir", "Enter Dir"),
        ("backspace", "back_dir", "Back"),
        ("u", "back_dir", "Up"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, start_path: str = "."):
        super().__init__()
        self.current_path = Path(start_path).resolve()
        self.is_loading = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            DataTable(id="file-table"),
            id="main-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Size", "Type")
        table.cursor_type = "row"
        self.refresh_table()

    def refresh_table(self) -> None:
        if self.is_loading:
            return
        
        self.is_loading = True
        self.sub_title = f"Scanning {self.current_path}..."
        
        # Run calculation in a separate thread to keep UI responsive
        self.run_worker(self.calculate_sizes(self.current_path))

    async def calculate_sizes(self, path: Path):
        items: List[Tuple[str, int, str]] = []
        try:
            # First, list immediate children to show *something* or just scan them
            entries = list(os.scandir(path))
            for entry in entries:
                p = Path(entry.path)
                item_type = "Folder" if entry.is_dir() else "File"
                # Use to_thread for the recursive size calc
                size = await asyncio.to_thread(get_recursive_size, p)
                items.append((entry.name, size, item_type))
        except (PermissionError, FileNotFoundError):
            pass

        # Sort by size descending
        items.sort(key=lambda x: x[1], reverse=True)
        self.post_message(SizeUpdate(path, items))

    def on_size_update(self, message: SizeUpdate) -> None:
        self.is_loading = False
        if message.current_path != self.current_path:
            return # Path changed while we were calculating
        
        table = self.query_one(DataTable)
        table.clear()
        self.sub_title = str(self.current_path)

        for name, size, item_type in message.items:
            table.add_row(
                Text(name, style="bold cyan" if item_type == "Folder" else ""),
                format_size(size),
                item_type,
                key=name
            )

    def action_enter_dir(self) -> None:
        if self.is_loading:
            return
        table = self.query_one(DataTable)
        cursor_row = table.cursor_row
        if cursor_row is not None:
            try:
                row_key = table.get_row_key_at(cursor_row)
                selected_name = row_key.value
                if selected_name:
                    new_path = self.current_path / selected_name
                    if new_path.is_dir():
                        self.current_path = new_path
                        self.refresh_table()
            except Exception:
                pass

    def action_back_dir(self) -> None:
        if self.is_loading:
            return
        if self.current_path != self.current_path.parent:
            self.current_path = self.current_path.parent
            self.refresh_table()

    def action_refresh(self) -> None:
        self.refresh_table()

def main():
    path = "."
    if len(sys.argv) > 1:
        path = sys.argv[1]
    app = DiskViewer(start_path=path)
    app.run()

if __name__ == "__main__":
    main()
