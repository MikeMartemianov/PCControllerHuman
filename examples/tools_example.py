"""
Custom Tools Example - Demonstrates registering custom tools for the AI.

Shows how to add custom functions that the AI can call.
"""

import asyncio
import os
from living_entity import LivingCore


# Personality for our assistant
PERSONALITY = """
My name is Assistant. I can:
- Calculate mathematical expressions
- Work with files
- Search for information
I always try to use tools when needed.
"""


async def main():
    """Custom tools demonstration."""
    
    # Get API key
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("Please set CEREBRAS_API_KEY environment variable")
        return
    
    # Create entity
    entity = LivingCore(
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
        model="gpt-oss-120b",
        system_params={
            "dm_temperature": 0.5,
            "mm_temperature": 0.4,
        },
        personality_text=PERSONALITY,
    )
    
    # =========================================
    # Register custom tools
    # =========================================
    
    # Method 1: Using decorator
    @entity.register_tool(
        description="Calculate a mathematical expression",
        parameters={"expression": "Math expression (e.g.: 2+2*3)"},
        returns="Calculation result"
    )
    def calculate(expression: str) -> str:
        """Safe math evaluation."""
        try:
            # Only allow safe math operations
            allowed = set('0123456789+-*/().  ')
            if not all(c in allowed for c in expression):
                return f"Error: invalid characters in expression"
            result = eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Calculation error: {e}"
    
    # Method 2: Using direct registration
    def get_weather(city: str) -> str:
        """Get weather for a city (mock implementation)."""
        # In real app, this would call a weather API
        return f"Weather in {city}: +22°C, sunny"
    
    entity.register_tool(
        get_weather,
        description="Get weather for a city",
        parameters={"city": "City name"},
        returns="Weather information"
    )
    
    # Method 3: Lambda function
    entity.register_tool(
        lambda name: f"Hello, {name}! How are you?",
        name="greet",
        description="Greet the user by name",
        parameters={"name": "User's name"},
        returns="Greeting message"
    )
    
    # =========================================
    # Show registered tools
    # =========================================
    
    print("=" * 60)
    print("Registered Tools")
    print("=" * 60)
    print(f"\nTotal tools: {len(entity.list_tools())}")
    print("\nTools list:")
    for tool_name in entity.list_tools():
        print(f"  - {tool_name}")
    
    print("\n" + "=" * 60)
    print("Tools Description (for AI):")
    print("=" * 60)
    print(entity.get_tools_description())
    
    # =========================================
    # Test tool execution directly
    # =========================================
    
    print("\n" + "=" * 60)
    print("Direct Tool Execution Test")
    print("=" * 60)
    
    # Execute tools directly
    result = entity.execute_tool("calculate", expression="2 + 2 * 3")
    print(f"\ncalculate('2 + 2 * 3'): {result}")
    
    result = entity.execute_tool("get_weather", city="London")
    print(f"get_weather('London'): {result}")
    
    result = entity.execute_tool("greet", name="John")
    print(f"greet('John'): {result}")
    
    result = entity.execute_tool("get_time")
    print(f"get_time(): {result}")
    
    # =========================================
    # Test with AI (if API key is available)
    # =========================================
    
    if api_key:
        print("\n" + "=" * 60)
        print("AI Tool Usage Test")
        print("=" * 60)
        
        @entity.on_output
        def handle_output(text):
            print(f"\n🤖 Assistant: {text}\n")
        
        try:
            await entity.start()
            
            # Test AI using tools
            print("\n📤 Signal: 'How much is 15 * 7?'\n")
            await entity.input_signal("How much is 15 * 7?")
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await entity.stop()
    else:
        print("\n⚠️ Set CEREBRAS_API_KEY for AI test")
    
    print("\n" + "=" * 60)
    print("Demonstration complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
