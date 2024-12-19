"""
A simple command-line tool to browse a directory tree, select files or directories,
and copy their contents (in a formatted snippet) to the clipboard.

New Feature:
- Press Shift+> on a highlighted directory to hide all its files and nested directories.
- Press Shift+< on a highlighted directory to unhide them.
All other functionality remains the same.
"""

import curses
import os
import pyperclip
from typing import List, Tuple, Set


def get_language_for_file(path: str) -> str:
    """
    Guess the programming language based on file extension.

    Args:
        path (str): The file path.

    Returns:
        str: The language name, or empty string if unknown.
    """
    ext = os.path.splitext(path)[1].lower()
    match ext:
        case ".c":
            return "c"
        case ".cpp":
            return "cpp"
        case ".cs":
            return "csharp"
        case ".go":
            return "go"
        case ".java":
            return "java"
        case ".js":
            return "javascript"
        case ".kt":
            return "kotlin"
        case ".m":
            return "objective-c"
        case ".php":
            return "php"
        case ".pl":
            return "perl"
        case ".py":
            return "python"
        case ".rs":
            return "rust"
        case ".ts":
            return "typescript"
        case "sol":
            return "solidity"
        case _:
            return ""


def read_file_content(filepath: str) -> str:
    """
    Safely read the contents of a file as text.

    Args:
        filepath (str): The path to the file.

    Returns:
        str: The file contents, or an empty string if reading fails.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def build_file_tree(root: str) -> List[Tuple[str, int, bool]]:
    """
    Recursively build a file tree from the given root directory.

    Args:
        root (str): The root directory path.

    Returns:
        List[Tuple[str, int, bool]]: A list of tuples (relative_path, depth, is_dir).
    """
    result = []

    def recurse(path: str, depth: int):
        entries = sorted(os.listdir(path))
        for e in entries:
            full_path = os.path.join(path, e)
            rel_path = os.path.relpath(full_path, root)
            is_dir = os.path.isdir(full_path)
            result.append((rel_path, depth, is_dir))
            if is_dir:
                recurse(full_path, depth + 1)

    recurse(root, 0)
    return result


def build_snippet(selected: Set[str], root: str) -> str:
    """
    Build a Markdown snippet combining selected files, with code blocks.

    Args:
        selected (Set[str]): A set of relative paths selected.
        root (str): The root directory path.

    Returns:
        str: A formatted Markdown snippet of selected file contents.
    """
    snippet_parts = []
    for p in sorted(selected):
        full_path = os.path.join(root, p)
        if os.path.isfile(full_path):
            filename = os.path.basename(p)
            directory_info = os.path.dirname(p)
            if directory_info == ".":
                directory_info = ""

            lang = get_language_for_file(full_path)
            content = read_file_content(full_path)

            # Format the snippet with proper markdown code block
            snippet_part = f"{directory_info + '/' if directory_info else ''}{filename}\n```{lang}\n{content}\n```"
            snippet_parts.append(snippet_part.strip("\n"))

    final_snippet = "\n\n".join(snippet_parts).strip()
    return final_snippet


def update_clipboard(selected: Set[str], root: str):
    """
    Update the system clipboard with the current snippet of selected files.

    Args:
        selected (Set[str]): A set of selected paths.
        root (str): The root directory path.
    """
    snippet = build_snippet(selected, root)
    pyperclip.copy(snippet)


def toggle_selection(
    selected: Set[str], tree: List[Tuple[str, int, bool]], index: int, root: str
):
    """
    Toggle the selection of a file or directory at a given index in the tree.
    If a directory, toggle all of its descendants.

    Args:
        selected (Set[str]): Current set of selected paths.
        tree (List[Tuple[str, int, bool]]): The file tree.
        index (int): Index in the tree list.
        root (str): The root directory path.
    """
    rel_path, depth, is_dir = tree[index]

    if is_dir:
        # Determine all descendants
        base_path = os.path.join(root, rel_path)
        all_descendants = []
        for p, d, idir in tree:
            full_p = os.path.join(root, p)
            if full_p == base_path or full_p.startswith(base_path + os.sep):
                all_descendants.append(p)

        # Check if directory is fully selected
        all_descendants_set = set(all_descendants)
        if all_descendants_set.issubset(selected):
            # All already selected, deselect them
            selected.difference_update(all_descendants_set)
        else:
            # Not all selected, select all that aren't selected
            selected.update(all_descendants_set)
    else:
        # Just a file
        if rel_path in selected:
            selected.remove(rel_path)
        else:
            selected.add(rel_path)


def get_visible_indices(
    tree: List[Tuple[str, int, bool]], collapsed: Set[str]
) -> List[int]:
    """
    Given the full tree and a set of collapsed directories, return the indices
    of the items that should be visible.

    We hide any item that is inside a collapsed directory (except the directory itself).
    """
    visible = []
    for i, (p, depth, is_dir) in enumerate(tree):
        # Check if this item is inside any collapsed directory
        # A directory d is collapsed means all items under d are hidden,
        # but d itself stays visible.
        hidden = False
        for c in collapsed:
            # If p != c and p starts with c + os.sep, it's hidden
            if p != c and p.startswith(c + os.sep):
                hidden = True
                break
        if not hidden:
            visible.append(i)
    return visible


def main(stdscr):
    """
    The main interactive UI loop using curses.

    Args:
        stdscr: The curses standard screen object.
    """
    # Initialize colors
    curses.start_color()
    curses.use_default_colors()
    # Create a subtle highlight color pair (grey on default background)
    curses.init_pair(1, 8, -1)  # 8 is grey in most terminal color schemes

    # Set nodelay mode to prevent input blocking
    stdscr.nodelay(1)

    # Enable keypad and remove cursor
    stdscr.keypad(1)
    curses.curs_set(0)

    # Reduce terminal latency by disabling input buffering and output processing
    curses.raw()
    curses.noecho()

    root = os.getcwd()
    tree = build_file_tree(root)

    selected = set()
    collapsed = set()  # Keep track of directories that are collapsed

    current_index = 0
    number_buffer = ""  # For handling number inputs for jumps and counts

    # Force initial clipboard update
    update_clipboard(selected, root)

    # To force a full redraw after selection toggles or view changes
    last_start_line = -1
    last_current_index = -1

    while True:
        # Compute visible indices based on collapsed state
        visible_indices = get_visible_indices(tree, collapsed)
        if not visible_indices:
            # If nothing is visible (extreme edge case?), reset collapse and show all
            collapsed.clear()
            visible_indices = get_visible_indices(tree, collapsed)

        # Ensure current_index is within range
        if current_index >= len(visible_indices):
            current_index = len(visible_indices) - 1
        if current_index < 0:
            current_index = 0

        h, w = stdscr.getmaxyx()
        # We'll show the navigation bar at the top (line 0)
        # File listing area below that
        max_lines = h - 1  # one line for navigation at the top

        # Calculate the middle of the screen (for centering current file)
        middle = max_lines // 2

        start_line = max(0, current_index - middle)
        if start_line + max_lines > len(visible_indices):
            start_line = max(0, len(visible_indices) - max_lines)

        # Draw navigation bar at the top (line 0)
        stdscr.move(0, 0)
        stdscr.clrtoeol()
        stdscr.attron(curses.color_pair(1))
        nav_line = "Navigation: ↑/↓/j/k [count] for movement | [count]G/go to line | gg top | q quit | Enter toggle | Shift+> hide | Shift+< unhide"
        # Truncate if too long
        nav_line = nav_line[:w]
        stdscr.addstr(0, 0, nav_line)
        stdscr.attroff(curses.color_pair(1))
        stdscr.noutrefresh()

        # Only redraw lines if something changed
        if start_line != last_start_line or current_index != last_current_index:
            # Draw each visible line
            for i, vi in enumerate(
                visible_indices[start_line : start_line + max_lines]
            ):
                p, depth, is_dir = tree[vi]
                filename = os.path.basename(p)
                indent = "  " * depth
                marker = "[D]" if is_dir else "   "
                sel_mark = "[x]" if p in selected else "[ ]"
                # line_number shown is based on the visible line number, not the original tree index
                line_number = i + start_line + 1
                line_str = f"{line_number:4d} {indent}{sel_mark} {marker} {filename}"

                stdscr.move(i + 1, 0)  # files start at line 1
                stdscr.clrtoeol()
                if (i + start_line) == current_index:
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addstr(i + 1, 0, line_str[:w])
                    stdscr.attroff(curses.A_REVERSE)
                else:
                    stdscr.addstr(i + 1, 0, line_str[:w])
                stdscr.noutrefresh()

            # Clear any extra lines if list got shorter
            shown_count = len(visible_indices[start_line : start_line + max_lines])
            for clr_i in range(shown_count + 1, max_lines + 1):
                stdscr.move(clr_i + 1, 0)
                stdscr.clrtoeol()
                stdscr.noutrefresh()

            last_start_line = start_line
            last_current_index = current_index

        curses.doupdate()
        curses.napms(10)

        key = stdscr.getch()
        if key in [curses.KEY_UP, ord("k")]:
            step = int(number_buffer) if number_buffer else 1
            current_index = max(current_index - step, 0)
            number_buffer = ""
        elif key in [curses.KEY_DOWN, ord("j")]:
            step = int(number_buffer) if number_buffer else 1
            current_index = min(current_index + step, len(visible_indices) - 1)
            number_buffer = ""
        elif key == ord("g"):
            if number_buffer:
                # Go to specific line number in visible lines
                target = int(number_buffer) - 1
                current_index = min(max(0, target), len(visible_indices) - 1)
                number_buffer = ""
            else:
                # Temporarily disable nodelay to wait for the next char
                curses.napms(50)
                stdscr.nodelay(0)
                next_key = stdscr.getch()
                stdscr.nodelay(1)
                if next_key == ord("g"):
                    # gg pressed - go to top visible line
                    current_index = 0
                elif next_key != -1 and next_key != ord("g"):
                    # If another key was pressed, interpret it as a normal key
                    if ord("0") <= next_key <= ord("9"):
                        number_buffer = chr(next_key)
        elif key == ord("G"):
            if number_buffer:
                target = int(number_buffer) - 1
                current_index = min(max(0, target), len(visible_indices) - 1)
            else:
                # Go to end of visible list
                current_index = len(visible_indices) - 1
            number_buffer = ""
        elif ord("0") <= key <= ord("9"):
            number_buffer += chr(key)
        elif key == ord("q"):
            break
        elif key == 10:  # ENTER
            if visible_indices:
                toggle_selection(selected, tree, visible_indices[current_index], root)
                update_clipboard(selected, root)
                # Force redraw
                last_start_line = -1
                last_current_index = -1
        elif key == ord(">"):  # Shift+>
            # Collapse the currently highlighted directory if it's a directory
            if visible_indices:
                rel_path, depth, is_dir = tree[visible_indices[current_index]]
                if is_dir and rel_path not in collapsed:
                    collapsed.add(rel_path)
                    # Force redraw
                    last_start_line = -1
                    last_current_index = -1
        elif key == ord("<"):  # Shift+<
            # Uncollapse the currently highlighted directory if it's collapsed
            if visible_indices:
                rel_path, depth, is_dir = tree[visible_indices[current_index]]
                if is_dir and rel_path in collapsed:
                    collapsed.remove(rel_path)
                    # Force redraw
                    last_start_line = -1
                    last_current_index = -1

    # End curses mode on exit
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()


curses.wrapper(main)
