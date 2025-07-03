import os
import sys
import json
import platform
import subprocess

KEYNOTE_DIR = os.path.join(os.path.expanduser("~"), "keynote")
SAVED_DATA = os.path.join(KEYNOTE_DIR, "kn_data.json")
os.makedirs(KEYNOTE_DIR, exist_ok=True)

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def open_shell():
    if platform.system() == "Windows":
        os.system("powershell")
    else:
        os.system(os.environ.get("SHELL", "/bin/bash"))

def run_script(data, key):
    if key not in data:
        print("Key not found.")
        return
    script = data[key]
    print(f"\nScript for '{key}': {script}")
    confirm = input("Press Enter to run, or type 'n' to cancel: ").strip().lower()
    if confirm == "n":
        print("Cancelled.")
        return
    try:
        if script.startswith("cd ") and " && " not in script:
            os.chdir(script[3:].strip())
            open_shell()
        else:
            subprocess.run(script, shell=True)
    except Exception as e:
        print(f"Error: {e}")

def find_data(data, keyword):
    keyword = keyword.strip().lower()
    results = {
        k: v for k, v in data.items()
        if keyword in k.lower() or keyword in v.lower()
    }
    if results:
        print(f"\nResults for '{keyword}':")
        for k, v in results.items():
            print(f"{k}: {v}")
    else:
        print("No matches found.")

def show_help():
    print("""
Commands:
  save   / -s  / s   >  Save a new command under a key (prompts for value)
  list   / -ls / ls  >  List all saved entries
  delete / -d  / d   >  Delete a saved entry
  load   / -l  / l   >  Show the value stored under a key
  run    / -r  / r   >  Run a saved command
  find   / -f  / f   >  Search entries by word or phrase
  help   / -h  / h   >  Show this help message

Examples:
  kn save "deploy prod"
  kn r deploy prod
  kn f git push
""")

def main():
    if len(sys.argv) < 2:
        print("Usage: python keynote.py [command]")
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]
    data = load(SAVED_DATA)

    if command in ["save", "-s", "s"]:
        key = " ".join(args).strip() if args else input("Enter key to save: ").strip()
        if not key:
            print("Key cannot be empty.")
            return
        if key in data:
            confirm = input(f"'{key}' exists. Overwrite? (y/n): ").lower()
            if confirm != "y":
                print("Cancelled.")
                return
        value = input("Enter command/script: ").strip()
        if not value:
            print("Value cannot be empty.")
            return
        data[key] = value
        save(SAVED_DATA, data)
        print(f"Saved: {key}")

    elif command in ["list", "-ls", "ls"]:
        if not data:
            print("No saved data.")
        else:
            print("\nSaved entries:\n")
            for k, v in data.items():
                print(f"{k}: {v}\n")

    elif command in ["delete", "-d", "d"]:
        key = " ".join(args).strip() if args else input("Enter key to delete: ").strip()
        if key in data:
            confirm = input(f"Delete '{key}'? (y/n): ").lower()
            if confirm == "y":
                del data[key]
                save(SAVED_DATA, data)
                print("Deleted.")
            else:
                print("Cancelled.")
        else:
            print("Key not found.")

    elif command in ["load", "-l", "l"]:
        key = " ".join(args).strip() if args else input("Enter key to load: ").strip()
        print(data.get(key, "Key not found."))

    elif command in ["run", "-r", "r"]:
        key = " ".join(args).strip() if args else input("Enter key to run: ").strip()
        run_script(data, key)

    elif command in ["find", "-f", "f"]:
        keyword = " ".join(args).strip() if args else input("Enter keyword: ").strip()
        find_data(data, keyword)

    elif command in ["help", "-h", "h"]:
        show_help()

    else:
        print("Unknown command. Use 'help' to view options.")

if __name__ == "__main__":
    main()
