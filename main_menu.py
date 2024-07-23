import argparse
import asyncio
from code_analyzer import analyze_codebase, generate_call_graph, generate_documentation

async def main_menu():
    parser = argparse.ArgumentParser(description="Codebase Analysis Tool")
    parser.add_argument("path", help="Path to the codebase")
    args = parser.parse_args()

    while True:
        print("\nMain Menu:")
        print("1. Analyze Codebase")
        print("2. Generate Call Graph")
        print("3. Generate Documentation")
        print("4. Perform All Steps")
        print("5. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            await analyze_codebase(args.path)
        elif choice == '2':
            await generate_call_graph(args.path)
        elif choice == '3':
            await generate_documentation(args.path)
        elif choice == '4':
            await analyze_codebase(args.path)
            await generate_call_graph(args.path)
            await generate_documentation(args.path)
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main_menu())
