# keynote

Keynote is a simple command-line tool designed to make it easy to manage and run long and complex Linux commands that are hard to remember. With Keynote, you can save, load, and run these commands effortlessly. This tool is especially useful for those working in Linux environments, and it's also compatible with Termux.


## Installation

1. Make sure you have Python and Git installed.
   ```
   apt install git python3
   ```

2. Clone or download this repository to your home directory:
   ```
   cd $HOME
   git clone https://github.com/knightfall-cs/keynote.git
   ```


## Usage

Navigate to the Keynote directory:

```
cd keynote
```

Run Keynote with the desired command:

```
python3 keynote.py [command]
```

### Available Commands

- **`save` / `-s` :** Save a long command for later use.

- **`list` / `-ls` :** List all saved commands.

- **`load` / `-l` :** Load and display a saved command.

- **`run` / `-r` :** Run a previously saved script.

- **`help` / `-h` :** Display available commands.


## Alias for Convenience

For added convenience, you can create an alias to use Keynote more easily. Add the following line to your shell configuration file, depending on your shell of choice:

- **For Bash or Zsh (~/.bashrc or ~/.zshrc):**
  ```
  alias kn="python ~/keynote/keynote.py"
  ```

- **For Termux (../usr/etc/bash.bashrc):**
  ```
  alias kn="python ~/keynote/keynote.py"
  ```

Make sure to restart your shell or run source ~/.bashrc (or the appropriate config file) to apply the alias.

**Once the alias is applied, you can run Keynote from any directory by typing kn followed by the desired command.**
```
kn help
```

## Customization for Termux

If you're using Termux, you can customize your experience with bash.bashrc file even further. Here's how:

- **Check out the [custom `bash.bashrc` file](https://github.com/knightfall-cs/termux-bashrc) on GitHub.**

- **Follow the instructions provided in the repository to customize your `bash.bashrc` file to your liking.**


---

Author: KNIGHTFALL
