# Keynote

**Keynote** is a lightweight command-line tool for saving and running frequently used or complex terminal commands using easy-to-remember keys. Designed for users who want quick access to their custom workflows without memorizing long commands.

It works cross-platform (Linux, macOS, Termux, Windows) and supports structured storage, interactive confirmations, and convenient aliases.

---

## 🛠 Installation

1. Install Python and Git (if not already installed):
   ```bash
   sudo apt install git python3
   ```

2. Clone the repository to your home directory:
   ```bash
   cd $HOME
   git clone https://github.com/knightfall-cs/keynote.git
   ```

---

## 🚀 Usage

Navigate to the project folder:
```bash
cd ~/keynote
```

Run Keynote:
```bash
python3 keynote.py [command]
```

### ✳️ Command Overview

| Command              | Description                                        |
|----------------------|----------------------------------------------------|
| `save` / `-s` / `s`   | Save a key with an associated command (prompts for value) |
| `run` / `-r` / `r`    | Execute the command saved under a key             |
| `list` / `-ls` / `ls` | Show all saved entries                            |
| `load` / `-l` / `l`   | Display the command stored under a specific key   |
| `delete` / `-d` / `d` | Remove a saved entry (with confirmation)          |
| `find` / `-f` / `f`   | Search for a keyword in keys or command content   |
| `help` / `-h` / `h`   | Show usage and available commands                 |

### 🧪 Examples

```bash
# Save a new key
kn save "docker deploy"
# → prompts for the actual command to save

# Run a saved command
kn r docker deploy

# Show all entries
kn list

# Search for keywords
kn f ssh

# Load/display a saved command
kn l docker deploy

# Delete an entry
kn d docker deploy
```

---

## ⚡️ Optional: Add Alias

To use `kn` globally from any folder, add this to your shell config:

### For Bash or Zsh:
```bash
echo 'alias kn="python3 ~/keynote/keynote.py"' >> ~/.bashrc
# or for Zsh:
echo 'alias kn="python3 ~/keynote/keynote.py"' >> ~/.zshrc
source ~/.bashrc  # or
source ~/.zshrc
```

### For Termux:
```bash
echo 'alias kn="python3 ~/keynote/keynote.py"' >> ~/.bashrc
termux-reload-settings
```

Once done, you can run:
```bash
kn save update
```

---

## 📁 Termux Customization

Looking to enhance your Termux terminal experience?  
Check out: [termux-bashrc by knightfall-cs](https://github.com/knightfall-cs/termux-bashrc)

---

## 👤 Author

**KNIGHTFALL**  
[GitHub: knightfall-cs](https://github.com/knightfall-cs)
