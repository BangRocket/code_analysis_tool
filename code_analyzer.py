import os
import argparse
import aiohttp
import asyncio
import json
import hashlib
from collections import Counter
from dotenv import load_dotenv
from aiolimiter import AsyncLimiter
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.tree import Tree
from rich.live import Live
from rich.markdown import Markdown
import networkx as nx
import matplotlib.pyplot as plt
import ast
import re
from collections import defaultdict
from call_graph import process_directory, visualize_call_graph
from generate_documentation import generate_documentation

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
CALLS_PER_MINUTE = 5
MAX_CONCURRENT_CALLS = 5
CACHE_FILE = "analysis_cache.json"

console = Console()
rate_limiter = AsyncLimiter(CALLS_PER_MINUTE, 60)
semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)

# Graph to store code relationships
code_graph = nx.DiGraph()

def extract_imports_and_functions(content, file_path):
    try:
        tree = ast.parse(content)
        imports = []
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for n in node.names:
                    imports.append(f"{module}.{n.name}")
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        
        return imports, functions, classes
    except SyntaxError:
        # If it's not a Python file, use regex to extract potential functions and classes
        function_pattern = r'(?:def|function)\s+(\w+)'
        class_pattern = r'class\s+(\w+)'
        import_pattern = r'(?:import|from)\s+(\w+)'
        
        functions = re.findall(function_pattern, content)
        classes = re.findall(class_pattern, content)
        imports = re.findall(import_pattern, content)
        
        return imports, functions, classes

async def generate_call_graph(codebase_path):
    console.print("[cyan]Generating call graph...[/cyan]")
    graph = process_directory(codebase_path)
    visualize_call_graph(graph, "codebase_call_graph")
    console.print("[green]Call graph generated as codebase_call_graph.png[/green]")
    return graph

def generate_codebase_graph(code_graph):
    plt.figure(figsize=(20, 20))
    pos = nx.spring_layout(code_graph, k=0.5, iterations=50)
    
    # Separate nodes by type
    file_nodes = [node for node, data in code_graph.nodes(data=True) if data.get('type') == 'file']
    function_nodes = [node for node, data in code_graph.nodes(data=True) if data.get('type') == 'function']
    class_nodes = [node for node, data in code_graph.nodes(data=True) if data.get('type') == 'class']
    import_nodes = [node for node, data in code_graph.nodes(data=True) if data.get('type') == 'import']

    # Draw nodes
    nx.draw_networkx_nodes(code_graph, pos, nodelist=file_nodes, node_color='lightblue', node_size=300, alpha=0.8)
    nx.draw_networkx_nodes(code_graph, pos, nodelist=function_nodes, node_color='lightgreen', node_size=200, alpha=0.8)
    nx.draw_networkx_nodes(code_graph, pos, nodelist=class_nodes, node_color='lightcoral', node_size=250, alpha=0.8)
    nx.draw_networkx_nodes(code_graph, pos, nodelist=import_nodes, node_color='lightyellow', node_size=150, alpha=0.8)

    # Draw edges
    nx.draw_networkx_edges(code_graph, pos, alpha=0.5, arrows=True)

    # Add labels
    labels = {node: node.split('::')[-1] for node in code_graph.nodes()}
    nx.draw_networkx_labels(code_graph, pos, labels, font_size=8)

    plt.title("Codebase Relationship Graph")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig("codebase_graph.png", dpi=300, bbox_inches='tight')
    plt.close()

def generate_text_summary(code_graph, results):
    summary = "# Codebase Summary\n\n"

    # File types summary
    file_types = Counter(result.get('file_type', 'Unknown') for result in results)
    summary += f"## File Types\nTotal Files: {len(results)}\n"
    for file_type, count in file_types.items():
        summary += f"- {file_type}: {count} files\n"
    summary += "\n"

    # Node types summary
    node_types = defaultdict(int)
    for _, data in code_graph.nodes(data=True):
        node_types[data.get('type', 'Unknown')] += 1
    
    summary += "## Code Elements\n"
    for node_type, count in node_types.items():
        summary += f"- {node_type.capitalize()}s: {count}\n"
    summary += "\n"

    # Most connected files
    file_connections = {node: degree for node, degree in code_graph.degree() 
                        if code_graph.nodes[node].get('type') == 'file'}
    most_connected = sorted(file_connections.items(), key=lambda x: x[1], reverse=True)[:10]
    
    summary += "## Most Connected Files\n"
    for file, connections in most_connected:
        summary += f"- {file}: {connections} connections\n"
    summary += "\n"

    # Most common imports
    imports = [node for node, data in code_graph.nodes(data=True) if data.get('type') == 'import']
    common_imports = Counter(imports).most_common(10)
    
    summary += "## Most Common Imports\n"
    for imp, count in common_imports:
        summary += f"- {imp}: used in {count} files\n"
    summary += "\n"

    return summary

def update_graph(file_path, imports, functions, classes):
    code_graph.add_node(file_path, type='file')
    for imp in imports:
        code_graph.add_node(imp, type='import')
        code_graph.add_edge(file_path, imp)
    for func in functions:
        func_node = f"{file_path}::{func}"
        code_graph.add_node(func_node, type='function')
        code_graph.add_edge(file_path, func_node)
    for cls in classes:
        class_node = f"{file_path}::{cls}"
        code_graph.add_node(class_node, type='class')
        code_graph.add_edge(file_path, class_node)

async def analyze_code_file(file_path, content, progress):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    template = """
# File Analysis

## File Type
[file extension] - [Programming language or file type]

## Overall Purpose
[Provide a concise description of the file's main purpose and its role in the project]

## Main Functions
1. **[Function name]** - [Brief description of the function's purpose and key features]
2. **[Function name]** - [Brief description of the function's purpose and key features]
3. **[Function name]** - [Brief description of the function's purpose and key features]
[Continue listing main functions as needed]

## Notable patterns and potential issues
### [Category (e.g., Safety and Input Validation, Error Handling, Memory Management, etc.)]
- [Describe the pattern or issue]
- [Describe another pattern or issue in this category if applicable]

### [Another category]
- [Describe the pattern or issue]
- [Describe another pattern or issue in this category if applicable]
[Continue listing categories and issues as needed]
"""

    async with semaphore:
        async with aiohttp.ClientSession() as session:
            async with rate_limiter:
                data = {
                    "model": "mistralai/mistral-nemo",
                    "messages": [
                        {"role": "system", "content": "You are a code analysis assistant. Analyze the provided code and output your analysis following the given template exactly. Use markdown formatting."},
                        {"role": "user", "content": f"Analyze the following code file:\n\nFile: {file_path}\n\n{content}\n\nUse this template for your response:\n{template}"}
                    ]
                }
                progress.update(progress.task_ids[0], description=f"[cyan]Analyzing {os.path.basename(file_path)}[/cyan]")
                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            if 'choices' in result and len(result['choices']) > 0:
                                return file_path, result['choices'][0]['message']['content']
                            else:
                                console.print(f"[bold red]Unexpected API response structure for {file_path}[/bold red]")
                                console.print(f"[yellow]API response: {result}[/yellow]")
                                return file_path, None
                        else:
                            error_text = await response.text()
                            console.print(f"[bold red]Error: {response.status} - {error_text}[/bold red]")
                            return file_path, None
                except Exception as e:
                    console.print(f"[bold red]Exception during API call for {file_path}: {str(e)}[/bold red]")
                    import traceback
                    console.print(f"[yellow]Traceback: {traceback.format_exc()}[/yellow]")
                    return file_path, None

async def global_analysis(results, progress):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    def create_summary_chunk(chunk_results):
        chunk_summary = "Codebase Chunk Analysis:\n\n"
        file_types = Counter(result.get('file_type', 'Unknown') for result in chunk_results)
        chunk_summary += f"This chunk contains {len(chunk_results)} files:\n"
        for file_type, count in file_types.items():
            chunk_summary += f"- {count} {file_type} files\n"
        
        chunk_summary += "\nFile Details:\n"
        for result in chunk_results:
            chunk_summary += f"- {result['file_path']}:\n"
            analysis = result.get('analysis', '')
            
            purpose = "Purpose not found in analysis"
            purpose_parts = analysis.split('## Overall Purpose')
            if len(purpose_parts) > 1:
                purpose = purpose_parts[1].split('##')[0].strip()
            chunk_summary += f"  Purpose: {purpose}\n"
            
            main_functions = re.findall(r'\*\*(.*?)\*\*', analysis)
            if main_functions:
                chunk_summary += f"  Main Functions: {', '.join(main_functions[:5])}\n"
            else:
                chunk_summary += "  Main Functions: None found in analysis\n"
        
        return chunk_summary

    chunk_size = 50  # Analyze 50 files at a time
    chunks = [results[i:i + chunk_size] for i in range(0, len(results), chunk_size)]
    
    global_analysis_results = []

    for i, chunk in enumerate(chunks):
        chunk_summary = create_summary_chunk(chunk)
        
        template = """
# Chunk Analysis

## Key Observations
[List the key observations about this chunk of the codebase]

## Common Patterns and Practices
[List and briefly describe any common coding patterns, practices, or conventions observed in this chunk]

## Potential Improvements
[Suggest potential areas for improvement in this chunk of the codebase]

## Notable Strengths
[Highlight any particularly strong aspects of this chunk of the codebase]
"""

        async with semaphore:
            async with aiohttp.ClientSession() as session:
                async with rate_limiter:
                    data = {
                        "model": "mistralai/mistral-nemo",
                        "messages": [
                            {"role": "system", "content": "You are a code analysis assistant specializing in analyzing codebases. Analyze the provided chunk summary and output your analysis following the given template exactly. Use markdown formatting."},
                            {"role": "user", "content": f"Analyze the following codebase chunk:\n\n{chunk_summary}\n\nUse this template for your response:\n{template}"}
                        ]
                    }
                    progress.update(progress.task_ids[0], description=f"[cyan]Performing global analysis (Chunk {i+1}/{len(chunks)})[/cyan]")
                    try:
                        async with session.post(url, headers=headers, json=data) as response:
                            if response.status == 200:
                                result = await response.json()
                                if 'choices' in result and len(result['choices']) > 0:
                                    global_analysis_results.append(result['choices'][0]['message']['content'])
                                else:
                                    console.print(f"[bold red]Unexpected API response structure in global analysis chunk {i+1}[/bold red]")
                                    console.print(f"[yellow]API response: {result}[/yellow]")
                                    global_analysis_results.append(f"Analysis failed for chunk {i+1} due to unexpected API response structure.")
                            else:
                                error_text = await response.text()
                                console.print(f"[bold red]Error in global analysis chunk {i+1}: {response.status} - {error_text}[/bold red]")
                                global_analysis_results.append(f"Analysis failed for chunk {i+1} due to API error: {response.status} - {error_text}")
                    except Exception as e:
                        console.print(f"[bold red]Exception during global analysis chunk {i+1}: {str(e)}[/bold red]")
                        import traceback
                        console.print(f"[yellow]Traceback: {traceback.format_exc()}[/yellow]")
                        global_analysis_results.append(f"Analysis failed for chunk {i+1} due to exception: {str(e)}")

    # Combine all chunk analyses
    combined_analysis = "# Global Codebase Analysis\n\n"
    for i, analysis in enumerate(global_analysis_results):
        combined_analysis += f"## Chunk {i+1} Analysis\n\n{analysis}\n\n"

    # Add a final summary section
    combined_analysis += "\n# Overall Summary\n\n"
    combined_analysis += f"Total Files Analyzed: {len(results)}\n"
    file_types = Counter(result.get('file_type', 'Unknown') for result in results)
    for file_type, count in file_types.items():
        combined_analysis += f"- {count} {file_type} files\n"

    return combined_analysis
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try:
                cache = json.load(f)
                # Validate cache structure
                for key, value in list(cache.items()):
                    if not isinstance(value, dict) or 'hash' not in value or 'analysis' not in value:
                        console.print(f"[yellow]Warning: Invalid cache entry for {key}. It will be regenerated.[/yellow]")
                        del cache[key]
                return cache
            except json.JSONDecodeError:
                console.print("[yellow]Warning: Cache file is corrupted. It will be regenerated.[/yellow]")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        console.print(f"[bold red]Error saving cache: {str(e)}[/bold red]")

def file_hash(content):
    return hashlib.md5(content.encode()).hexdigest()

def parse_analysis_result(analysis):
    lines = analysis.split('\n')
    file_type = ''
    for line in lines:
        if line.startswith('## File Type'):
            file_type = lines[lines.index(line) + 1].strip()
            break
    return {
        "file_type": file_type,
        "analysis": analysis
    }

def read_file_safely(file_path):
    encodings = ['utf-8', 'latin-1', 'ascii']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to read {file_path} with any of the attempted encodings")

def update_cache(cache, file_path, file_hash_value, analysis_result):
    cache[file_path] = {
        'hash': file_hash_value,
        'analysis': analysis_result
    }
    save_cache(cache)

def split_content(content, max_chars=70000):
    """Split content into chunks based on character count."""
    chunks = []
    current_chunk = ""
    for line in content.split('\n'):
        if len(current_chunk) + len(line) > max_chars:
            chunks.append(current_chunk)
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def get_file_type(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    file_types = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.java': 'Java',
        '.cs': 'C#',
        '.html': 'HTML',
        '.css': 'CSS',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.go': 'Go',
        '.rs': 'Rust',
        '.ts': 'TypeScript',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.m': 'Objective-C',
        '.mm': 'Objective-C++',
        '.pl': 'Perl',
        '.sh': 'Shell Script',
        '.sql': 'SQL',
        '.xml': 'XML',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.md': 'Markdown',
        '.txt': 'Plain Text'
    }
    return file_types.get(extension, 'Unknown')

async def analyze_code_file_chunked(file_path, content, progress):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    file_type = get_file_type(file_path)
    
    template = f"""
# File Analysis

## Overall Purpose
[Provide a concise description of the file's main purpose and its role in the project]

## Main Functions
1. **[Function name]** - [Brief description of the function's purpose and key features]
2. **[Function name]** - [Brief description of the function's purpose and key features]
3. **[Function name]** - [Brief description of the function's purpose and key features]
[Continue listing main functions as needed]

## Notable patterns and potential issues
### [Category (e.g., Safety and Input Validation, Error Handling, Memory Management, etc.)]
- [Describe the pattern or issue]
- [Describe another pattern or issue in this category if applicable]

### [Another category]
- [Describe the pattern or issue]
- [Describe another pattern or issue in this category if applicable]
[Continue listing categories and issues as needed]
"""

    chunks = split_content(content)
    chunk_analyses = []

    async with semaphore:
        async with aiohttp.ClientSession() as session:
            for i, chunk in enumerate(chunks):
                async with rate_limiter:
                    data = {
                        "model": "mistralai/mistral-nemo",
                        "messages": [
                            {"role": "system", "content": f"You are a code analysis assistant for {file_type} files. Analyze the provided code chunk and output your analysis following the given template exactly. Use markdown formatting."},
                            {"role": "user", "content": f"Analyze the following {file_type} file chunk ({i+1}/{len(chunks)}):\n\nFile: {file_path}\n\n{chunk}\n\nUse this template for your response:\n{template}"}
                        ]
                    }
                    progress.update(progress.task_ids[0], description=f"[cyan]Analyzing {os.path.basename(file_path)} (Chunk {i+1}/{len(chunks)})[/cyan]")
                    try:
                        async with session.post(url, headers=headers, json=data) as response:
                            if response.status == 200:
                                result = await response.json()
                                if result and 'choices' in result and len(result['choices']) > 0:
                                    chunk_analyses.append(result['choices'][0]['message']['content'])
                                else:
                                    console.print(f"[bold red]Unexpected API response structure for {file_path} (Chunk {i+1})[/bold red]")
                                    console.print(f"[yellow]API response: {result}[/yellow]")
                                    chunk_analyses.append(f"Analysis failed for chunk {i+1} due to unexpected API response structure.")
                            else:
                                error_text = await response.text()
                                console.print(f"[bold red]Error: {response.status} - {error_text} (Chunk {i+1})[/bold red]")
                                chunk_analyses.append(f"Analysis failed for chunk {i+1} due to API error: {response.status} - {error_text}")
                    except Exception as e:
                        console.print(f"[bold red]Exception during API call for {file_path} (Chunk {i+1}): {str(e)}[/bold red]")
                        import traceback
                        console.print(f"[yellow]Traceback: {traceback.format_exc()}[/yellow]")
                        chunk_analyses.append(f"Analysis failed for chunk {i+1} due to exception: {str(e)}")

    # Combine chunk analyses
    combined_analysis = f"# Combined File Analysis for {file_type} File\n\n"
    for i, analysis in enumerate(chunk_analyses):
        combined_analysis += f"## Chunk {i+1} Analysis\n\n{analysis}\n\n"

    return file_path, file_type, combined_analysis

async def process_file(file_path, progress, cache):
    try:
        content = read_file_safely(file_path)
        
        file_hash_value = file_hash(content)
        if file_path in cache and cache[file_path]['hash'] == file_hash_value:
            cached_result = cache[file_path]['analysis']
            progress.update(progress.task_ids[0], advance=1, description=f"[green]Cached: {os.path.basename(file_path)}[/green]")
            return {
                "file_path": file_path,
                "file_type": cached_result['file_type'],
                "analysis": cached_result['analysis']
            }
        
        imports, functions, classes = extract_imports_and_functions(content, file_path)
        update_graph(file_path, imports, functions, classes)

        file_path, file_type, analysis = await analyze_code_file_chunked(file_path, content, progress)
        if analysis:
            result = {
                "file_path": file_path,
                "file_type": file_type,
                "analysis": analysis
            }
            update_cache(cache, file_path, file_hash_value, result)
            progress.update(progress.task_ids[0], advance=1, description=f"[green]Analyzed: {os.path.basename(file_path)} ({file_type})[/green]")
            return result
        else:
            console.print(f"[bold red]Error: Failed to analyze {file_path}[/bold red]")
            return None
    except Exception as e:
        console.print(f"[bold red]Error processing {file_path}: {str(e)}[/bold red]")
        import traceback
        console.print(f"[yellow]Traceback: {traceback.format_exc()}[/yellow]")
        progress.update(progress.task_ids[0], advance=1, description=f"[red]Failed: {os.path.basename(file_path)}[/red]")
        return None
async def process_files(files, progress, cache):
    tasks = [process_file(file_path, progress, cache) for file_path in files]
    results = await asyncio.gather(*tasks)
    return [result for result in results if result is not None]

def create_file_tree(path):
    tree = Tree(f"[bold green]{os.path.basename(path)}[/bold green]")
    
    def add_to_tree(current_path, current_tree):
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                branch = current_tree.add(f"[bold magenta]{item}[/bold magenta]")
                add_to_tree(item_path, branch)
            else:
                current_tree.add(f"[cyan]{item}[/cyan]")
    
    add_to_tree(path, tree)
    return tree

async def main():
    parser = argparse.ArgumentParser(description="Analyze a codebase")
    parser.add_argument("path", help="Path to the codebase")
    parser.add_argument("--output", help="Output file path", default="analysis_results.json")
    args = parser.parse_args()

    console.print(Panel.fit("[bold yellow]Code Analysis Tool[/bold yellow]"))
    
    file_tree = create_file_tree(args.path)
    console.print(file_tree)
    
    console.print("[bold green]Starting analysis...[/bold green]")

    files_to_process = []
    for root, dirs, files in os.walk(args.path):
        for file in files:
            if file.endswith(('.py', '.js', '.cpp', '.h', '.hpp', '.java', '.cs')):
                full_path = os.path.join(root, file)
                files_to_process.append(full_path)

    console.print(f"[green]Total files to process: {len(files_to_process)}[/green]")

    cache = load_cache()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    task = progress.add_task("[green]Analyzing files...", total=len(files_to_process) + 2)  # +2 for call graph and global analysis

    with Live(progress, refresh_per_second=10):
        results = await process_files(files_to_process, progress, cache)

        # Generate and analyze call graph
        progress.update(task, description="[cyan]Generating call graph...[/cyan]")
        call_graph = process_directory(args.path)
        call_graph_data = nx.node_link_data(call_graph)
        visualize_call_graph(call_graph, "codebase_call_graph")
        progress.update(task, advance=1, description="[green]Call graph generated[/green]")

        # Analyze call graph with LLM
        progress.update(task, description="[cyan]Analyzing call graph...[/cyan]")
        call_graph_analysis = await analyze_call_graph_with_llm(call_graph)
        progress.update(task, advance=1, description="[green]Call graph analyzed[/green]")

        # Perform global analysis
        progress.update(task, description="[cyan]Performing global analysis...[/cyan]")
        global_result = await global_analysis(results, progress)
        progress.update(task, advance=1, description="[green]Global analysis complete[/green]")

    console.print("[bold green]Analysis complete![/bold green]")
    
    # Display and save results
    console.print(Panel("[bold blue]Global Codebase Analysis[/bold blue]"))
    console.print(Markdown(global_result))
    console.print("\n")

    console.print(Panel("[bold blue]Call Graph Analysis[/bold blue]"))
    console.print(Markdown(call_graph_analysis))
    console.print("\n")

    # Save results
    full_results = {
        "global_analysis": global_result,
        "call_graph_analysis": call_graph_analysis,
        "file_analyses": results,
        "call_graph": call_graph_data
    }
    with open(args.output, 'w') as outfile:
        json.dump(full_results, outfile, indent=2)
    
    save_cache(cache)

    # Generate HTML documentation
    generate_documentation(full_results, call_graph, 'docs')
    
    console.print(f"[bold blue]Full analysis results saved to {args.output}[/bold blue]")
    console.print("[bold green]Codebase call graph saved as codebase_call_graph.png[/bold green]")

# New function to analyze call graph with LLM
async def analyze_call_graph_with_llm(call_graph):
    graph_summary = f"The call graph contains {call_graph.number_of_nodes()} functions and {call_graph.number_of_edges()} calls between them."
    most_called = sorted(call_graph.in_degree, key=lambda x: x[1], reverse=True)[:5]
    graph_summary += "\nMost called functions:\n" + "\n".join([f"{func}: {calls} calls" for func, calls in most_called])

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    async with semaphore:
        async with aiohttp.ClientSession() as session:
            async with rate_limiter:
                data = {
                    "model": "mistralai/mistral-nemo",
                    "messages": [
                        {"role": "system", "content": "You are a code analysis assistant. Analyze the given call graph summary and provide insights."},
                        {"role": "user", "content": f"Analyze the following call graph summary and provide insights on the codebase structure and potential areas for improvement:\n\n{graph_summary}"}
                    ]
                }
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        console.print(f"[bold red]Error: {response.status} - {await response.text()}[/bold red]")
                        return "Error in analyzing call graph"

if __name__ == "__main__":
    asyncio.run(main())