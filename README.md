# Keynote

**Keynote** is a lightweight command-line tool for saving, organizing, and executing frequently used terminal commands. Built with the Python standard library (zero external dependencies).

Runs on **Linux**, **macOS**, **Termux**, and **Windows**.

---

## Installation

### Via `pipx` (Recommended)
```bash
git clone https://github.com/knightfall-cs/keynote.git
cd keynote
pipx install .
```
This makes `kn` available globally.

### Via Shell Alias (Termux / Lightweight)
```bash
cd ~
git clone https://github.com/knightfall-cs/keynote.git
echo 'alias kn="python3 ~/keynote/keynote.py"' >> ~/.bashrc
source ~/.bashrc
```

---

## Commands

| Command | Alias | Description |
| :--- | :--- | :--- |
| `save [key] [cmd]` | `s` | Save a command (`-d` description, `-t` tags) |
| `run [key] [args...]` | `r` | Run a saved command (`-y` auto-confirm, `-n` dry-run, `-c` copy) |
| `list` | `ls` | Display saved commands table (`-t` filter tag, `-s` sort) |
| `find [term]` | `f` | Search commands, keys, tags, and descriptions |
| `copy [key] [args...]`| `c` | Copy resolved command to clipboard |
| `load [key]` | `l`, `show` | Inspect full details of a saved command |
| `delete [key]` | `d`, `rm` | Delete a command snippet (`-y` skip prompt) |
| `export [file]` | — | Export all commands to JSON |
| `import [file]` | — | Import commands from JSON |
| `completion [shell]`| — | Generate shell autocompletion (`bash` or `zsh`) |

---

## Examples

### 1. Save commands
```bash
# Basic command
kn save update "sudo apt update && sudo apt upgrade -y"

# With tags and description
kn save deploy "docker compose up -d" -t docker prod -d "Start production services"

# With dynamic placeholders
kn save git-commit "git commit -m '<message>'"
kn save docker-logs "docker logs -f <container> --tail <lines:100>"
```

### 2. Run commands
```bash
# Run with confirmation prompt
kn run deploy

# Skip confirmation (-y)
kn run update -y

# Pass placeholder values
kn run git-commit "fix header layout"
kn run docker-logs container=api lines=50

# Preview without running (-n)
kn run deploy -n
```

### 3. List & Search
```bash
# View all saved commands
kn list

# Filter by tag or sort by popularity
kn list -t docker
kn list --sort popular

# Search keyword
kn find docker
```

### 4. Copy to clipboard
```bash
kn copy deploy
kn c git-commit "feat: add user auth"
```

---

## Shell Autocompletion

Enable Tab-completion for command keys:

```bash
# For Bash
echo 'source <(kn completion bash)' >> ~/.bashrc

# For Zsh
echo 'source <(kn completion zsh)' >> ~/.zshrc
```

---

## Configuration

Commands are stored in `~/.config/keynote/kn_data.json` (or `%APPDATA%\keynote\kn_data.json` on Windows).  
Override path with `export KEYNOTE_DATA_FILE="/path/to/custom.json"`.

---

## Author

[**KNIGHTFALL**](https://github.com/knightfall-cs)
