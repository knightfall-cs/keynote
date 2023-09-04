import sys
import json
import subprocess
import os

# File to store data
SAVED_DATA = os.path.join(os.path.expanduser("~"), "keynote", "kn_data.json")

# Function to save data to a file
def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# Function to load data from a file
def load(file):
    try:
        with open(file, "r") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        return {}

# Function to run a stored script
def run(data, key):
    if key in data:
        script_to_run = data[key]
        print(f"Function: {script_to_run}")
        choice = input("Do you want to run it? (y/n): ").lower()
        if choice == "y":
            try:
                subprocess.run([script_to_run], shell=True)
            except Exception as e:
                print(f"Error running the script: {e}")
    else:
        print("Key does not exist.")

# Main program
if len(sys.argv) == 2:
    command = sys.argv[1]
    data = load(SAVED_DATA)

    if command == "save" or command == "-s":
        key = input("Enter the key to save: ")
        data[key] = input("Enter data: ")
        save(SAVED_DATA, data)
        print("Data saved!")

    elif command == "list" or command == "-ls":
        print("Saved data:")
        for key, value in data.items():
            print(f"{key}: {value}\n")
        
    elif command == "delete" or command == "-d":
        key = input("Enter the key to delete: ")
        if key in data:
            del data[key]
            save(SAVED_DATA, data)
            print("Data deleted!")
        else:
            print("Key does not exist.")

    elif command == "help" or command == "-h":
      print("Available commands:")
      print("  save   / -s  > Save data to a key")
      print("  list   / -ls > List all saved data")
      print("  delete / -d  > Delete a key and its data")
      print("  load   / -l  > Load and display data")
      print("  run    / -r  > Run a stored script")
      print("  help   / -h  > Display this help message")
        
    elif command == "load" or command == "-l":
        key = input("Enter the key to load: ")
        if key in data:
            print(data[key])
        else:
            print("Key does not exist.")

    elif command == "run" or command == "-r":
        key = input("Enter the key of the script to run: ")
        run(data, key)
        
    else:
      print("Unknown command.")
      sys.exit(1)

else:
    print("Usage: python keynote.py [command]")