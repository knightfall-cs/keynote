#!/usr/bin/env python3
"""
Keynote - A lightweight, modern command-line tool for saving and running
frequently used or complex terminal commands.

Zero external dependencies - built entirely on Python standard library.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "2.0.0"

# ==============================================================================
# ANSI Styling & Formatting (Zero-Dependency)
# ==============================================================================

class Color:
    """ANSI color codes with automatic terminal & NO_COLOR detection."""
    _enabled: bool = True

    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    RESET = "\033[0m"

    @classmethod
    def init(cls) -> None:
        """Detect if ANSI colors should be enabled."""
        if (
            os.environ.get("NO_COLOR") is not None
            or os.environ.get("TERM") == "dumb"
            or not sys.stdout.isatty()
        ):
            cls._enabled = False
        else:
            cls._enabled = True

    @classmethod
    def style(cls, text: str, *codes: str) -> str:
        """Apply styling codes to text if enabled."""
        if not cls._enabled or not codes:
            return text
        prefix = "".join(codes)
        return f"{prefix}{text}{cls.RESET}"

    @classmethod
    def visible_len(cls, text: str) -> int:
        """Calculate visible length of text by stripping ANSI escape codes."""
        ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return len(ansi_regex.sub("", text))


def c_key(text: str) -> str:
    return Color.style(text, Color.CYAN, Color.BOLD)

def c_cmd(text: str) -> str:
    return Color.style(text, Color.WHITE)

def c_tag(text: str) -> str:
    return Color.style(f"[{text}]", Color.YELLOW)

def c_dim(text: str) -> str:
    return Color.style(text, Color.GRAY)

def c_bold(text: str) -> str:
    return Color.style(text, Color.BOLD)

def c_green(text: str) -> str:
    return Color.style(text, Color.GREEN, Color.BOLD)

def c_yellow(text: str) -> str:
    return Color.style(text, Color.YELLOW, Color.BOLD)

def c_red(text: str) -> str:
    return Color.style(text, Color.RED, Color.BOLD)


# ==============================================================================
# Storage & Config Management
# ==============================================================================

class Storage:
    """Manages Keynote snippet data adhering to XDG specs."""

    def __init__(self, custom_path: Optional[str] = None) -> None:
        self.file_path = self._resolve_path(custom_path)

    @staticmethod
    def _resolve_path(custom_path: Optional[str]) -> Path:
        if custom_path:
            return Path(custom_path).expanduser().resolve()

        env_path = os.environ.get("KEYNOTE_DATA_FILE")
        if env_path:
            return Path(env_path).expanduser().resolve()

        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            base_dir = Path(appdata) / "keynote"
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
            base_dir = Path(xdg_config) / "keynote"

        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "kn_data.json"

    def load(self) -> Dict[str, Dict[str, Any]]:
        """Load data and normalize entries into structured dictionary."""
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception:
            return {}

        normalized: Dict[str, Dict[str, Any]] = {}
        for key, val in raw_data.items():
            if isinstance(val, str):
                normalized[key] = {
                    "command": val,
                    "description": "",
                    "tags": [],
                    "usage_count": 0,
                    "last_used": None,
                    "created_at": datetime.datetime.now().isoformat(),
                }
            elif isinstance(val, dict):
                normalized[key] = {
                    "command": val.get("command", ""),
                    "description": val.get("description", ""),
                    "tags": list(val.get("tags", [])),
                    "usage_count": int(val.get("usage_count", 0)),
                    "last_used": val.get("last_used"),
                    "created_at": val.get("created_at", datetime.datetime.now().isoformat()),
                }
        return normalized

    def save(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Save data atomically to prevent corruption."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp_file, self.file_path)


# ==============================================================================
# Placeholder Interpolation & Clipboard Engine
# ==============================================================================

PLACEHOLDER_REGEX = re.compile(r"<([^>]+)>|\{\{([^}]+)\}\}")

def extract_placeholders(command: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Find all placeholders in a command.
    Returns a list of (raw_token, variable_name, default_value).
    """
    placeholders: List[Tuple[str, str, Optional[str]]] = []
    for match in PLACEHOLDER_REGEX.finditer(command):
        raw = match.group(0)
        inner = match.group(1) if match.group(1) is not None else match.group(2)
        inner = inner.strip()
        if ":" in inner:
            name, default = inner.split(":", 1)
            placeholders.append((raw, name.strip(), default.strip()))
        else:
            placeholders.append((raw, inner, None))
    return placeholders


def resolve_placeholders(command: str, cli_args: List[str], interactive: bool = True) -> str:
    """
    Substitute placeholders using positional CLI arguments, named key=val args,
    or interactive terminal prompts.
    """
    placeholders = extract_placeholders(command)
    if not placeholders:
        if cli_args:
            # If command has no placeholders, append extra arguments to the end
            return f"{command} " + " ".join(cli_args)
        return command

    named_args: Dict[str, str] = {}
    positional_args: List[str] = []

    for arg in cli_args:
        if "=" in arg and not arg.startswith("-"):
            k, v = arg.split("=", 1)
            named_args[k.strip()] = v.strip()
        else:
            positional_args.append(arg)

    pos_idx = 0
    resolved = command

    for raw, name, default in placeholders:
        value: Optional[str] = None

        if name in named_args:
            value = named_args[name]
        elif pos_idx < len(positional_args):
            value = positional_args[pos_idx]
            pos_idx += 1
        elif not interactive or not sys.stdin.isatty():
            value = default if default is not None else ""
        else:
            prompt_def = f" [{default}]" if default else ""
            prompt_str = f"Enter value for {c_yellow(f'<{name}>')}{prompt_def}: "
            try:
                user_input = input(prompt_str).strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{c_yellow('Operation cancelled.')}")
                sys.exit(130)

            if user_input:
                value = user_input
            elif default is not None:
                value = default
            else:
                value = ""

        resolved = resolved.replace(raw, value or "", 1)

    # Any remaining positional args can be appended to the command
    if pos_idx < len(positional_args):
        remaining = " ".join(positional_args[pos_idx:])
        resolved = f"{resolved} {remaining}"

    return resolved


def copy_to_clipboard(text: str) -> Tuple[bool, str]:
    """Copy text to clipboard using platform utilities."""
    tools = [
        ("termux-clipboard-set", ["termux-clipboard-set"]),
        ("wl-copy", ["wl-copy"]),
        ("xclip", ["xclip", "-selection", "clipboard"]),
        ("xsel", ["xsel", "--clipboard", "--input"]),
        ("pbcopy", ["pbcopy"]),
        ("clip.exe", ["clip.exe"]),
    ]

    for name, cmd in tools:
        if shutil.which(name):
            try:
                subprocess.run(
                    cmd,
                    input=text.encode("utf-8"),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"Copied to clipboard via {name}."
            except Exception:
                continue

    return False, "No clipboard utility found (install xclip, wl-clipboard, or termux-api)."


# ==============================================================================
# Formatted Table View & Helpers
# ==============================================================================

def render_table(rows: List[Tuple[str, str, str, str, str]]) -> None:
    """Render a clean, aligned ANSI table responsive to terminal width."""
    if not rows:
        return

    term_width = shutil.get_terminal_size((80, 24)).columns
    headers = ("#", "KEY", "COMMAND", "TAGS", "RUNS")

    # Column widths calculation
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], Color.visible_len(val))

    # Available width for command (index 2)
    other_widths = col_widths[0] + col_widths[1] + col_widths[3] + col_widths[4] + 12
    max_cmd_width = max(20, term_width - other_widths)

    header_line = (
        f"{c_bold(headers[0].ljust(col_widths[0]))}  "
        f"{c_bold(headers[1].ljust(col_widths[1]))}  "
        f"{c_bold(headers[2].ljust(min(col_widths[2], max_cmd_width)))}  "
        f"{c_bold(headers[3].ljust(col_widths[3]))}  "
        f"{c_bold(headers[4].rjust(col_widths[4]))}"
    )

    sep_len = min(term_width, sum(col_widths) + 10)
    divider = c_dim("─" * max(40, sep_len))

    print(divider)
    print(header_line)
    print(divider)

    for row in rows:
        num, key, cmd_str, tags_str, runs = row
        cmd_visible = Color.visible_len(cmd_str)
        if cmd_visible > max_cmd_width:
            cmd_display = cmd_str[: max_cmd_width - 3] + "..."
        else:
            cmd_display = cmd_str

        pad_cmd = " " * max(0, min(col_widths[2], max_cmd_width) - Color.visible_len(cmd_display))
        pad_num = " " * max(0, col_widths[0] - Color.visible_len(num))
        pad_key = " " * max(0, col_widths[1] - Color.visible_len(key))
        pad_tags = " " * max(0, col_widths[3] - Color.visible_len(tags_str))
        pad_runs = " " * max(0, col_widths[4] - Color.visible_len(runs))

        print(f"{num}{pad_num}  {key}{pad_key}  {cmd_display}{pad_cmd}  {tags_str}{pad_tags}  {pad_runs}{runs}")

    print(divider)


# ==============================================================================
# Command Actions
# ==============================================================================

def cmd_save(
    storage: Storage,
    key: Optional[str],
    command: Optional[str],
    description: str = "",
    tags: Optional[List[str]] = None,
    overwrite: bool = False,
) -> None:
    data = storage.load()
    interactive = False

    if not key:
        interactive = True
        try:
            key = input(c_bold("Enter key/shortcut: ")).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c_yellow('Cancelled.')}")
            return

    if not key:
        print(c_red("Error: Key cannot be empty."))
        return

    if key in data and not overwrite:
        print(f"Key {c_key(key)} already exists: {c_dim(data[key]['command'])}")
        try:
            confirm = input(f"Overwrite? ({c_bold('y')}/{c_bold('N')}): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c_yellow('Cancelled.')}")
            return
        if confirm != "y":
            print(c_yellow("Cancelled."))
            return

    if not command:
        interactive = True
        try:
            command = input(c_bold("Enter command: ")).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c_yellow('Cancelled.')}")
            return

    if not command:
        print(c_red("Error: Command cannot be empty."))
        return

    if interactive and not description and sys.stdin.isatty():
        try:
            desc_in = input(c_dim("Optional description (press Enter to skip): ")).strip()
            if desc_in:
                description = desc_in
        except (KeyboardInterrupt, EOFError):
            pass

    if interactive and tags is None and sys.stdin.isatty():
        try:
            tags_in = input(c_dim("Optional tags comma-separated (e.g. docker,ops): ")).strip()
            if tags_in:
                tags = [t.strip() for t in tags_in.split(",") if t.strip()]
        except (KeyboardInterrupt, EOFError):
            pass

    existing = data.get(key, {})
    data[key] = {
        "command": command,
        "description": description or existing.get("description", ""),
        "tags": [t.strip() for t in tags] if tags is not None else existing.get("tags", []),
        "usage_count": existing.get("usage_count", 0),
        "last_used": existing.get("last_used"),
        "created_at": existing.get("created_at", datetime.datetime.now().isoformat()),
    }

    storage.save(data)
    print(f"{c_green('✔ Saved')} {c_key(key)} -> {c_cmd(command)}")


def cmd_run(
    storage: Storage,
    key: Optional[str],
    extra_args: List[str],
    yes: bool = False,
    dry_run: bool = False,
    copy: bool = False,
    print_only: bool = False,
) -> None:
    data = storage.load()
    if not data:
        print(c_yellow("No saved commands found. Use 'kn save' to add one."))
        return

    # Extract any flags that might have been collected into extra_args
    clean_args: List[str] = []
    for a in extra_args:
        if a in ("-y", "--yes"):
            yes = True
        elif a in ("-n", "--dry-run"):
            dry_run = True
        elif a in ("-c", "--copy"):
            copy = True
        elif a in ("-p", "--print"):
            print_only = True
        else:
            clean_args.append(a)
    extra_args = clean_args

    if not key:
        key = select_interactive(data, prompt_text="Select a command to run:")
        if not key:
            return

    if key not in data:
        # Check partial or case-insensitive match
        matches = [k for k in data if k.lower() == key.lower()]
        if matches:
            key = matches[0]
        else:
            print(c_red(f"Error: Key '{key}' not found."))
            cmd_find(storage, key)
            return

    entry = data[key]
    raw_cmd = entry["command"]
    is_interactive = not (yes or dry_run or print_only)
    resolved_cmd = resolve_placeholders(raw_cmd, extra_args, interactive=is_interactive)

    if print_only:
        print(resolved_cmd)
        return

    if copy:
        ok, msg = copy_to_clipboard(resolved_cmd)
        if ok:
            print(f"{c_green('✔')} {msg}")
            print(f"{c_dim('Command:')} {c_cmd(resolved_cmd)}")
        else:
            print(c_yellow(msg))
        return

    print(f"\n{c_bold('Key:')}     {c_key(key)}")
    if entry.get("description"):
        print(f"{c_bold('Info:')}    {c_dim(entry['description'])}")
    print(f"{c_bold('Command:')} {c_green(resolved_cmd)}")

    if dry_run:
        print(f"\n{c_yellow('Dry-run complete. Command was not executed.')}")
        return

    if not yes and sys.stdin.isatty():
        try:
            confirm = input(f"\nPress {c_bold('Enter')} to run, or {c_bold('n')} to cancel: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c_yellow('Cancelled.')}")
            return
        if confirm == "n":
            print(c_yellow("Cancelled."))
            return

    # Update usage metadata
    entry["usage_count"] = entry.get("usage_count", 0) + 1
    entry["last_used"] = datetime.datetime.now().isoformat()
    data[key] = entry
    storage.save(data)

    print()
    try:
        if resolved_cmd.startswith("cd ") and " && " not in resolved_cmd and " || " not in resolved_cmd:
            target_dir = os.path.expanduser(resolved_cmd[3:].strip().strip('"').strip("'"))
            if os.path.isdir(target_dir):
                os.chdir(target_dir)
                shell = os.environ.get("SHELL", "/bin/bash" if platform.system() != "Windows" else "powershell")
                print(c_dim(f"Opening subshell in {target_dir} (exit to return)..."))
                subprocess.run([shell])
            else:
                print(c_red(f"Directory not found: {target_dir}"))
        else:
            subprocess.run(resolved_cmd, shell=True, check=False)
    except Exception as e:
        print(c_red(f"Execution failed: {e}"))


def cmd_list(
    storage: Storage,
    tag_filter: Optional[str] = None,
    sort_by: str = "name",
    quiet: bool = False,
) -> None:
    data = storage.load()
    if not data:
        if not quiet:
            print(c_yellow("No saved commands found. Run 'kn save' to add one."))
        return

    items = list(data.items())

    if tag_filter:
        tag_lower = tag_filter.strip().lower()
        items = [
            (k, v) for k, v in items
            if any(tag_lower == t.lower() for t in v.get("tags", []))
        ]
        if not items:
            print(c_yellow(f"No commands found with tag '{tag_filter}'."))
            return

    # Sorting
    if sort_by == "recent":
        items.sort(key=lambda x: x[1].get("last_used") or "", reverse=True)
    elif sort_by == "popular":
        items.sort(key=lambda x: x[1].get("usage_count", 0), reverse=True)
    else:  # name
        items.sort(key=lambda x: x[0].lower())

    if quiet:
        for k, _ in items:
            print(k)
        return

    rows: List[Tuple[str, str, str, str, str]] = []
    for idx, (k, v) in enumerate(items, 1):
        num_str = c_dim(str(idx))
        key_str = c_key(k)
        cmd_str = v.get("command", "")
        tags_list = v.get("tags", [])
        tags_str = " ".join(c_tag(t) for t in tags_list) if tags_list else ""
        runs_str = c_dim(str(v.get("usage_count", 0)))
        rows.append((num_str, key_str, cmd_str, tags_str, runs_str))

    render_table(rows)
    print(c_dim(f"Total: {len(items)} command(s) | Storage: {storage.file_path}"))


def cmd_find(storage: Storage, keyword: Optional[str]) -> None:
    data = storage.load()
    if not data:
        print(c_yellow("No saved commands found."))
        return

    if not keyword:
        try:
            keyword = input(c_bold("Enter search term: ")).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c_yellow('Cancelled.')}")
            return

    if not keyword:
        return

    kw = keyword.lower()
    matches: List[Tuple[str, Dict[str, Any]]] = []

    for k, v in data.items():
        cmd = v.get("command", "").lower()
        desc = v.get("description", "").lower()
        tags = [t.lower() for t in v.get("tags", [])]

        if kw in k.lower() or kw in cmd or kw in desc or any(kw in t for t in tags):
            matches.append((k, v))

    if not matches:
        print(c_yellow(f"No matches found for '{keyword}'."))
        return

    print(f"\n{c_bold('Found')} {c_green(str(len(matches)))} {c_bold('match(es) for')} '{c_yellow(keyword)}':\n")
    for k, v in matches:
        # Highlight match
        hl_key = re.sub(f"({re.escape(keyword)})", lambda m: c_yellow(m.group(1)), k, flags=re.IGNORECASE)
        hl_cmd = re.sub(f"({re.escape(keyword)})", lambda m: c_yellow(m.group(1)), v.get("command", ""), flags=re.IGNORECASE)
        print(f"  • {c_bold(hl_key)}")
        print(f"    {c_dim('Command:')} {hl_cmd}")
        if v.get("description"):
            print(f"    {c_dim('Info:')}    {v['description']}")
        if v.get("tags"):
            print(f"    {c_dim('Tags:')}    {' '.join(c_tag(t) for t in v['tags'])}")
        print()


def cmd_load(storage: Storage, key: Optional[str]) -> None:
    data = storage.load()
    if not key:
        key = select_interactive(data, prompt_text="Select a command to inspect:")
        if not key:
            return

    if key not in data:
        print(c_red(f"Error: Key '{key}' not found."))
        return

    v = data[key]
    print(f"\n{c_bold('Key:')}         {c_key(key)}")
    print(f"{c_bold('Command:')}     {c_cmd(v.get('command', ''))}")
    if v.get("description"):
        print(f"{c_bold('Description:')} {v['description']}")
    if v.get("tags"):
        print(f"{c_bold('Tags:')}        {' '.join(c_tag(t) for t in v['tags'])}")
    print(f"{c_bold('Runs:')}        {v.get('usage_count', 0)}")
    if v.get("last_used"):
        print(f"{c_bold('Last Used:')}   {v['last_used']}")
    if v.get("created_at"):
        print(f"{c_bold('Created:')}     {v['created_at']}")
    print()


def cmd_delete(storage: Storage, key: Optional[str], yes: bool = False) -> None:
    data = storage.load()
    if not key:
        key = select_interactive(data, prompt_text="Select a command to delete:")
        if not key:
            return

    if key not in data:
        print(c_red(f"Error: Key '{key}' not found."))
        return

    if not yes:
        if not sys.stdin.isatty():
            print(c_red("Error: Deletion requires -y/--yes in non-interactive mode."))
            return
        try:
            confirm = input(f"Delete {c_key(key)}? ({c_bold('y')}/{c_bold('N')}): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c_yellow('Cancelled.')}")
            return
        if confirm != "y":
            print(c_yellow("Cancelled."))
            return

    del data[key]
    storage.save(data)
    print(f"{c_green('✔ Deleted')} '{key}'.")


def cmd_copy(storage: Storage, key: Optional[str], extra_args: List[str]) -> None:
    cmd_run(storage, key, extra_args, copy=True)


def cmd_export(storage: Storage, target_file: Optional[str]) -> None:
    data = storage.load()
    if not target_file:
        target_file = f"keynote_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    out_path = Path(target_file).expanduser().resolve()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"{c_green('✔ Exported')} {len(data)} command(s) to {out_path}")


def cmd_import(storage: Storage, source_file: str, overwrite: bool = False) -> None:
    in_path = Path(source_file).expanduser().resolve()
    if not in_path.exists():
        print(c_red(f"Error: File not found: {in_path}"))
        return

    try:
        with open(in_path, "r", encoding="utf-8") as f:
            new_data = json.load(f)
    except Exception as e:
        print(c_red(f"Failed to parse JSON: {e}"))
        return

    existing = storage.load()
    count = 0

    for k, v in new_data.items():
        if k in existing and not overwrite:
            continue
        if isinstance(v, str):
            existing[k] = {
                "command": v,
                "description": "",
                "tags": [],
                "usage_count": 0,
                "last_used": None,
                "created_at": datetime.datetime.now().isoformat(),
            }
        elif isinstance(v, dict):
            existing[k] = v
        count += 1

    storage.save(existing)
    print(f"{c_green('✔ Imported')} {count} command(s) into Keynote.")


def cmd_completion(shell: str) -> None:
    """Print shell completion script."""
    if shell.lower() == "bash":
        print("""
# Keynote Bash completion
_kn_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="save run list find load delete copy export import help"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
        return 0
    fi

    case "${prev}" in
        run|r|load|l|show|delete|d|rm|copy|c)
            local keys
            keys=$(kn list -q 2>/dev/null)
            COMPREPLY=( $(compgen -W "${keys}" -- "${cur}") )
            return 0
            ;;
        *)
            ;;
    esac
}
complete -F _kn_completion kn keynote
""")
    elif shell.lower() == "zsh":
        print("""
# Keynote Zsh completion
#compdef kn keynote

_kn() {
    local -a commands
    commands=(
        'save:Save a command under a key'
        'run:Execute a saved command'
        'list:List all saved commands'
        'find:Search saved commands'
        'load:Show command details'
        'delete:Remove a command'
        'copy:Copy command to clipboard'
        'export:Export all commands to JSON'
        'import:Import commands from JSON'
    )

    if (( CURRENT == 2 )); then
        _describe 'command' commands
    elif (( CURRENT == 3 )); then
        case "$words[2]" in
            run|r|load|l|delete|d|copy|c)
                local -a keys
                keys=(${(f)"$(kn list -q 2>/dev/null)"})
                _values 'keys' $keys
                ;;
        esac
    fi
}
_kn
""")
    else:
        print(f"Supported shells: bash, zsh")


def select_interactive(data: Dict[str, Dict[str, Any]], prompt_text: str = "Select a command:") -> Optional[str]:
    """Simple interactive selector when running on a TTY."""
    if not data or not sys.stdin.isatty():
        return None

    keys = sorted(data.keys())
    print(f"\n{c_bold(prompt_text)}\n")
    for idx, k in enumerate(keys, 1):
        cmd_preview = data[k]["command"]
        if len(cmd_preview) > 50:
            cmd_preview = cmd_preview[:47] + "..."
        print(f"  {c_dim(f'[{idx}]')} {c_key(k)} {c_dim('→')} {c_dim(cmd_preview)}")

    print()
    try:
        choice = input(f"Enter number (1-{len(keys)}) or name: ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{c_yellow('Cancelled.')}")
        return None

    if not choice:
        return None

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(keys):
            return keys[idx - 1]

    if choice in data:
        return choice

    # Partial match
    matches = [k for k in keys if choice.lower() in k.lower()]
    if len(matches) == 1:
        return matches[0]

    print(c_red(f"Invalid selection: '{choice}'"))
    return None


# ==============================================================================
# CLI Argument Parser & Entrypoint
# ==============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kn",
        description="Keynote - Fast & modern terminal command manager.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kn save deploy "docker-compose up -d --build" -t docker,prod
  kn run deploy
  kn save git-commit "git commit -m '<msg>'"
  kn run git-commit "Initial commit"
  kn list --sort popular
  kn find docker
  kn copy deploy
""",
    )
    parser.add_argument("-v", "--version", action="version", version=f"Keynote v{VERSION}")

    subparsers = parser.add_subparsers(dest="subcommand", title="Subcommands", metavar="<command>")

    # SAVE
    p_save = subparsers.add_parser("save", aliases=["s"], help="Save a command snippet")
    p_save.add_argument("key", nargs="?", default=None, help="Unique name/key for snippet")
    p_save.add_argument("command", nargs="?", default=None, help="The command line string")
    p_save.add_argument("-d", "--desc", default="", help="Description of the command")
    p_save.add_argument("-t", "--tags", nargs="+", default=None, help="Tags (e.g. -t git dev)")
    p_save.add_argument("-f", "--force", action="store_true", help="Overwrite existing key without prompt")

    # RUN
    p_run = subparsers.add_parser("run", aliases=["r"], help="Run a saved command")
    p_run.add_argument("key", nargs="?", default=None, help="Key of the command to run")
    p_run.add_argument("extra_args", nargs="*", help="Arguments or placeholder values")
    p_run.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    p_run.add_argument("-n", "--dry-run", action="store_true", help="Print command without executing")
    p_run.add_argument("-c", "--copy", action="store_true", help="Copy command to clipboard instead of running")
    p_run.add_argument("-p", "--print", action="store_true", help="Print pure command string (useful for eval)")

    # LIST
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List saved commands")
    p_list.add_argument("-t", "--tag", default=None, help="Filter entries by tag")
    p_list.add_argument("-s", "--sort", choices=["name", "recent", "popular"], default="name", help="Sort order")
    p_list.add_argument("-q", "--quiet", action="store_true", help="Output only keys (useful for scripting)")

    # FIND
    p_find = subparsers.add_parser("find", aliases=["f"], help="Search entries by keyword")
    p_find.add_argument("keyword", nargs="?", default=None, help="Keyword to search in keys, commands, tags")

    # LOAD / SHOW
    p_load = subparsers.add_parser("load", aliases=["l", "show"], help="Show full details of a saved command")
    p_load.add_argument("key", nargs="?", default=None, help="Key of the command to inspect")

    # DELETE
    p_del = subparsers.add_parser("delete", aliases=["d", "rm"], help="Delete a saved command")
    p_del.add_argument("key", nargs="?", default=None, help="Key of the command to delete")
    p_del.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    # COPY
    p_copy = subparsers.add_parser("copy", aliases=["c"], help="Copy a command to the clipboard")
    p_copy.add_argument("key", nargs="?", default=None, help="Key of the command to copy")
    p_copy.add_argument("extra_args", nargs="*", help="Arguments or placeholder values")

    # EXPORT
    p_export = subparsers.add_parser("export", help="Export saved commands to a JSON file")
    p_export.add_argument("target", nargs="?", default=None, help="Output JSON filepath")

    # IMPORT
    p_import = subparsers.add_parser("import", help="Import commands from a JSON file")
    p_import.add_argument("source", help="Input JSON filepath")
    p_import.add_argument("-f", "--force", action="store_true", help="Overwrite existing keys on import")

    # COMPLETION
    p_comp = subparsers.add_parser("completion", help="Generate shell auto-completion script")
    p_comp.add_argument("shell", choices=["bash", "zsh"], help="Target shell")

    return parser


def main() -> None:
    Color.init()
    storage = Storage()
    parser = build_parser()

    # Pre-process arguments to handle legacy flag-based aliases like -s, -r, -ls, -f, -d, -l, -h
    argv = sys.argv[1:]
    alias_map = {
        "-s": "save",
        "-r": "run",
        "-ls": "list",
        "-f": "find",
        "-l": "load",
        "-d": "delete",
        "-c": "copy",
        "-h": "--help",
    }
    if argv and argv[0] in alias_map:
        argv[0] = alias_map[argv[0]]

    # If no args provided, show table list followed by interactive prompt
    if not argv:
        data = storage.load()
        if not data:
            parser.print_help()
        else:
            cmd_list(storage)
            print(f"\n{c_dim('Quick-run a command (or press Enter to exit):')}")
            key = select_interactive(data)
            if key:
                cmd_run(storage, key, [], yes=False)
        return

    args = parser.parse_args(argv)

    subcmd = args.subcommand
    if subcmd in ("save", "s"):
        cmd_save(storage, args.key, args.command, description=args.desc, tags=args.tags, overwrite=args.force)
    elif subcmd in ("run", "r"):
        cmd_run(
            storage,
            args.key,
            args.extra_args,
            yes=args.yes,
            dry_run=args.dry_run,
            copy=args.copy,
            print_only=args.print,
        )
    elif subcmd in ("list", "ls"):
        cmd_list(storage, tag_filter=args.tag, sort_by=args.sort, quiet=args.quiet)
    elif subcmd in ("find", "f"):
        cmd_find(storage, args.keyword)
    elif subcmd in ("load", "l", "show"):
        cmd_load(storage, args.key)
    elif subcmd in ("delete", "d", "rm"):
        cmd_delete(storage, args.key, yes=args.yes)
    elif subcmd in ("copy", "c"):
        cmd_copy(storage, args.key, args.extra_args)
    elif subcmd == "export":
        cmd_export(storage, args.target)
    elif subcmd == "import":
        cmd_import(storage, args.source, overwrite=args.force)
    elif subcmd == "completion":
        cmd_completion(args.shell)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
