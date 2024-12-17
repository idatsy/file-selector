# Simple CLI Directory Browser and Clipboard Snippet Tool

This is a minimal tool that allows you to navigate through a directory tree using vim-like keybindings (j/k or arrow keys), select files or directories, and copy their contents as Markdown snippets to the system clipboard.

## Features

- Navigate files and directories
- Select multiple files or entire directories
- Copies selected files' contents to the clipboard as a Markdown snippet
- Vim-like navigation (`j/k/gg/G`) and file selection (`Enter`)

## Key Bindings

- **Navigation:**  
  - `j` / `↓`: Move down  
  - `k` / `↑`: Move up  
  - `[count]j` or `[count]k`: Move multiple lines  
  - `gg`: Jump to top  
  - `G`: Jump to bottom or `[count]G` to jump to a specific line number

- **Selection:**  
  - `Enter`: Toggle selection of a file or directory (directories toggle all descendants)

- **Exit:**  
  - `q`: Quit

## Requirements

- Python 3.6+  
- `pyperclip`
- linux
- xclip
