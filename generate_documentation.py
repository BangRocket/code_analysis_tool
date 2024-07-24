import os
import json
from jinja2 import Template
import networkx as nx
from pyvis.network import Network
import tiktoken

def load_analysis_results(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def split_content(content, max_tokens=4000):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = encoding.encode(content)
    chunks = []
    current_chunk = []
    current_length = 0

    for token in tokens:
        if current_length + 1 > max_tokens:
            chunks.append(encoding.decode(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(token)
        current_length += 1

    if current_chunk:
        chunks.append(encoding.decode(current_chunk))

    return chunks

def create_call_graph_html(call_graph):
    net = Network(notebook=True, directed=True)
    for node in call_graph.nodes():
        net.add_node(node, label=node)
    for edge in call_graph.edges():
        net.add_edge(edge[0], edge[1])
    return net.generate_html()

def generate_documentation_html(analysis_results, output_dir, call_graph=None):
    os.makedirs(output_dir, exist_ok=True)
    index_template = Template('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Analysis Documentation</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css">
        <style>
            .sidebar { height: 100vh; overflow-y: auto; }
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <nav class="col-md-3 col-lg-2 d-md-block bg-light sidebar">
                    <div class="position-sticky pt-3">
                        <ul class="nav flex-column">
                            <li class="nav-item">
                                <a class="nav-link active" href="#global-analysis">Global Analysis</a>
                            </li>
                            {% if call_graph_html %}
                            <li class="nav-item">
                                <a class="nav-link" href="#call-graph">Call Graph</a>
                            </li>
                            {% endif %}
                            <li class="nav-item">
                                <a class="nav-link" href="#file-analyses">File Analyses</a>
                                <ul class="nav flex-column ms-3">
                                    {% for file_path, details in cache.items() %}
                                    <li class="nav-item">
                                        <a class="nav-link" href="#{{ file_path|replace('/', '-') }}">{{ file_path }}</a>
                                    </li>
                                    {% endfor %}
                                </ul>
                            </li>
                        </ul>
                    </div>
                </nav>

                <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
                    <h1 class="mt-4">Code Analysis Documentation</h1>

                    <section id="global-analysis">
                        <h2>Global Analysis</h2>
                        <div class="card">
                            <div class="card-body">
                                {% for chunk in global_analysis_chunks %}
                                    {{ chunk|safe }}
                                {% endfor %}
                            </div>
                        </div>
                    </section>

                    {% if call_graph_html %}
                    <section id="call-graph">
                        <h2>Call Graph</h2>
                        <div class="card">
                            <div class="card-body">
                                {{ cache['call_graph_html']|safe }}
                            </div>
                        </div>
                    </section>
                    {% endif %}

                    <section id="file-analyses">
                        <h2>File Analyses</h2>
                        {% for file_path, details in cache.items() %}
                        <div class="card mb-3" id="{{ file_path|replace('/', '-') }}">
                            <div class="card-header">
                                <h3>{{ file_path }}</h3>
                            </div>
                            <div class="card-body">
                                <h4>File Type: {{ file['file_type'] }}</h4>
                                {% for chunk in file['analysis_chunks'] %}
                                    {{ chunk|safe }}
                                {% endfor %}
                            </div>
                        </div>
                        {% endfor %}
                    </section>
                </main>
            </div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''')

    call_graph_html = create_call_graph_html(call_graph) if call_graph else None

    # Split global analysis into chunks
    global_analysis_chunks = split_content(analysis_results['global_analysis'])

    # Split file analyses into chunks
    for file in analysis_results['file_analyses']:
        file['analysis_chunks'] = split_content(file['analysis'])

    index_html = index_template.render(
        analysis_results=analysis_results,
        call_graph_html=call_graph_html,
        global_analysis_chunks=global_analysis_chunks
    )

    with open(os.path.join(output_dir, 'index.html'), 'w') as f:
        f.write(index_html)
    print(f"Documentation generated in {output_dir}")

import asyncio
from rich.console import Console

console = Console()

async def generate_documentation(path):
    console.print("[cyan]Generating documentation...[/cyan]")
    analysis_results = load_analysis_results('analysis_results.json')
    
    # Check if 'call_graph' exists in analysis_results
    if 'call_graph' in analysis_results:
        call_graph = nx.node_link_graph(analysis_results['call_graph'])
    else:
        console.print("[yellow]Warning: No call graph data found. Call graph will be omitted from the documentation.[/yellow]")
        call_graph = None
    
    generate_documentation_html(analysis_results, 'docs', call_graph)
    console.print("[green]Documentation generated in docs/ folder[/green]")

if __name__ == "__main__":
    asyncio.run(generate_documentation(input("Enter the path to the codebase: ")))
