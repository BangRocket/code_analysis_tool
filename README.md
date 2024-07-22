# Code Analysis Tool

## Overview

The Code Analysis Tool is a powerful Python-based utility designed to perform comprehensive analysis of codebases. It leverages AI-powered insights, static code analysis, and visualization techniques to provide developers with a deep understanding of their project structure, dependencies, and potential areas for improvement.

## Features

- **File Analysis**: Analyzes individual code files across multiple programming languages, including Python, JavaScript, C++, Java, and C#.
- **Call Graph Generation**: Creates a visual representation of function calls within the codebase.
- **Global Codebase Analysis**: Provides an overarching analysis of the entire codebase, identifying patterns and suggesting improvements.
- **Code Relationship Graph**: Generates a graph showing relationships between files, functions, classes, and imports.
- **Caching**: Implements a caching system to speed up subsequent analyses of unchanged files.
- **Documentation Generation**: Automatically generates HTML documentation based on the analysis results.
- **Progress Tracking**: Displays real-time progress of the analysis process.
- **File Tree Visualization**: Shows the structure of the analyzed codebase in a tree format.

## Requirements

- Python 3.7+
- OpenRouter API Key (set as an environment variable)
- Required Python packages (install via `pip install -r requirements.txt`):
  - aiohttp
  - asyncio
  - networkx
  - matplotlib
  - rich
  - python-dotenv
  - aiolimiter

## Usage

1. Set up your OpenRouter API key in a `.env` file:

OPENROUTER_API_KEY=your_api_key_here


2. Run the analysis:

python code_analyzer.py /path/to/your/codebase


3. Optional: Specify an output file for the analysis results:

python code_analyzer.py /path/to/your/codebase --output custom_output.json


## Output

- JSON file with detailed analysis results
- PNG file of the codebase call graph
- PNG file of the code relationship graph
- HTML documentation in the `docs` directory

## Key Components

- `analyze_code_file`: Performs AI-powered analysis of individual code files
- `generate_call_graph`: Creates a call graph of the codebase
- `global_analysis`: Conducts an overall analysis of the entire codebase
- `generate_codebase_graph`: Visualizes relationships within the codebase
- `generate_documentation`: Creates HTML documentation from analysis results

## Limitations

- The tool currently focuses on Python, JavaScript, C++, Java, and C# files.
- Analysis quality depends on the OpenRouter API's capabilities.
- Large codebases may take significant time to analyze due to API rate limiting.

## Contributing

Contributions to improve the Code Analysis Tool are welcome. Please submit pull requests or open issues on the project repository.

## License

This project is licensed under the MIT License.

MIT License

Copyright (c) 2024 Joshua Heidorn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.