# disk-viewer

A high-performance Terminal User Interface (TUI) tool designed for macOS to visualize disk space usage and identify large files/directories. Built with Python and the Textual framework.

## Key Features

- **Recursive Disk Analysis**: Accurately calculates real disk usage using block allocation (handles sparse files like `Docker.raw` correctly).
- **Persistent Caching**: Uses a high-precision nanosecond timestamp (mtime_ns) validation to cache directory sizes, enabling near-instant browsing of previously scanned paths.
- **Delta-Based Updates**: Automatically propagates size changes up the directory tree without requiring full rescans.
- **Interactive Navigation**: Fluent keyboard-driven interface to explore your filesystem.
- **System Overview**: Displays global macOS disk usage (Total, Used, Free) at a glance.
- **Clipboard Integration**: Quickly copy current paths to the clipboard for use in other terminal commands.

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

### Prerequisites

- Python 3.10 or higher.
- macOS (for `pbcopy` support).

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/disk-viewer.git
cd disk-viewer

# Install dependencies
poetry install
```

## Usage

Start the tool using Poetry:

```bash
# Scan the current directory
poetry run disk-viewer

# Scan a specific path
poetry run disk-viewer /Users/username/Downloads
```

### Controls

| Key | Action |
|-----|--------|
| `Enter` | Enter the selected directory |
| `Backspace` / `u` | Go up to the parent directory |
| `r` | **Deep Refresh**: Force a full recursive rescan of the current tree |
| `c` | Copy the current absolute path to clipboard |
| `q` | Quit the application |
| `Arrows` | Navigate through the list |

## Performance

The tool utilizes asynchronous workers to keep the UI responsive during heavy disk I/O operations. Cached results are stored in `~/.disk_viewer_cache.json`.

## License

MIT
