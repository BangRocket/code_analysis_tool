import os
import json
from jinja2 import Template
import networkx as nx
from pyvis.network import Network

def load_analysis_results(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def create_call_graph_html(call_graph):
    net = Network(notebook=True, directed=True)
    for node in call_graph.nodes():
        net.add_node(node, label=node)
    for edge in call_graph.edges():
        net.add_edge(edge[0], edge[1])
    return net.generate_html()

def generate_documentation(analysis_results, call_graph, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Generate index.html
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
                            <li class="nav-item">
                                <a class="nav-link" href="#call-graph">Call Graph</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="#file-analyses">File Analyses</a>
                                <ul class="nav flex-column ms-3">
                                    {% for file in analysis_results['file_analyses'] %}
                                    <li class="nav-item">
                                        <a class="nav-link" href="#{{ file['file_path']|replace('/', '-') }}">{{ file['file_path'] }}</a>
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
                                {{ analysis_results['global_analysis']|safe }}
                            </div>
                        </div>
                    </section>

                    <section id="call-graph">
                        <h2>Call Graph</h2>
                        <div class="card">
                            <div class="card-body">
                                {{ call_graph_html|safe }}
                            </div>
                        </div>
                    </section>

                    <section id="file-analyses">
                        <h2>File Analyses</h2>
                        {% for file in analysis_results['file_analyses'] %}
                        <div class="card mb-3" id="{{ file['file_path']|replace('/', '-') }}">
                            <div class="card-header">
                                <h3>{{ file['file_path'] }}</h3>
                            </div>
                            <div class="card-body">
                                <h4>File Type: {{ file['file_type'] }}</h4>
                                {{ file['analysis']|safe }}
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

    call_graph_html = create_call_graph_html(call_graph)

    index_html = index_template.render(
        analysis_results=analysis_results,
        call_graph_html=call_graph_html
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
    call_graph = nx.node_link_graph(analysis_results['call_graph'])
    generate_documentation(analysis_results, call_graph, 'docs')
    console.print("[green]Documentation generated in docs/ folder[/green]")

if __name__ == "__main__":
    asyncio.run(generate_documentation(input("Enter the path to the codebase: ")))
