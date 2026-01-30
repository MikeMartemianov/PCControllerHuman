"""
AI Agent Wizard Server - Backend for the wizard web interface.

Creates and manages real AI agents using LivingEntity.
"""

import asyncio
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser

# Add parent to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from living_entity import LivingCore


# Global state
current_entity = None
entity_lock = threading.Lock()
response_buffer = []
event_loop = None


class WizardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for wizard API."""
    
    def __init__(self, *args, **kwargs):
        self.directory = os.path.dirname(__file__)
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
            
            if self.path == '/api/create':
                result = create_agent(data)
            elif self.path == '/api/message':
                result = send_message(data)
            elif self.path == '/api/stop':
                result = stop_agent()
            elif self.path == '/api/responses':
                result = get_responses()
            else:
                result = {'error': 'Unknown endpoint'}
            
            self.send_json_response(result)
            
        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_json_response({'error': str(e)}, 500)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/api/status':
            with entity_lock:
                running = current_entity is not None
                memories = current_entity.get_memory_count() if current_entity else 0
            self.send_json_response({
                'running': running,
                'memories': memories
            })
        elif self.path == '/api/responses':
            self.send_json_response(get_responses())
        elif self.path.startswith('/api/'):
            self.send_json_response({'error': 'Use POST for API calls'})
        else:
            super().do_GET()
    
    def send_json_response(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


def create_agent(config):
    """Create a new agent from config."""
    global current_entity, event_loop, response_buffer
    
    with entity_lock:
        # Stop existing entity
        if current_entity:
            try:
                asyncio.run_coroutine_threadsafe(
                    current_entity.stop(), 
                    event_loop
                ).result(timeout=5)
            except:
                pass
            current_entity = None
        
        response_buffer = []
    
    # Provider URLs
    providers = {
        'cerebras': 'https://api.cerebras.ai/v1',
        'groq': 'https://api.groq.com/openai/v1',
        'deepseek': 'https://api.deepseek.com/v1',
        'openai': None
    }
    
    # Models
    models = {
        'cerebras': 'gpt-oss-120b',
        'groq': 'mixtral-8x7b-32768',
        'deepseek': 'deepseek-chat',
        'openai': 'gpt-4-turbo-preview'
    }
    
    provider_name = config.get('provider', 'cerebras')
    api_key = config.get('apiKey', '')
    
    if not api_key:
        return {'error': 'API ключ не указан'}
    
    temperature = config.get('temperature', 0.5)
    personality = config.get('personality', 'Я полезный ИИ-ассистент.')
    name = config.get('name', 'Ава')
    
    # Add name to personality if not present
    if name.lower() not in personality.lower():
        personality = f"Меня зовут {name}.\n{personality}"
    
    # Clean old memory to avoid confusion
    import shutil
    memory_path = './memory_db'
    if os.path.exists(memory_path):
        try:
            shutil.rmtree(memory_path)
            print(f"[WIZARD] Cleared old memory at {memory_path}")
        except Exception as e:
            print(f"[WIZARD] Warning: Could not clear memory: {e}")
    
    print(f"\n[WIZARD] Creating agent: {name}")
    print(f"[WIZARD] Provider: {provider_name}")
    print(f"[WIZARD] Temperature: {temperature}")
    
    try:
        entity = LivingCore(
            api_key=api_key,
            base_url=providers.get(provider_name),
            model=models.get(provider_name, 'gpt-oss-120b'),
            system_params={
                # Lower temperature for stable JSON parsing
                'dm_temperature': min(0.3, temperature),
                'mm_temperature': min(0.2, temperature * 0.6),
                'dm_interval': 3.0,
                'mm_interval': 0.5,
                'max_tokens': 2048,  # More tokens for complete JSON
            },
            personality_text=personality,
        )
        
        # Set up output handler
        def handle_output(text):
            print(f"[AI] {text}")
            response_buffer.append({
                'type': 'ai',
                'text': text,
                'name': name
            })
        
        entity.on_output(handle_output)
        
        # Start entity
        asyncio.run_coroutine_threadsafe(
            entity.start(),
            event_loop
        ).result(timeout=10)
        
        with entity_lock:
            current_entity = entity
        
        print(f"[WIZARD] Agent {name} started successfully!")
        
        return {
            'success': True,
            'name': name,
            'memories': entity.get_memory_count()
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to create agent: {e}")
        return {'error': str(e)}


def send_message(data):
    """Send message to agent."""
    global current_entity, event_loop
    
    with entity_lock:
        if not current_entity:
            return {'error': 'Агент не запущен'}
        entity = current_entity
    
    message = data.get('message', '')
    if not message:
        return {'error': 'Пустое сообщение'}
    
    print(f"[USER] {message}")
    
    try:
        asyncio.run_coroutine_threadsafe(
            entity.input_signal(message),
            event_loop
        ).result(timeout=5)
        
        return {'success': True, 'sent': message}
        
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")
        return {'error': str(e)}


def get_responses():
    """Get buffered responses."""
    global response_buffer
    
    responses = response_buffer.copy()
    response_buffer.clear()
    
    return {'responses': responses}


def stop_agent():
    """Stop current agent."""
    global current_entity, event_loop
    
    with entity_lock:
        if current_entity:
            try:
                memories = current_entity.get_memory_count()
                asyncio.run_coroutine_threadsafe(
                    current_entity.stop(),
                    event_loop
                ).result(timeout=5)
                current_entity = None
                print("[WIZARD] Agent stopped")
                return {'success': True, 'memories': memories}
            except Exception as e:
                current_entity = None
                return {'success': True, 'error': str(e)}
    
    return {'success': True, 'memories': 0}


def run_event_loop():
    """Run asyncio event loop in background thread."""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()


def run_server(port=8080):
    """Run the wizard server."""
    # Start event loop thread
    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()
    
    # Wait for loop to start
    import time
    time.sleep(0.5)
    
    server = HTTPServer(('localhost', port), WizardHandler)
    
    print("\n" + "=" * 60)
    print("🧠 AI Agent Wizard Server")
    print("=" * 60)
    print(f"\n🌐 URL: http://localhost:{port}")
    print("📖 Open in browser to use the AI Agent Wizard")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    # Open browser
    webbrowser.open(f'http://localhost:{port}')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        stop_agent()


if __name__ == '__main__':
    run_server()
