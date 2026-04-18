import os
import sys
import json
import stat
import asyncio
from pathlib import Path
from typing import List, Tuple, Dict
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
from textual.containers import Container
from textual.message import Message
from rich.text import Text

# Path for the persistent cache
CACHE_FILE = Path.home() / ".disk_viewer_cache.json"

class SizeCache:
    """Manages directory size caching with mtime_ns validation."""
    def __init__(self):
        self.cache: Dict[str, List] = {} # path -> [size, mtime_ns]
        self.load()

    def load(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f)
        except Exception:
            pass

    def get(self, path: Path) -> int | None:
        path_str = str(path.absolute())
        if path_str in self.cache:
            cached_size, cached_mtime_ns = self.cache[path_str]
            try:
                # Use nanosecond precision for reliable validation
                if path.lstat().st_mtime_ns == cached_mtime_ns:
                    return cached_size
            except (PermissionError, FileNotFoundError):
                pass
        return None

    def set(self, path: Path, size: int, mtime_ns: int):
        path_str = str(path.absolute())
        old_data = self.cache.get(path_str)
        
        # Update current path
        self.cache[path_str] = [size, mtime_ns]
        
        # If size changed, invalidate parents in cache to force them to recalculate
        if old_data is None or old_data[0] != size:
            current = path.parent
            # Invalidate up to root
            while str(current) != str(current.parent):
                parent_str = str(current.absolute())
                if parent_str in self.cache:
                    del self.cache[parent_str]
                current = current.parent

def get_recursive_size(path: Path, cache: SizeCache, bypass_cache: bool = False) -> int:
    """Calculate actual disk usage recursively, optionally bypassing cache."""
    try:
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode):
            return 0
        
        # Check cache for directories if not bypassing
        if stat.S_ISDIR(st.st_mode):
            if not bypass_cache:
                cached_val = cache.get(path)
                if cached_val is not None:
                    return cached_val

            total_size = 0
            try:
                for entry in os.scandir(path):
                    total_size += get_recursive_size(Path(entry.path), cache, bypass_cache)
            except (PermissionError, FileNotFoundError):
                pass
            
            # Store directory size in cache with ns precision
            cache.set(path, total_size, st.st_mtime_ns)
            return total_size
        else:
            # Actual usage for files
            return st.st_blocks * 512
    except (PermissionError, FileNotFoundError):
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
    """A CUI disk space visualization tool with robust caching."""

    CSS = """
    DataTable {
        height: 100%;
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
        self.size_cache = SizeCache()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(DataTable(id="file-table"))
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Size", "Type")
        table.cursor_type = "row"
        table.focus()
        self.refresh_table()

    def refresh_table(self, force: bool = False) -> None:
        if self.is_loading:
            return
        
        self.is_loading = True
        self.sub_title = f"{'Deep Scanning' if force else 'Scanning'} {self.current_path}..."
        
        self.run_worker(self.calculate_sizes(self.current_path, bypass_cache=force))

    async def calculate_sizes(self, path: Path, bypass_cache: bool = False):
        items: List[Tuple[str, int, str]] = []
        try:
            entries = list(os.scandir(path))
            for entry in entries:
                p = Path(entry.path)
                item_type = "Folder" if entry.is_dir() else "File"
                size = await asyncio.to_thread(get_recursive_size, p, self.size_cache, bypass_cache)
                items.append((entry.name, size, item_type))
        except (PermissionError, FileNotFoundError):
            pass

        items.sort(key=lambda x: x[1], reverse=True)
        self.post_message(SizeUpdate(path, items))
        
        await asyncio.to_thread(self.size_cache.save)

    def on_size_update(self, message: SizeUpdate) -> None:
        self.is_loading = False
        if message.current_path != self.current_path:
            return
        
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self.is_loading:
            return
        selected_name = event.row_key.value
        if selected_name:
            new_path = self.current_path / selected_name
            if new_path.is_dir():
                self.current_path = new_path
                self.refresh_table()

    def action_enter_dir(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.get_row_key_at(table.cursor_row)
                self.on_data_table_row_selected(DataTable.RowSelected(table, row_key))
            except Exception:
                pass

    def action_back_dir(self) -> None:
        if self.is_loading:
            return
        if self.current_path != self.current_path.parent:
            self.current_path = self.current_path.parent
            self.refresh_table()

    def action_refresh(self) -> None:
        self.refresh_table(force=True)

def main():
    path = "."
    if len(sys.argv) > 1:
        path = sys.argv[1]
    app = DiskViewer(start_path=path)
    app.run()

if __name__ == "__main__":
    main()
