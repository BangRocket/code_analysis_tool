import ast
import os
import networkx as nx
from graphviz import Digraph

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
    calls = extract_calls(tree)
    
    G = nx.DiGraph()
    for caller, callee in calls:
        G.add_edge(caller, callee)
    
    return G

def visualize_call_graph(G, output_file):
    dot = Digraph(comment='Call Graph')
    dot.attr(rankdir='LR', size='8,5')
    
    for node in G.nodes():
        dot.node(node, shape='box')
    
    for edge in G.edges():
        dot.edge(edge[0], edge[1])
    
    dot.render(output_file, format='png', cleanup=True)

def process_directory(directory):
    combined_graph = nx.DiGraph()
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):  # Adjust this for the file types you want to analyze
                file_path = os.path.join(root, file)
                file_graph = create_call_graph(file_path)
                combined_graph = nx.compose(combined_graph, file_graph)
    
    return combined_graph

import asyncio
from rich.console import Console

console = Console()

async def generate_call_graph(path):
    console.print("[cyan]Generating call graph...[/cyan]")
    graph = process_directory(path)
    visualize_call_graph(graph, "codebase_call_graph")
    console.print("[green]Call graph generated as codebase_call_graph.png[/green]")

if __name__ == "__main__":
    asyncio.run(generate_call_graph(input("Enter the path to the codebase: ")))
