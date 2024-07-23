import asyncio
from code_analyzer import analyze_codebase
from call_graph import generate_call_graph
from generate_documentation import generate_documentation

async def main_menu():
    print("Welcome to the Codebase Analysis Tool")
    
    while True:
        path = input("Enter the path to the codebase (or 'q' to quit): ")
        if path.lower() == 'q':
            break

        if not os.path.exists(path):
            print(f"Error: The path '{path}' does not exist.")
            continue

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
                await analyze_codebase(path)
            elif choice == '2':
                await generate_call_graph(path)
            elif choice == '3':
                await generate_documentation(path)
            elif choice == '4':
                await analyze_codebase(path)
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
