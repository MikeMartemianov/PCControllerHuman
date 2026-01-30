"""
Configuration generator for LivingEntity.

Generate optimized configurations for different providers and use cases.
"""

import json
import os
import sys
from typing import Optional


# Provider presets
PROVIDER_PRESETS = {
    "openai": {
        "name": "OpenAI",
        "base_url": None,
        "models": {
            "gpt-4": {"context": 8192, "fast": False, "cost": "high"},
            "gpt-4-turbo": {"context": 128000, "fast": True, "cost": "medium"},
            "gpt-4o": {"context": 128000, "fast": True, "cost": "medium"},
            "gpt-3.5-turbo": {"context": 16385, "fast": True, "cost": "low"},
        },
        "default_model": "gpt-3.5-turbo",
        "recommended_params": {
            "dm_temperature": 0.7,
            "mm_temperature": 0.3,
        },
    },
    "cerebras": {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "models": {
            "llama3-70b-8192": {"context": 8192, "fast": True, "cost": "medium"},
            "llama3-8b-8192": {"context": 8192, "fast": True, "cost": "low"},
        },
        "default_model": "llama3-70b-8192",
        "recommended_params": {
            "dm_temperature": 0.1,  # Lower for stable JSON
            "mm_temperature": 0.0,
            "dm_interval": 2.0,  # Faster because Cerebras is fast
            "mm_interval": 0.5,
        },
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "models": {
            "llama3-70b-8192": {"context": 8192, "fast": True, "cost": "medium"},
            "llama3-8b-8192": {"context": 8192, "fast": True, "cost": "low"},
            "mixtral-8x7b-32768": {"context": 32768, "fast": True, "cost": "medium"},
            "gemma-7b-it": {"context": 8192, "fast": True, "cost": "low"},
        },
        "default_model": "llama3-70b-8192",
        "recommended_params": {
            "dm_temperature": 0.3,
            "mm_temperature": 0.1,
            "dm_interval": 2.0,
            "mm_interval": 0.5,
        },
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": {
            "deepseek-chat": {"context": 32768, "fast": False, "cost": "low"},
            "deepseek-coder": {"context": 16384, "fast": False, "cost": "low"},
        },
        "default_model": "deepseek-chat",
        "recommended_params": {
            "dm_temperature": 0.5,
            "mm_temperature": 0.2,
        },
    },
    "local": {
        "name": "Local (Ollama, LM Studio)",
        "base_url": "http://localhost:11434/v1",
        "models": {
            "llama3": {"context": 8192, "fast": False, "cost": "free"},
            "mistral": {"context": 8192, "fast": False, "cost": "free"},
            "codellama": {"context": 16384, "fast": False, "cost": "free"},
        },
        "default_model": "llama3",
        "recommended_params": {
            "dm_temperature": 0.7,
            "mm_temperature": 0.3,
            "dm_interval": 5.0,  # Slower for local
            "mm_interval": 2.0,
        },
    },
}

# Use case presets
USE_CASE_PRESETS = {
    "chat": {
        "name": "Conversational Chat",
        "description": "Friendly conversation with good memory",
        "params": {
            "dm_temperature": 0.8,
            "mm_temperature": 0.5,
            "max_tokens": 512,
        },
    },
    "coding": {
        "name": "Code Assistant",
        "description": "Precise code generation and execution",
        "params": {
            "dm_temperature": 0.2,
            "mm_temperature": 0.0,
            "max_tokens": 2048,
            "unsafe_mode": False,
        },
    },
    "research": {
        "name": "Research Assistant",
        "description": "Analytical thinking with detailed memory",
        "params": {
            "dm_temperature": 0.5,
            "mm_temperature": 0.2,
            "max_tokens": 1024,
            "dm_interval": 5.0,  # More time to think
        },
    },
    "automation": {
        "name": "Task Automation",
        "description": "Fast, reliable task execution",
        "params": {
            "dm_temperature": 0.1,
            "mm_temperature": 0.0,
            "max_tokens": 1024,
            "dm_interval": 2.0,
            "mm_interval": 0.5,
        },
    },
}


def list_providers():
    """List available providers."""
    print("\n📡 Available Providers:\n")
    for key, provider in PROVIDER_PRESETS.items():
        print(f"  {key:12} - {provider['name']}")
        if provider['base_url']:
            print(f"              URL: {provider['base_url']}")
        print(f"              Models: {', '.join(provider['models'].keys())}")
        print()


def list_use_cases():
    """List use case presets."""
    print("\n🎯 Use Case Presets:\n")
    for key, use_case in USE_CASE_PRESETS.items():
        print(f"  {key:12} - {use_case['name']}")
        print(f"              {use_case['description']}")
        print()


def generate_config(
    provider: str,
    use_case: Optional[str] = None,
    model: Optional[str] = None,
    api_key_env: str = "API_KEY",
) -> dict:
    """Generate a configuration dict."""
    if provider not in PROVIDER_PRESETS:
        raise ValueError(f"Unknown provider: {provider}")
    
    preset = PROVIDER_PRESETS[provider]
    
    # Start with provider recommended params
    config = {
        "api_key": f"${{{api_key_env}}}",  # Placeholder
        "base_url": preset["base_url"],
        "model": model or preset["default_model"],
        "system_params": preset["recommended_params"].copy(),
        "memory_path": "./memory_db",
    }
    
    # Apply use case overrides
    if use_case:
        if use_case not in USE_CASE_PRESETS:
            raise ValueError(f"Unknown use case: {use_case}")
        
        use_case_params = USE_CASE_PRESETS[use_case]["params"]
        config["system_params"].update(use_case_params)
    
    # Add default params that might be missing
    defaults = {
        "max_tokens": 1024,
        "dm_interval": 3.0,
        "mm_interval": 1.0,
        "context_compression_threshold": 0.8,
        "sandbox_path": "./sandbox",
        "unsafe_mode": False,
        "log_level": "INFO",
    }
    
    for key, value in defaults.items():
        if key not in config["system_params"]:
            config["system_params"][key] = value
    
    return config


def generate_code(config: dict, provider: str) -> str:
    """Generate Python code for the config."""
    api_key_env = {
        "openai": "OPENAI_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "groq": "GROQ_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "local": "LOCAL_API_KEY",
    }.get(provider, "API_KEY")
    
    base_url_str = f'"{config["base_url"]}"' if config["base_url"] else "None"
    
    params_str = json.dumps(config["system_params"], indent=8, ensure_ascii=False)
    # Fix indentation for inline dict
    params_str = params_str.replace('\n', '\n    ')
    
    code = f'''"""
Auto-generated LivingEntity configuration.
Provider: {PROVIDER_PRESETS[provider]['name']}
"""

import asyncio
import os
from living_entity import LivingCore


async def main():
    # Get API key from environment
    api_key = os.getenv("{api_key_env}")
    if not api_key:
        print("Please set {api_key_env} environment variable")
        return
    
    # Create entity
    entity = LivingCore(
        api_key=api_key,
        base_url={base_url_str},
        model="{config['model']}",
        system_params={params_str},
        memory_path="{config['memory_path']}",
    )
    
    # Register output callback
    @entity.on_output
    def handle_output(text):
        print(f"🤖 Entity: {{text}}")
    
    # Start and interact
    async with entity:
        await entity.input_signal("Hello! What can you help me with?")
        await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
'''
    return code


def interactive_generator():
    """Interactive configuration generator."""
    print("\n" + "=" * 60)
    print("    🛠️ LivingEntity Configuration Generator")
    print("=" * 60 + "\n")
    
    # Select provider
    print("Select provider:")
    providers = list(PROVIDER_PRESETS.keys())
    for i, p in enumerate(providers):
        print(f"  {i+1}. {PROVIDER_PRESETS[p]['name']}")
    
    while True:
        try:
            choice = int(input("\nChoice (1-5): ")) - 1
            if 0 <= choice < len(providers):
                provider = providers[choice]
                break
        except ValueError:
            pass
        print("Invalid choice")
    
    # Select model
    preset = PROVIDER_PRESETS[provider]
    print(f"\nSelect model for {preset['name']}:")
    models = list(preset["models"].keys())
    for i, m in enumerate(models):
        info = preset["models"][m]
        print(f"  {i+1}. {m} (context: {info['context']}, cost: {info['cost']})")
    
    while True:
        try:
            choice = input(f"\nChoice (1-{len(models)}, Enter for default): ").strip()
            if not choice:
                model = preset["default_model"]
                break
            choice = int(choice) - 1
            if 0 <= choice < len(models):
                model = models[choice]
                break
        except ValueError:
            pass
        print("Invalid choice")
    
    # Select use case
    print("\nSelect use case (optional):")
    use_cases = list(USE_CASE_PRESETS.keys())
    print("  0. None (use provider defaults)")
    for i, uc in enumerate(use_cases):
        print(f"  {i+1}. {USE_CASE_PRESETS[uc]['name']}")
    
    while True:
        try:
            choice = input(f"\nChoice (0-{len(use_cases)}): ").strip()
            if not choice or choice == "0":
                use_case = None
                break
            choice = int(choice) - 1
            if 0 <= choice < len(use_cases):
                use_case = use_cases[choice]
                break
        except ValueError:
            pass
        print("Invalid choice")
    
    # Generate
    config = generate_config(provider, use_case, model)
    code = generate_code(config, provider)
    
    print("\n" + "=" * 60)
    print("Generated Configuration:")
    print("=" * 60)
    print(code)
    
    # Save option
    save = input("\nSave to file? (filename or Enter to skip): ").strip()
    if save:
        with open(save, "w") as f:
            f.write(code)
        print(f"Saved to {save}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LivingEntity Configuration Generator")
    parser.add_argument("--list-providers", action="store_true", help="List providers")
    parser.add_argument("--list-use-cases", action="store_true", help="List use cases")
    parser.add_argument("--provider", "-p", help="Provider name")
    parser.add_argument("--use-case", "-u", help="Use case preset")
    parser.add_argument("--model", "-m", help="Model name")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    if args.list_providers:
        list_providers()
        return
    
    if args.list_use_cases:
        list_use_cases()
        return
    
    if args.interactive or not args.provider:
        interactive_generator()
        return
    
    # Generate from arguments
    config = generate_config(args.provider, args.use_case, args.model)
    code = generate_code(config, args.provider)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(code)
        print(f"Configuration saved to {args.output}")
    else:
        print(code)


if __name__ == "__main__":
    main()
