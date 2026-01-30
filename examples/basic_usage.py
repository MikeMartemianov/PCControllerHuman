"""
Basic usage example for LivingEntity library.
"""

import asyncio
import os
from living_entity import LivingCore


async def main():
    """Basic usage demonstration."""
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    # Create entity with default OpenAI configuration
    entity = LivingCore(
        api_key=api_key,
        model="gpt-3.5-turbo",
        system_params={
            "dm_temperature": 0.7,
            "mm_temperature": 0.3,
            "max_tokens": 1024,
        }
    )
    
    # Register output callback
    @entity.on_output
    def handle_output(text):
        print(f"\n🤖 Entity: {text}\n")
    
    # Optional: Register thought callback for debugging
    @entity.on_thought
    def handle_thought(thought):
        print(f"💭 [Spirit thinking]: {thought}")
    
    try:
        # Start the entity
        print("Starting LivingEntity...")
        await entity.start()
        
        # Send a greeting
        print("\n📤 Sending signal: 'Hello! Who are you and what can you do?'\n")
        await entity.input_signal("Hello! Who are you and what can you do?")
        
        # Wait for processing
        await asyncio.sleep(15)
        
        # Send another message
        print("\n📤 Sending signal: 'Remember that my name is Alex'\n")
        await entity.input_signal("Remember that my name is Alex")
        
        await asyncio.sleep(10)
        
        # Check memory
        print("\n📤 Sending signal: 'What is my name?'\n")
        await entity.input_signal("What is my name?")
        
        await asyncio.sleep(10)
        
    finally:
        # Stop the entity
        await entity.stop()
        print("\nEntity stopped.")
        print(f"Total memories: {entity.get_memory_count()}")


if __name__ == "__main__":
    asyncio.run(main())
