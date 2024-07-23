import asyncio
import code_analyzer
from call_graph import generate_call_graph
from generate_documentation import generate_documentation
import os
import json

LAST_PATH_FILE = 'last_path.json'

def save_last_path(path):
    with open(LAST_PATH_FILE, 'w') as f:
        json.dump({'last_path': path}, f)

def load_last_path():
    try:
        with open(LAST_PATH_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_path', '')
    except FileNotFoundError:
        return ''

async def main_menu():
    print("Welcome to the Codebase Analysis Tool")
    
    while True:
        last_path = load_last_path()
        if last_path:
            path = input(f"Enter the path to the codebase (or press Enter to use last path: {last_path}, or 'q' to quit): ")
            if path == '':
                path = last_path
        else:
            path = input("Enter the path to the codebase (or 'q' to quit): ")
        
        if path.lower() == 'q':
            break

        if not os.path.exists(path):
            print(f"Error: The path '{path}' does not exist.")
            continue

        save_last_path(path)

        while True:
            print("\nMain Menu:")
            print("1. Analyze Codebase")
            print("2. Generate Call Graph")
            print("3. Generate Documentation")
            print("4. Perform All Steps")
            print("5. Return to Path Selection")
            print("6. Exit")
            
            choice = input("Enter your choice: ")

            if choice == '1':
                await code_analyzer.analyze_codebase(path)
            elif choice == '2':
                await generate_call_graph(path)
            elif choice == '3':
                await generate_documentation(path)
            elif choice == '4':
                await code_analyzer.analyze_codebase(path)
                await generate_call_graph(path)
                await generate_documentation(path)
            elif choice == '5':
                break
            elif choice == '6':
                return
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main_menu())
