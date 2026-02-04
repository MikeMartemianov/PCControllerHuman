"""
AppForge AI Agent - Advanced AI agent for creating applications.
Uses LivingEntity with comprehensive tools similar to a full coding agent.
"""

import asyncio
import sys
import os
import json
import shutil
import re
import base64
from datetime import datetime

# Initialize colorama for Windows compatibility
import colorama
colorama.init()

from living_entity import LivingCore

# Results storage
results = {
    "files_created": [],
    "files_modified": [],
    "files_deleted": [],
    "commands_run": [],
    "output": [],
    "errors": [],
    "complete": False
}

KNOWLEDGE_BASE = """
# AppForge AI Builder

You are an EXPERT AI coding agent. Create complete, working applications.

## CAPABILITIES
- Web apps (HTML/CSS/JS, React, Vue)
- Games (Canvas, WebGL)
- APIs and CLI tools
- Mobile-first responsive design
- Any programming language

## QUICK PATTERNS

### HTML App Template:
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>App</title></head><body><main id="app"></main><script>/*code*/</script></body></html>

### Essential CSS:
:root{--primary:#3b82f6;--bg:#fff;--text:#1f2937}*{margin:0;box-sizing:border-box}.flex{display:flex;align-items:center}.btn{padding:.5rem 1rem;border-radius:8px;cursor:pointer;transition:.2s}

### JS Patterns:
const el=document.querySelector('.c');el.addEventListener('click',fn);localStorage.setItem('k',JSON.stringify(d));fetch(url).then(r=>r.json());

### Canvas Game:
const canvas=document.getElementById('g'),ctx=canvas.getContext('2d');let last=0;function loop(t){const dt=(t-last)/1000;last=t;update(dt);render();requestAnimationFrame(loop)}requestAnimationFrame(loop)

## RULES
1. Create index.html as main entry
2. Make WORKING apps, not mockups
3. Use inline styles/scripts for simplicity
4. Handle errors with try/catch
5. Make responsive (mobile-friendly)
6. Call task_complete() when done
"""


async def run_agent(task: str, folder_path: str, api_key: str, base_url: str = None, model: str = "llama-3.3-70b"):
    """Run the AI agent to complete a task."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

    print("[AI]: Agent starting...", flush=True)
    print(f"[AI]: Folder path: {folder_path}", flush=True)
    
    # Load personality
    memory_dir = os.path.join(LIVING_ENTITY_PATH, ".ai_memory")
    os.makedirs(memory_dir, exist_ok=True)
    system_prompt_file = os.path.join(memory_dir, "system_prompt.txt")
    memories_file = os.path.join(memory_dir, "memories.json")
    
    if os.path.exists(system_prompt_file):
        with open(system_prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()
    else:
        system_prompt = KNOWLEDGE_BASE
    
    if os.path.exists(memories_file):
        with open(memories_file, 'r', encoding='utf-8') as f:
            memories = json.load(f)
    else:
        memories = []
    
    personality_text = system_prompt + "\n\nMemories:\n" + "\n".join(f"- {m}" for m in memories)
    
    entity = LivingCore(
        api_key=api_key,
        base_url=base_url or "https://api.cerebras.ai/v1",
        model=model,
        system_params={
            "dm_temperature": 0.7,
            "mm_temperature": 0.3,
            "max_tokens": 8192,
            "dm_interval": 2.0,
            "mm_interval": 0.5,
            "unsafe_mode": True,
        },
        memory_path=memory_dir,
        personality_text=personality_text
    )

    print("[AI]: LivingCore initialized", flush=True)

    # ===== FILE TOOLS =====
    
    @entity.register_tool(
        description="Create a new file with content. Creates parent directories automatically.",
        parameters={
            "path": "File path relative to project (e.g., 'src/App.jsx', 'index.html')",
            "content": "Complete file content to write"
        },
        returns="Success message with file path"
    )
    def create_file(path: str, content: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else folder_path, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            results["files_created"].append(path)
            print(f"Created: {path}")
            return f"✓ Created: {path} ({len(content)} bytes)"
        except Exception as e:
            return f"✗ Error creating {path}: {str(e)}"

    @entity.register_tool(
        description="Read a file's complete content",
        parameters={"path": "File path relative to project"},
        returns="File content or error message"
    )
    def read_file(path: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"Content of {path}:\n```\n{content}\n```"
            return f"✗ File not found: {path}"
        except Exception as e:
            return f"✗ Error reading {path}: {str(e)}"

    @entity.register_tool(
        description="Edit a file by replacing specific text. Use for modifications.",
        parameters={
            "path": "File path relative to project",
            "old_text": "Exact text to find and replace",
            "new_text": "New text to insert"
        },
        returns="Success/failure message"
    )
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if not os.path.exists(full_path):
                return f"✗ File not found: {path}"
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if old_text not in content:
                return f"✗ Text not found in {path}"
            new_content = content.replace(old_text, new_text, 1)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            if path not in results["files_modified"]:
                results["files_modified"].append(path)
            return f"✓ Modified: {path}"
        except Exception as e:
            return f"✗ Error editing {path}: {str(e)}"

    @entity.register_tool(
        description="Append content to the end of a file",
        parameters={
            "path": "File path relative to project",
            "content": "Content to append"
        },
        returns="Success message"
    )
    def append_to_file(path: str, content: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return f"✓ Appended to: {path}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Delete a file from the project",
        parameters={"path": "File path relative to project"},
        returns="Success message"
    )
    def delete_file(path: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if os.path.exists(full_path):
                os.remove(full_path)
                results["files_deleted"].append(path)
                return f"✓ Deleted: {path}"
            return f"✗ File not found: {path}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Copy a file to a new location",
        parameters={
            "source": "Source file path",
            "destination": "Destination file path"
        },
        returns="Success message"
    )
    def copy_file(source: str, destination: str) -> str:
        try:
            src = os.path.join(folder_path, source)
            dst = os.path.join(folder_path, destination)
            os.makedirs(os.path.dirname(dst) if os.path.dirname(dst) else folder_path, exist_ok=True)
            shutil.copy2(src, dst)
            results["files_created"].append(destination)
            return f"✓ Copied {source} to {destination}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Move/rename a file",
        parameters={
            "source": "Current file path",
            "destination": "New file path"
        },
        returns="Success message"
    )
    def move_file(source: str, destination: str) -> str:
        try:
            src = os.path.join(folder_path, source)
            dst = os.path.join(folder_path, destination)
            os.makedirs(os.path.dirname(dst) if os.path.dirname(dst) else folder_path, exist_ok=True)
            shutil.move(src, dst)
            return f"✓ Moved {source} to {destination}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    # ===== DIRECTORY TOOLS =====

    @entity.register_tool(
        description="List files and directories in a path",
        parameters={"path": "Directory path (use '.' for project root)"},
        returns="List of items with types"
    )
    def list_dir(path: str = ".") -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if not os.path.exists(full_path):
                return f"✗ Directory not found: {path}"
            items = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                if os.path.isdir(item_path):
                    items.append(f"📁 {item}/")
                else:
                    size = os.path.getsize(item_path)
                    items.append(f"📄 {item} ({size} bytes)")
            return "\n".join(items) if items else "(empty directory)"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Create a new directory",
        parameters={"path": "Directory path to create"},
        returns="Success message"
    )
    def create_dir(path: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            os.makedirs(full_path, exist_ok=True)
            return f"✓ Created directory: {path}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Delete a directory and all its contents",
        parameters={"path": "Directory path to delete"},
        returns="Success message"
    )
    def delete_dir(path: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if os.path.exists(full_path):
                shutil.rmtree(full_path)
                return f"✓ Deleted directory: {path}"
            return f"✗ Directory not found: {path}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    # ===== SEARCH TOOLS =====

    @entity.register_tool(
        description="Search for text in all project files",
        parameters={
            "query": "Text or regex pattern to search for",
            "file_pattern": "Optional: file extension filter (e.g., '*.js', '*.html')"
        },
        returns="List of matches with file paths and line numbers"
    )
    def search_in_files(query: str, file_pattern: str = "*") -> str:
        try:
            matches = []
            for root, dirs, files in os.walk(folder_path):
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '.ai_memory']]
                for file in files:
                    if file_pattern == "*" or file.endswith(file_pattern.replace("*", "")):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, folder_path)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                for i, line in enumerate(f, 1):
                                    if query.lower() in line.lower():
                                        matches.append(f"{rel_path}:{i}: {line.strip()[:100]}")
                        except:
                            pass
            return "\n".join(matches[:20]) if matches else "No matches found"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Get file statistics (size, lines, word count)",
        parameters={"path": "File path to analyze"},
        returns="File statistics"
    )
    def file_stats(path: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if not os.path.exists(full_path):
                return f"✗ File not found: {path}"
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.count('\n') + 1
            words = len(content.split())
            size = os.path.getsize(full_path)
            return f"📊 {path}: {size} bytes, {lines} lines, {words} words"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    # ===== COMMAND TOOLS =====

    @entity.register_tool(
        description="Run a shell command in the project directory. Use for npm, git, etc.",
        parameters={"command": "Shell command to execute"},
        returns="Command output (stdout + stderr)"
    )
    def run_command(command: str) -> str:
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=folder_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            output = (result.stdout + result.stderr).strip()
            results["commands_run"].append(command)
            return output[:3000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "✗ Command timed out (120s limit)"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    # ===== PROJECT TOOLS =====

    @entity.register_tool(
        description="Initialize a package.json for a Node.js project",
        parameters={
            "name": "Project name",
            "description": "Project description",
            "dependencies": "Comma-separated list of dependencies (optional)"
        },
        returns="Success message"
    )
    def init_package_json(name: str, description: str = "", dependencies: str = "") -> str:
        try:
            pkg = {
                "name": name.lower().replace(" ", "-"),
                "version": "1.0.0",
                "description": description,
                "main": "index.js",
                "scripts": {
                    "start": "node index.js",
                    "dev": "vite"
                },
                "dependencies": {}
            }
            if dependencies:
                for dep in dependencies.split(","):
                    dep = dep.strip()
                    if dep:
                        pkg["dependencies"][dep] = "latest"
            full_path = os.path.join(folder_path, "package.json")
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(pkg, f, indent=2)
            results["files_created"].append("package.json")
            return f"✓ Created package.json for {name}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Get a project template (html-app, react-app, game, api)",
        parameters={"template_type": "Type: 'html-app', 'react-app', 'game', 'api'"},
        returns="Template structure description"
    )
    def get_template(template_type: str) -> str:
        templates = {
            "html-app": """
HTML App Template:
1. Create index.html with <!DOCTYPE html>, meta viewport, title
2. Add <style> section with modern CSS (flexbox, variables, animations)
3. Add <script> section with ES6+ JavaScript
4. Include responsive design for mobile
""",
            "react-app": """
React App Template:
1. Create index.html with root div and React CDN scripts
2. Create src/App.jsx with functional component using hooks
3. Create src/main.jsx with ReactDOM.createRoot
4. Add Tailwind CSS via CDN for styling
""",
            "game": """
Game Template:
1. Create index.html with canvas element
2. Add game loop with requestAnimationFrame
3. Implement: init(), update(delta), render()
4. Add keyboard/mouse event listeners
5. Include game state management
""",
            "api": """
API Template:
1. Create index.js with Express server
2. Add routes for CRUD operations
3. Include error handling middleware
4. Add CORS for frontend access
"""
        }
        return templates.get(template_type, "Unknown template. Available: html-app, react-app, game, api")

    # ===== UTILITY TOOLS =====

    @entity.register_tool(
        description="Generate a UUID or random ID",
        parameters={"length": "ID length (default 8)"},
        returns="Generated ID"
    )
    def generate_id(length: int = 8) -> str:
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @entity.register_tool(
        description="Get current timestamp",
        parameters={},
        returns="ISO format timestamp"
    )
    def get_timestamp() -> str:
        return datetime.now().isoformat()

    @entity.register_tool(
        description="Validate JSON content",
        parameters={"content": "JSON string to validate"},
        returns="Valid/Invalid with details"
    )
    def validate_json(content: str) -> str:
        try:
            json.loads(content)
            return "✓ Valid JSON"
        except json.JSONDecodeError as e:
            return f"✗ Invalid JSON: {str(e)}"

    @entity.register_tool(
        description="Check if a file or directory exists",
        parameters={"path": "Path to check"},
        returns="Exists/Not exists with type"
    )
    def path_exists(path: str) -> str:
        full_path = os.path.join(folder_path, path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                return f"✓ Directory exists: {path}"
            return f"✓ File exists: {path}"
        return f"✗ Does not exist: {path}"

    @entity.register_tool(
        description="Read multiple files at once",
        parameters={"paths": "Comma-separated list of file paths"},
        returns="Contents of all files"
    )
    def read_files(paths: str) -> str:
        results_str = []
        for p in paths.split(","):
            p = p.strip()
            if not p:
                continue
            full_path = os.path.join(folder_path, p)
            try:
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    results_str.append(f"=== {p} ===\n{content}")
                else:
                    results_str.append(f"=== {p} ===\n(file not found)")
            except Exception as e:
                results_str.append(f"=== {p} ===\nError: {str(e)}")
        return "\n\n".join(results_str)

    @entity.register_tool(
        description="Insert text at a specific line in a file",
        parameters={
            "path": "File path",
            "line_number": "Line number to insert at (1-based)",
            "content": "Content to insert"
        },
        returns="Success message"
    )
    def insert_at_line(path: str, line_number: int, content: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if not os.path.exists(full_path):
                return f"✗ File not found: {path}"
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            idx = max(0, min(line_number - 1, len(lines)))
            lines.insert(idx, content + '\n')
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return f"✓ Inserted at line {line_number} in {path}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Replace text in file using regex pattern",
        parameters={
            "path": "File path",
            "pattern": "Regex pattern to match",
            "replacement": "Replacement text"
        },
        returns="Number of replacements made"
    )
    def regex_replace(path: str, pattern: str, replacement: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            if not os.path.exists(full_path):
                return f"✗ File not found: {path}"
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return f"✓ Made {count} replacement(s) in {path}"
            return f"✗ Pattern not found in {path}"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Write raw binary data as base64 (for images, etc.)",
        parameters={
            "path": "File path",
            "base64_data": "Base64 encoded data"
        },
        returns="Success message"
    )
    def write_binary(path: str, base64_data: str) -> str:
        try:
            full_path = os.path.join(folder_path, path)
            os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else folder_path, exist_ok=True)
            data = base64.b64decode(base64_data)
            with open(full_path, 'wb') as f:
                f.write(data)
            results["files_created"].append(path)
            return f"✓ Written binary file: {path} ({len(data)} bytes)"
        except Exception as e:
            return f"✗ Error: {str(e)}"

    @entity.register_tool(
        description="Get code snippet template for common patterns",
        parameters={"pattern": "Pattern name: modal, form, carousel, tabs, accordion, dropdown, toast, loading"},
        returns="Code snippet"
    )
    def get_code_snippet(pattern: str) -> str:
        snippets = {
            "modal": '''
<!-- Modal HTML -->
<div id="modal" class="modal-overlay" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.5); align-items:center; justify-content:center; z-index:50;">
  <div class="modal-content" style="background:white; border-radius:16px; padding:2rem; max-width:500px; width:90%;">
    <h2>Modal Title</h2>
    <p>Modal content here...</p>
    <button onclick="closeModal()">Close</button>
  </div>
</div>
<script>
function openModal() { document.getElementById('modal').style.display = 'flex'; }
function closeModal() { document.getElementById('modal').style.display = 'none'; }
document.getElementById('modal').onclick = (e) => { if(e.target.id === 'modal') closeModal(); };
</script>
''',
            "form": '''
<form id="myForm" onsubmit="handleSubmit(event)">
  <div style="margin-bottom:1rem;">
    <label for="name" style="display:block; margin-bottom:0.5rem; font-weight:500;">Name</label>
    <input type="text" id="name" required style="width:100%; padding:0.75rem; border:1px solid #ddd; border-radius:8px;">
  </div>
  <div style="margin-bottom:1rem;">
    <label for="email" style="display:block; margin-bottom:0.5rem; font-weight:500;">Email</label>
    <input type="email" id="email" required style="width:100%; padding:0.75rem; border:1px solid #ddd; border-radius:8px;">
  </div>
  <button type="submit" style="width:100%; padding:0.75rem; background:#3b82f6; color:white; border:none; border-radius:8px; font-weight:600; cursor:pointer;">Submit</button>
</form>
<script>
function handleSubmit(e) {
  e.preventDefault();
  const data = { name: document.getElementById('name').value, email: document.getElementById('email').value };
  console.log('Form submitted:', data);
}
</script>
''',
            "tabs": '''
<div class="tabs">
  <div class="tab-buttons" style="display:flex; gap:0.5rem; border-bottom:2px solid #e5e7eb; margin-bottom:1rem;">
    <button class="tab-btn active" onclick="showTab('tab1')" style="padding:0.75rem 1.5rem; background:none; border:none; border-bottom:2px solid #3b82f6; margin-bottom:-2px; cursor:pointer;">Tab 1</button>
    <button class="tab-btn" onclick="showTab('tab2')" style="padding:0.75rem 1.5rem; background:none; border:none; cursor:pointer;">Tab 2</button>
  </div>
  <div id="tab1" class="tab-content">Content for Tab 1</div>
  <div id="tab2" class="tab-content" style="display:none;">Content for Tab 2</div>
</div>
<script>
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab-btn').forEach(el => el.style.borderBottom = 'none');
  document.getElementById(id).style.display = 'block';
  event.target.style.borderBottom = '2px solid #3b82f6';
}
</script>
''',
            "toast": '''
<div id="toast" style="position:fixed; bottom:2rem; right:2rem; padding:1rem 1.5rem; background:#22c55e; color:white; border-radius:8px; transform:translateY(100px); opacity:0; transition:all 0.3s;"></div>
<script>
function showToast(message, type='success') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.style.background = type === 'error' ? '#ef4444' : '#22c55e';
  toast.style.transform = 'translateY(0)';
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.transform = 'translateY(100px)'; toast.style.opacity = '0'; }, 3000);
}
</script>
''',
            "loading": '''
<div id="loading" style="display:none; position:fixed; inset:0; background:rgba(255,255,255,0.9); align-items:center; justify-content:center; z-index:100;">
  <div style="text-align:center;">
    <div style="width:50px; height:50px; border:4px solid #e5e7eb; border-top-color:#3b82f6; border-radius:50%; animation:spin 1s linear infinite;"></div>
    <p style="margin-top:1rem; color:#6b7280;">Loading...</p>
  </div>
</div>
<style>@keyframes spin { to { transform: rotate(360deg); } }</style>
<script>
function showLoading() { document.getElementById('loading').style.display = 'flex'; }
function hideLoading() { document.getElementById('loading').style.display = 'none'; }
</script>
'''
        }
        return snippets.get(pattern, f"Unknown pattern '{pattern}'. Available: " + ", ".join(snippets.keys()))

    @entity.register_tool(
        description="Mark the task as complete. Call this when finished.",
        parameters={"summary": "Brief summary of what was created"},
        returns="Completion confirmation"
    )
    def task_complete(summary: str) -> str:
        results["complete"] = True
        results["summary"] = summary
        return "✓ Task marked complete. Stopping agent."

    # Capture output
    @entity.on_output
    def handle_output(text: str):
        results["output"].append(text)
        print(f"[AI]: {text}")

    # Start entity
    await entity.start()

    print("[AI]: Entity started", flush=True)

    # Send task
    await entity.input_signal(f"""You are AppForge AI Builder - an expert developer agent.

PROJECT PATH: {folder_path}
TASK: {task}

INSTRUCTIONS:
1. Analyze the task and plan the file structure
2. Create all necessary files using create_file tool
3. Make the app FULLY FUNCTIONAL (not a mockup)
4. ALWAYS create index.html as the main entry point
5. Include all CSS and JS inline for self-contained apps
6. For games: implement real gameplay mechanics
7. For tools: make them actually work
8. Call task_complete() when finished

START NOW - create an amazing application!""")

    # Wait for completion (max 180 seconds)
    for _ in range(360):  # 360 * 0.5s = 180s max
        await asyncio.sleep(0.5)
        if results["complete"]:
            break

    # Stop entity
    await entity.stop()

    return results


def main():
    """Entry point for command line usage."""
    if len(sys.argv) < 4:
        print("Usage: python ai_agent.py <task> <folder_path> <api_key> [base_url] [model]")
        sys.exit(1)

    task = sys.argv[1]
    folder_path = sys.argv[2]
    api_key = sys.argv[3]
    base_url = sys.argv[4] if len(sys.argv) > 4 else None
    model = sys.argv[5] if len(sys.argv) > 5 else "llama-3.3-70b"

    # Run agent
    result = asyncio.run(run_agent(task, folder_path, api_key, base_url, model))

    # Output JSON result
    print("\n=== RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
