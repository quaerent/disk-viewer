# Disk Viewer

A simple CUI (Command-line User Interface) tool to visualize disk space usage on macOS, written in Python.

## Features

- **Recursive size calculation**: Shows the total size of files and directories.
- **Interactive Navigation**: Enter directories with `Enter`, go back with `Backspace` or `U`.
- **Sorted View**: Automatically sorts items by size (descending).
- **Modern UI**: Built with `Textual` for a responsive and beautiful terminal experience.

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
git clone <repository-url>
cd disk-viewer
poetry install
```

## Usage

Run the tool using Poetry:

```bash
poetry run disk-viewer [path]
```

Or install it globally:

```bash
poetry build
pip install dist/*.whl
disk-viewer [path]
```

### Key Bindings

- `q`: Quit
- `Enter`: Enter selected directory
- `Backspace` / `u`: Go up one directory level
- `r`: Refresh current view
- `Arrow Keys`: Navigate the list
