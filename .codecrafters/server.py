from flask import Flask, request, jsonify, render_template_string
import os, sys, json, subprocess
from openai import OpenAI

app = Flask(__name__)

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

TOOLS = [
    {"type": "function", "function": {"name": "Read", "description": "Read and return the contents of a file", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "The path to the file to read"}}, "required": ["file_path"]}}},
    {"type": "function", "function": {"name": "Write", "description": "Write content to a file", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "The path of the file to write to"}, "content": {"type": "string", "description": "The content to write to the file"}}, "required": ["file_path", "content"]}}},
    {"type": "function", "function": {"name": "Bash", "description": "Execute a shell command", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "The command to execute"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "ListFiles", "description": "List all files in a directory", "parameters": {"type": "object", "properties": {"directory": {"type": "string", "description": "The directory path to list files from"}}, "required": ["directory"]}}}
]

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Claude Code Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0d1117; color: #e6edf3; font-family: 'Segoe UI', sans-serif; height: 100vh; display: flex; flex-direction: column; }
        header { background: #161b22; padding: 16px 24px; border-bottom: 1px solid #30363d; display: flex; align-items: center; gap: 12px; }
        header h1 { font-size: 18px; color: #58a6ff; }
        header span { font-size: 12px; color: #8b949e; background: #21262d; padding: 2px 8px; border-radius: 12px; }
        #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
        .message { max-width: 80%; padding: 12px 16px; border-radius: 12px; line-height: 1.6; font-size: 14px; white-space: pre-wrap; }
        .user { align-self: flex-end; background: #1f6feb; color: white; border-bottom-right-radius: 4px; }
        .agent { align-self: flex-start; background: #161b22; border: 1px solid #30363d; border-bottom-left-radius: 4px; }
        .tool-log { align-self: flex-start; background: #0d1117; border: 1px solid #30363d; border-left: 3px solid #3fb950; font-family: monospace; font-size: 12px; color: #3fb950; padding: 8px 12px; border-radius: 6px; max-width: 80%; }
        .thinking { align-self: flex-start; color: #8b949e; font-size: 13px; font-style: italic; }
        #input-area { background: #161b22; border-top: 1px solid #30363d; padding: 16px 24px; display: flex; gap: 12px; }
        #prompt { flex: 1; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; color: #e6edf3; font-size: 14px; resize: none; height: 52px; outline: none; }
        #prompt:focus { border-color: #58a6ff; }
        #send { background: #238636; color: white; border: none; border-radius: 8px; padding: 12px 24px; cursor: pointer; font-size: 14px; font-weight: 600; }
        #send:hover { background: #2ea043; }
        #send:disabled { background: #21262d; color: #8b949e; cursor: not-allowed; }
    </style>
</head>
<body>
    <header>
        <h1>⚡ Claude Code Agent</h1>
        <span>claude-haiku-4.5</span>
    </header>
    <div id="chat">
        <div class="message agent">👋 Hi! I'm your AI coding agent. I can read files, write files, and run shell commands. What would you like me to do?</div>
    </div>
    <div id="input-area">
        <textarea id="prompt" placeholder="Ask me anything..." onkeydown="if(event.key==='Enter' && !event.shiftKey){event.preventDefault();send();}"></textarea>
        <button id="send" onclick="send()">Send</button>
    </div>
    <script>
        async function send() {
            const input = document.getElementById('prompt');
            const chat = document.getElementById('chat');
            const btn = document.getElementById('send');
            const text = input.value.trim();
            if (!text) return;

            input.value = '';
            btn.disabled = true;

            chat.innerHTML += `<div class="message user">${text}</div>`;
            chat.innerHTML += `<div class="thinking" id="thinking">⏳ Thinking...</div>`;
            chat.scrollTop = chat.scrollHeight;

            const res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: text})
            });
            const data = await res.json();

            document.getElementById('thinking').remove();

            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => {
                    chat.innerHTML += `<div class="tool-log">🔧 ${log}</div>`;
                });
            }

            chat.innerHTML += `<div class="message agent">${data.response}</div>`;
            chat.scrollTop = chat.scrollHeight;
            btn.disabled = false;
            input.focus();
        }
    </script>
</body>
</html>
"""

def execute_tool(tool_name, arguments):
    logs = []
    try:
        if tool_name == "Read":
            file_path = arguments["file_path"]
            logs.append(f"Read: {file_path}")
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist.", logs
            with open(file_path, "r") as f:
                return f.read(), logs

        elif tool_name == "Write":
            file_path = arguments["file_path"]
            content = arguments["content"]
            logs.append(f"Write: {file_path}")
            if os.path.dirname(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}", logs

        elif tool_name == "Bash":
            command = arguments["command"]
            logs.append(f"Bash: {command}")
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = proc.stdout + proc.stderr
            return output if output else "(command completed with no output)", logs

        elif tool_name == "ListFiles":
            directory = arguments["directory"]
            logs.append(f"ListFiles: {directory}")
            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist.", logs
            files = []
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
            return "\n".join(files) if files else "(no files found)", logs

        else:
            return f"Error: Unknown tool '{tool_name}'", logs

    except Exception as e:
        return f"Error: {str(e)}", logs

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    prompt = data.get("prompt", "")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [{"role": "user", "content": prompt}]
    all_logs = []

    for _ in range(20):
        response = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        messages.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})

        if not message.tool_calls:
            return jsonify({"response": message.content, "logs": all_logs})

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            result, logs = execute_tool(tool_name, arguments)
            all_logs.extend(logs)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    return jsonify({"response": "Max iterations reached.", "logs": all_logs})

if __name__ == "__main__":
    app.run(debug=True, port=5000)