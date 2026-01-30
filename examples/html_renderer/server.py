"""
AI HTML Renderer Server - Real-time HTML generation and manipulation by AI.

The AI expresses its responses as HTML that is immediately rendered.
All user actions on the page are captured and sent back to the AI for processing.
"""

import asyncio
import json
import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# WebSocket support
try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call(["pip", "install", "websockets"])
    import websockets

# Add parent to path for LivingEntity
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from living_entity import LivingCore

# =============================================================================
# Configuration
# =============================================================================

HTTP_PORT = 8081
WS_PORT = 8082

# =============================================================================
# Global State
# =============================================================================

current_entity: Optional[LivingCore] = None
entity_lock = threading.Lock()
event_loop: Optional[asyncio.AbstractEventLoop] = None
ws_connections: set = set()
user_api_key: Optional[str] = None  # API key from web interface


# =============================================================================
# HTML Commands Queue - for AI to send updates
# =============================================================================

html_command_queue: asyncio.Queue = None


async def send_to_all_clients(message: dict):
    """Send a message to all connected WebSocket clients."""
    if ws_connections:
        msg = json.dumps(message, ensure_ascii=False)
        await asyncio.gather(
            *[ws.send(msg) for ws in ws_connections],
            return_exceptions=True
        )


def queue_html_command(command: dict):
    """Queue an HTML command to be sent to clients."""
    global html_command_queue, event_loop
    if html_command_queue and event_loop:
        asyncio.run_coroutine_threadsafe(
            html_command_queue.put(command),
            event_loop
        )


# =============================================================================
# Custom AI Tools for HTML Manipulation
# =============================================================================

def create_html_tools(entity: LivingCore):
    """Register custom tools for HTML manipulation."""
    tools = entity.tools
    
    @tools.register(
        name="render_html",
        description="Полностью заменить HTML на странице. Используй для создания новой страницы или полного обновления. HTML будет отображён пользователю мгновенно.",
        parameters={"html": "Полный HTML код страницы (body content)"},
        returns="Подтверждение отрисовки",
        category="html"
    )
    def render_html(html: str) -> str:
        """Replace the entire HTML content of the preview."""
        queue_html_command({
            "type": "full",
            "html": html,
            "timestamp": datetime.now().isoformat()
        })
        return f"✓ HTML отрисован ({len(html)} символов)"
    
    @tools.register(
        name="patch_html",
        description="Точечно изменить элемент на странице по CSS-селектору. Действия: replace (заменить элемент), innerHTML (заменить содержимое), append (добавить в конец), prepend (добавить в начало), remove (удалить), setAttribute (установить атрибут), setStyle (изменить стиль), addClass (добавить класс), removeClass (удалить класс).",
        parameters={
            "selector": "CSS-селектор элемента (напр. '#myButton', '.card', 'h1')",
            "action": "Действие: replace|innerHTML|append|prepend|remove|setAttribute|setStyle|addClass|removeClass",
            "content": "Новое содержимое или значение (для setAttribute формат: 'атрибут=значение', для setStyle: 'свойство=значение')"
        },
        returns="Результат операции",
        category="html"
    )
    def patch_html(selector: str, action: str, content: str = "") -> str:
        """Modify a specific element on the page."""
        valid_actions = ["replace", "innerHTML", "append", "prepend", "remove", 
                        "setAttribute", "setStyle", "addClass", "removeClass"]
        if action not in valid_actions:
            return f"❌ Неизвестное действие '{action}'. Доступные: {', '.join(valid_actions)}"
        
        queue_html_command({
            "type": "patch",
            "selector": selector,
            "action": action,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        return f"✓ Патч применён: {action} на {selector}"
    
    @tools.register(
        name="run_js",
        description="Выполнить JavaScript код на странице. Используй для добавления интерактивности, анимаций или сложной логики.",
        parameters={"code": "JavaScript код для выполнения"},
        returns="Подтверждение выполнения",
        category="html"
    )
    def run_js(code: str) -> str:
        """Execute JavaScript in the page context."""
        queue_html_command({
            "type": "script",
            "code": code,
            "timestamp": datetime.now().isoformat()
        })
        return f"✓ JS выполнен ({len(code)} символов)"
    
    @tools.register(
        name="get_page_state",
        description="Получить текущее состояние страницы (какие элементы есть, их id и классы).",
        parameters={},
        returns="Описание текущего состояния страницы",
        category="html"
    )
    def get_page_state() -> str:
        """Request current page state from client."""
        queue_html_command({
            "type": "get_state",
            "timestamp": datetime.now().isoformat()
        })
        return "⏳ Запрос состояния страницы отправлен. Ответ придёт в следующем сообщении."
    
    print(f"[HTML_RENDERER] Registered 4 HTML tools")
    
    # Rebuild Brain's system prompt with new tools
    entity.rebuild_tool_prompts()


# =============================================================================
# AI Entity Management
# =============================================================================

SYSTEM_PERSONALITY = """Ты - интерактивный ИИ-дизайнер интерфейсов.

## КРИТИЧЕСКИ ВАЖНО - ПРАВИЛО ИЗМЕНЕНИЙ:
- render_html - ТОЛЬКО для первоначального создания страницы!
- patch_html - для ВСЕХ последующих изменений!
- НИКОГДА не пересоздавай всю страницу! Изменяй только нужные элементы!

## Твои инструменты:
1. **render_html(html)** - ТОЛЬКО для создания НОВОЙ страницы с нуля
2. **patch_html(selector, action, content)** - ОСНОВНОЙ инструмент для изменений!
3. **run_js(code)** - JavaScript для анимаций
4. **say_to_user(text)** - ТОЛЬКО для критических ошибок

## Действия patch_html:
- innerHTML - заменить содержимое элемента
- replace - заменить элемент целиком  
- append - добавить в конец
- prepend - добавить в начало
- remove - удалить элемент
- setAttribute - установить атрибут
- setStyle - изменить стиль
- addClass/removeClass - классы

## Примеры использования:
- Пользователь просит изменить текст кнопки → patch_html("#btn", "innerHTML", "Новый текст")
- Пользователь кликнул → patch_html("#result", "innerHTML", "<p>Результат</p>")
- Добавить элемент → patch_html("#container", "append", "<div>Новый блок</div>")

## Стиль дизайна:
- Тёмная тема: фон #0a0a0f, текст #f8fafc
- Акцент: #6366f1 (индиго)
- Все элементы с уникальными id!

## События пользователя:
- "click: #elementId" - клик → используй patch_html!
- "input: #inputId = значение" - ввод → используй patch_html!

ВСЕГДА используй patch_html для изменений, НЕ пересоздавай страницу!"""


def create_entity(api_key: str) -> LivingCore:
    """Create and configure the AI entity."""
    entity = LivingCore(
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
        model="gpt-oss-120b",
        system_params={
            "dm_temperature": 0.3,
            "mm_temperature": 0.1,
            "dm_interval": 0.5,  # Fast: Spirit thinks every 0.5s
            "mm_interval": 0.1,  # Fast: Brain acts every 0.1s
            "max_tokens": 4096,
        },
        personality_text=SYSTEM_PERSONALITY,
    )
    
    # Register HTML tools
    create_html_tools(entity)
    
    # Set up output handler for say_to_user
    def handle_output(text):
        print(f"[AI SAY] {text}")
        queue_html_command({
            "type": "message",
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
    
    entity.on_output(handle_output)
    
    return entity


async def start_entity(api_key: str):
    """Start the AI entity."""
    global current_entity, user_api_key
    
    with entity_lock:
        if current_entity:
            return {"success": True, "message": "Already running"}
    
    user_api_key = api_key
    
    print("[HTML_RENDERER] Creating AI entity...")
    try:
        entity = create_entity(api_key)
        
        print("[HTML_RENDERER] Starting AI entity...")
        await entity.start()
        
        with entity_lock:
            current_entity = entity
        
        print("[HTML_RENDERER] AI entity ready!")
        
        # Send initial greeting
        await entity.input_signal("Приветствуй пользователя и покажи ему что ты умеешь создавать - отрисуй красивую приветственную страницу с примерами твоих возможностей.")
        
        return {"success": True, "message": "AI started"}
        
    except Exception as e:
        error_msg = str(e)
        print(f"[HTML_RENDERER] Failed to start: {error_msg}")
        return {"success": False, "error": error_msg}


async def stop_entity():
    """Stop the AI entity."""
    global current_entity
    
    with entity_lock:
        entity = current_entity
        current_entity = None
    
    if entity:
        await entity.stop()
        print("[HTML_RENDERER] AI entity stopped")


async def send_to_entity(message: str):
    """Send a message to the AI entity."""
    with entity_lock:
        entity = current_entity
    
    if entity:
        await entity.input_signal(message)
    else:
        print("[HTML_RENDERER] No entity running")


# =============================================================================
# WebSocket Server
# =============================================================================

async def handle_websocket(websocket):
    """Handle a WebSocket connection."""
    ws_connections.add(websocket)
    print(f"[WS] Client connected. Total: {len(ws_connections)}")
    
    try:
        # Handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")
                
                if msg_type == "init":
                    # Initialize with API key
                    api_key = data.get("apiKey", "")
                    if api_key:
                        result = await start_entity(api_key)
                        await websocket.send(json.dumps({
                            "type": "init_result",
                            **result
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "init_result",
                            "success": False,
                            "error": "API key required"
                        }))
                
                elif msg_type == "event":
                    # User interaction event
                    event = data.get("event", {})
                    event_type = event.get("type", "unknown")
                    target = event.get("target", "")
                    value = event.get("value", "")
                    
                    # Format event for AI
                    if event_type == "click":
                        ai_message = f"click: {target}"
                    elif event_type == "input":
                        ai_message = f"input: {target} = {value}"
                    elif event_type == "submit":
                        form_data = event.get("formData", {})
                        ai_message = f"submit: {target} с данными {json.dumps(form_data, ensure_ascii=False)}"
                    elif event_type == "hover":
                        ai_message = f"hover: {target}"
                    elif event_type == "state":
                        # Page state response
                        ai_message = f"Текущее состояние страницы: {value}"
                    else:
                        ai_message = f"{event_type}: {target} ({value})"
                    
                    print(f"[EVENT] {ai_message}")
                    await send_to_entity(ai_message)
                    
                elif msg_type == "chat":
                    # Direct text message
                    text = data.get("text", "")
                    if text:
                        print(f"[CHAT] {text}")
                        await send_to_entity(text)
                        
                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                print(f"[WS] Invalid JSON: {message[:100]}")
            except Exception as e:
                print(f"[WS] Error processing message: {e}")
                import traceback
                traceback.print_exc()
                
    except websockets.ConnectionClosed:
        print("[WS] Client disconnected")
    finally:
        ws_connections.discard(websocket)
        print(f"[WS] Remaining clients: {len(ws_connections)}")


async def broadcast_commands():
    """Broadcast HTML commands from queue to all clients."""
    global html_command_queue
    
    html_command_queue = asyncio.Queue()
    
    while True:
        command = await html_command_queue.get()
        if ws_connections:
            await send_to_all_clients(command)


async def run_websocket_server():
    """Run the WebSocket server."""
    # Start broadcast task
    broadcast_task = asyncio.create_task(broadcast_commands())
    
    print(f"[WS] Starting WebSocket server on ws://localhost:{WS_PORT}")
    
    async with websockets.serve(handle_websocket, "localhost", WS_PORT):
        await asyncio.Future()  # Run forever


# =============================================================================
# HTTP Server
# =============================================================================

class HTMLRendererHandler(SimpleHTTPRequestHandler):
    """HTTP handler for static files."""
    
    def __init__(self, *args, **kwargs):
        self.directory = os.path.dirname(__file__)
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def log_message(self, format, *args):
        """Custom logging."""
        pass  # Suppress logs
    
    def end_headers(self):
        """Add CORS headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def run_http_server():
    """Run the HTTP server in a thread."""
    server = HTTPServer(('localhost', HTTP_PORT), HTMLRendererHandler)
    print(f"[HTTP] Starting HTTP server on http://localhost:{HTTP_PORT}")
    server.serve_forever()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    global event_loop
    
    print("\n" + "=" * 60)
    print("🎨 AI HTML Renderer")
    print("=" * 60)
    print(f"\n🌐 Open: http://localhost:{HTTP_PORT}")
    print(f"📡 WebSocket: ws://localhost:{WS_PORT}")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    # Start HTTP server in thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Open browser
    webbrowser.open(f'http://localhost:{HTTP_PORT}')
    
    # Run WebSocket server in main thread with asyncio
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    
    try:
        event_loop.run_until_complete(run_websocket_server())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        event_loop.run_until_complete(stop_entity())
        print("Goodbye!")


if __name__ == "__main__":
    main()
