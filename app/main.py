import argparse
import os
import sys
import json
import subprocess
from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "Read",
            "description": "Read and return the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Write",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to write to"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Bash",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ListFiles",
            "description": "List all files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The directory path to list files from"
                    }
                },
                "required": ["directory"]
            }
        }
    }
]


def execute_tool(tool_name, arguments):
    try:
        if tool_name == "Read":
            file_path = arguments["file_path"]
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist."
            print(f"[Read] {file_path}", file=sys.stderr)
            with open(file_path, "r") as f:
                return f.read()

        elif tool_name == "Write":
            file_path = arguments["file_path"]
            content = arguments["content"]
            if os.path.dirname(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            print(f"[Write] {file_path}", file=sys.stderr)
            with open(file_path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"

        elif tool_name == "Bash":
            command = arguments["command"]
            print(f"[Bash] {command}", file=sys.stderr)
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = proc.stdout + proc.stderr
            return output if output else "(command completed with no output)"

        elif tool_name == "ListFiles":
            directory = arguments["directory"]
            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist."
            print(f"[ListFiles] {directory}", file=sys.stderr)
            files = []
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
            return "\n".join(files) if files else "(no files found)"

        else:
            return f"Error: Unknown tool '{tool_name}'"

    except PermissionError:
        return f"Error: Permission denied for {tool_name} operation."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def main():
    p = argparse.ArgumentParser(description="Claude Code - An AI coding agent")
    p.add_argument("-p", required=True, help="The prompt to send to the agent")
    p.add_argument("--model", default="anthropic/claude-haiku-4.5", help="The model to use")
    p.add_argument("--verbose", action="store_true", help="Show detailed logs")
    args = p.parse_args()

    if not API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get a key at https://openrouter.ai and set it with:", file=sys.stderr)
        print("  $env:OPENROUTER_API_KEY='your-key'  (PowerShell)", file=sys.stderr)
        print("  export OPENROUTER_API_KEY='your-key'  (Mac/Linux)", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [{"role": "user", "content": args.p}]

    if args.verbose:
        print(f"[Agent] Starting with model: {args.model}", file=sys.stderr)
        print(f"[Agent] Prompt: {args.p}", file=sys.stderr)

    iteration = 0
    max_iterations = 20

    while iteration < max_iterations:
        iteration += 1

        try:
            chat = client.chat.completions.create(
                model=args.model,
                messages=messages,
                tools=TOOLS,
            )
        except Exception as e:
            print(f"Error calling API: {str(e)}", file=sys.stderr)
            sys.exit(1)

        message = chat.choices[0].message
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls
        })

        if not message.tool_calls:
            print(message.content)
            break

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            result = execute_tool(tool_name, arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    if iteration >= max_iterations:
        print("Warning: Reached maximum iterations limit.", file=sys.stderr)


if __name__ == "__main__":
    main()