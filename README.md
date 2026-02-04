# LivingEntity

A Python library for creating autonomous AI agents with a Spirit/Brain architecture.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🧠 **Dual-Layer Architecture**: High-level thinking ("Spirit") and execution mechanisms ("Brain")
- ⚡ **Asynchronous Loops**: Spirit (3s cycle) and Brain (1s cycle) operate independently
- 📚 **Vector Memory**: Built-in RAG with ChromaDB for associative retrieval
- 🔧 **Tool System**: Register custom functions as AI-callable tools
- 🔌 **Multi-Provider**: OpenAI, Cerebras, Groq, DeepSeek, LocalAI compatible

## Installation

```bash
git clone https://github.com/MikeMartemianov/PCControllerHuman.git
cd PCControllerHuman
pip install -e .
```

## Quick Start

```python
import asyncio
import os
from living_entity import LivingCore

# Initialize with Cerebras (or any OpenAI-compatible API)
entity = LivingCore(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
    model="llama3-70b-8192",
    system_params={
        "dm_temperature": 0.7,  # Spirit creativity
        "mm_temperature": 0.3,  # Brain precision
        "max_tokens": 1024
    }
)

# Register output callback
@entity.on_output
def handle_speech(text):
    print(f"Entity says: {text}")

# Run the entity
async def main():
    await entity.start()
    await entity.input_signal("Hello! Who are you?")
    await asyncio.sleep(10)
    await entity.stop()

asyncio.run(main())
```

## Registering Custom Tools

After you register tools with `register_tool`, the Brain's system prompt is updated automatically — **no manual reload is needed**. (In older versions you had to call `rebuild_tool_prompts()` after adding tools; this is now done for you.)

```python
# Method 1: Decorator
@entity.register_tool(
    description="Calculate a math expression",
    parameters={"expression": "Math expression like 2+2*3"},
    returns="Calculation result"
)
def calculate(expression: str) -> str:
    return str(eval(expression))

# Method 2: Direct registration
def get_weather(city: str) -> str:
    return f"Weather in {city}: 22°C, sunny"

entity.register_tool(
    get_weather,
    description="Get weather for a city",
    parameters={"city": "City name"}
)
```

If you change tools **without** using `register_tool` (e.g. by editing `entity.tools` or the underlying `ToolRegistry` directly), call `entity.rebuild_tool_prompts()` once so the AI sees the updated list.

## Supported Providers

| Provider | base_url | Models |
|----------|----------|--------|
| OpenAI | `None` (default) | gpt-4, gpt-3.5-turbo |
| Cerebras | `https://api.cerebras.ai/v1` | llama3-70b-8192, gpt-oss-120b |
| Groq | `https://api.groq.com/openai/v1` | llama3-70b-8192, mixtral-8x7b |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    LivingCore                        │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐                 │
│  │   Spirit    │───▶│    Brain    │                 │
│  │  (DM, 3s)   │    │  (MM, 1s)   │                 │
│  └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                         │
│  ┌──────▼──────┐    ┌──────▼──────┐                 │
│  │ MemoryMatrix│    │ToolRegistry │                 │
│  │  (ChromaDB) │    │  (Actions)  │                 │
│  └─────────────┘    └─────────────┘                 │
└─────────────────────────────────────────────────────┘
```

### Spirit (DM - Thinking Module)
The high-level thinking component that:
- Analyzes input signals and context
- Retrieves relevant memories
- Generates strategic decisions
- Delegates tasks to Brain

### Brain (MM - Mechanical Module)  
The execution component that:
- Receives tasks from Spirit
- Calls registered tools
- Handles user responses
- Reports results back to Spirit

## API Reference

### LivingCore

```python
entity = LivingCore(
    api_key: str,              # API key for LLM provider
    base_url: str = None,      # Custom API URL (None = OpenAI)
    model: str = "gpt-3.5-turbo",
    system_params: dict = {},  # Temperature, tokens, intervals
    memory_path: str = "./memory_db",
    personality_text: str = None  # Optional personality prompt
)

# Methods
await entity.start()           # Start Spirit and Brain loops
await entity.stop()            # Stop all processes
await entity.input_signal(text, source="user")  # Send input

# Callbacks
@entity.on_output              # Entity speech output
@entity.on_thought             # Spirit thoughts (debug)
@entity.on_action              # Brain actions (debug)

# Tools (reload is automatic after register_tool)
entity.register_tool(func, name, description, parameters, returns)
entity.list_tools()            # Get registered tool names
entity.execute_tool(name, **kwargs)  # Direct tool execution
entity.rebuild_tool_prompts()  # Call only if you changed tools outside register_tool
entity.sync_tools_output_callback()  # Re-bind say_to_user to core output handler
```

### MemoryMatrix

```python
from living_entity import MemoryMatrix

memory = MemoryMatrix(persist_path="./memory_db")
memory.save_memory("Important fact", source="user", importance=0.8)
results = memory.retrieve("search query", threshold=0.7)
```

## Examples

See the `examples/` directory for complete examples:
- `basic_usage.py` - Simple getting started
- `cerebras_example.py` - Using Cerebras API with personality
- `tools_example.py` - Custom tool registration
- `interactive_chat.py` - Continuous chat mode

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
black living_entity/
ruff check living_entity/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
