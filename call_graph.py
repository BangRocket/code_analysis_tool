import os
import ast
import json
import subprocess
from rich.console import Console

console = Console()

def parse_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return ast.parse(content)

def extract_calls(node, current_function=None):
    calls = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef):
            calls.extend(extract_calls(child, child.name))
        elif isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                if current_function:
                    calls.append((current_function, child.func.id))
        elif isinstance(child, ast.ClassDef):
            calls.extend(extract_calls(child, child.name))
    return calls

def create_call_graph(file_path):
    tree = parse_file(file_path)
    return extract_calls(tree)

def process_directory(directory):
    combined_calls = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_calls = create_call_graph(file_path)
                combined_calls.extend(file_calls)
    
    return combined_calls

def generate_code2flow_input(calls):
    code2flow_input = {}
    for caller, callee in calls:
        if caller not in code2flow_input:
            code2flow_input[caller] = []
        code2flow_input[caller].append(callee)
    return json.dumps(code2flow_input)

async def generate_call_graph(path):
    console.print("[cyan]Generating call graph...[/cyan]")
    calls = process_directory(path)
    code2flow_input = generate_code2flow_input(calls)
    
    with open('code2flow_input.json', 'w') as f:
        f.write(code2flow_input)
    
    try:
        subprocess.run(['code2flow', 'code2flow_input.json', '-o', 'codebase_call_graph.png', '--language', 'python'], check=True)
        console.print("[green]Call graph generated as codebase_call_graph.png[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error: Failed to generate call graph. Error message: {e}[/red]")
    except FileNotFoundError:
        console.print("[red]Error: code2flow not found. Please install it using 'pip install code2flow'.[/red]")
    
    # Clean up the temporary input file
    os.remove('code2flow_input.json')

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_call_graph(input("Enter the path to the codebase: ")))
