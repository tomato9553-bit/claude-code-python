# Claude Code (Python)

A Python implementation of an AI coding agent, built on top of the Anthropic Claude API. Inspired by the CodeCrafters "Build Your Own Claude Code" challenge.

## What it does

This agent accepts a prompt and autonomously completes tasks by:
- Reading files from your filesystem
- Writing files to your filesystem
- Running shell commands
- Looping until the task is fully complete

## How it works

The agent uses a loop:
1. Sends your prompt to Claude
2. If Claude requests a tool (Read, Write, Bash), executes it
3. Feeds the result back to Claude
4. Repeats until Claude gives a final answer

## Setup

### Prerequisites
- Python 3.8+
- An OpenRouter API key (get one at https://openrouter.ai)

### Installation
git clone <your-repo-url>
cd codecrafters-claude-code-python
pip install openai

### Configuration
Set your API key as an environment variable:

Windows (PowerShell):
$env:OPENROUTER_API_KEY="your-api-key-here"

Mac/Linux:
export OPENROUTER_API_KEY="your-api-key-here"

## Usage

python app/main.py -p "Your prompt here"

### Examples

# Read a file and summarize it
python app/main.py -p "What is in README.md? Summarize it."

# Create a new file
python app/main.py -p "Create a file called hello.py that prints Hello World"

# Delete a file
python app/main.py -p "Delete the file called old.txt"

## Tools Available

| Tool      | Description                                      |
|-----------|--------------------------------------------------|
| Read      | Reads the contents of a file                     |
| Write     | Writes content to a file (creates or overwrites) |
| Bash      | Executes a shell command and returns output      |
| ListFiles | Lists all files in a directory                   |

## Built With
- OpenAI Python SDK
- OpenRouter - API gateway to Claude
- Anthropic Claude Haiku 4.5