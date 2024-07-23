import os
import ast
import json
import subprocess
import logging
from rich.console import Console

console = Console()

# Create necessary directories
os.makedirs('temp', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('docs', exist_ok=True)

# Set up logging
logging.basicConfig(filename='logs/call_graph.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
    
    input_file = 'temp/code2flow_input.json'
    output_file = 'docs/codebase_call_graph.png'
    
    with open(input_file, 'w') as f:
        f.write(code2flow_input)
    
    try:
        subprocess.run(['code2flow', input_file, '-o', output_file, '--language', 'py'], check=True)
        console.print(f"[green]Call graph generated as {output_file}[/green]")
        logging.info(f"Call graph generated successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        error_msg = f"Error: Failed to generate call graph. Error message: {e}"
        console.print(f"[red]{error_msg}[/red]")
        console.print(f"[yellow]Command used: code2flow {input_file} -o {output_file} --language py[/yellow]")
        logging.error(error_msg)
    except FileNotFoundError:
        error_msg = "Error: code2flow not found. Please install it using 'pip install code2flow'."
        console.print(f"[red]{error_msg}[/red]")
        logging.error(error_msg)
    
    # Clean up the temporary input file
    os.remove(input_file)

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_call_graph(input("Enter the path to the codebase: ")))
