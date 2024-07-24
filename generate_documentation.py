import os
import json
from jinja2 import Template
import networkx as nx
from pyvis.network import Network
import asyncio
from rich.console import Console

console = Console()

def load_analysis_cache(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def create_call_graph_html(call_graph):
    net = Network(notebook=True, directed=True, bgcolor="#222222", font_color="white")
    for node in call_graph.nodes():
        net.add_node(node, label=node, color="#4CAF50")
    for edge in call_graph.edges():
        net.add_edge(edge[0], edge[1], color="#FFFFFF")
    return net.generate_html()

def generate_documentation_html(analysis_cache, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    index_template = Template('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Analysis Documentation</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
            body { background-color: #1a202c; color: #e2e8f0; }
            .sidebar { height: 100vh; overflow-y: auto; }
            .content { max-width: 800px; margin: 0 auto; }
            pre { background-color: #2d3748; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
        </style>
    </head>
    <body class="font-sans">
        <div class="flex">
            <nav class="w-64 bg-gray-800 sidebar">
                <div class="p-4">
                    <h2 class="text-xl font-bold mb-4">Navigation</h2>
                    <ul>
                        <li class="mb-2"><a href="#global-analysis" class="text-blue-300 hover:text-blue-100">Global Analysis</a></li>
                        {% if call_graph_html %}
                        <li class="mb-2"><a href="#call-graph" class="text-blue-300 hover:text-blue-100">Call Graph</a></li>
                        {% endif %}
                        <li class="mb-2">
                            <span class="text-blue-300">File Analyses</span>
                            <ul class="ml-4 mt-2">
                                {% for file_path, file_data in analysis_cache.items() %}
                                {% if file_path != 'global_analysis' and file_path != 'call_graph' %}
                                <li class="mb-1"><a href="#{{ file_path|replace('/', '-') }}" class="text-blue-300 hover:text-blue-100">{{ file_path }}</a></li>
                                {% endif %}
                                {% endfor %}
                            </ul>
                        </li>
                    </ul>
                </div>
            </nav>

            <main class="flex-1 p-8">
                <div class="content">
                    <h1 class="text-4xl font-bold mb-8">Code Analysis Documentation</h1>

                    <section id="global-analysis" class="mb-12">
                        <h2 class="text-2xl font-bold mb-4">Global Analysis</h2>
                        <div class="bg-gray-700 rounded-lg p-6">
                            {{ analysis_cache['global_analysis']|safe }}
                        </div>
                    </section>

                    {% if call_graph_html %}
                    <section id="call-graph" class="mb-12">
                        <h2 class="text-2xl font-bold mb-4">Call Graph</h2>
                        <div class="bg-gray-700 rounded-lg p-6">
                            {{ call_graph_html|safe }}
                        </div>
                    </section>
                    {% endif %}

                    <section id="file-analyses">
                        <h2 class="text-2xl font-bold mb-4">File Analyses</h2>
                        {% for file_path, file_data in analysis_cache.items() %}
                        {% if file_path != 'global_analysis' and file_path != 'call_graph' %}
                        <div class="mb-8 bg-gray-700 rounded-lg p-6" id="{{ file_path|replace('/', '-') }}">
                            <h3 class="text-xl font-bold mb-2">{{ file_path }}</h3>
                            <h4 class="text-lg font-semibold mb-2">File Type: {{ file_data['file_type'] }}</h4>
                            <div class="whitespace-pre-wrap">{{ file_data['analysis']|safe }}</div>
                        </div>
                        {% endif %}
                        {% endfor %}
                    </section>
                </div>
            </main>
        </div>
    </body>
    </html>
    ''')

    call_graph_html = None
    if 'call_graph' in analysis_cache:
        call_graph = nx.node_link_graph(analysis_cache['call_graph'])
        call_graph_html = create_call_graph_html(call_graph)

    index_html = index_template.render(
        analysis_cache=analysis_cache,
        call_graph_html=call_graph_html
    )

    with open(os.path.join(output_dir, 'index.html'), 'w') as f:
        f.write(index_html)
    console.print(f"[green]Documentation generated in {output_dir}[/green]")

async def generate_documentation(path):
    console.print("[cyan]Generating documentation...[/cyan]")
    analysis_cache = load_analysis_cache('analysis_cache.json')
    generate_documentation_html(analysis_cache, 'docs')

if __name__ == "__main__":
    asyncio.run(generate_documentation(input("Enter the path to the codebase: ")))
