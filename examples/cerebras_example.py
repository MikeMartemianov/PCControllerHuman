"""
Cerebras provider example for LivingEntity library.

Demonstrates using the ultra-fast Cerebras inference API.
The AI runs continuously until entity.stop() is called.
"""

import asyncio
import os
from living_entity import LivingCore


# Example personality text
PERSONALITY = """
My name is Ava. I am friendly and curious.
I love helping people and learning new things.
I enjoy programming in Python.
I try to be polite and respectful.
If I don't know something - I honestly admit it.
I value giving accurate and helpful answers.
"""


async def main():
    """Cerebras provider demonstration."""
    
    # Get Cerebras API key from environment
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ Please set CEREBRAS_API_KEY environment variable")
        return
    
    # Create entity with personality
    entity = LivingCore(
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
        model="gpt-oss-120b",
        system_params={
            "dm_temperature": 0.5,
            "mm_temperature": 0.4,
            "max_tokens": 1024,
            # AI operating intervals
            "dm_interval": 3.0,   # Spirit thinks every 3 sec
            "mm_interval": 0.5,   # Brain responds every 0.5 sec
        },
        personality_text=PERSONALITY,
    )
    
    # Register output handler
    @entity.on_output
    def handle_speech(text):
        print(f"\n🚀 Ava says: {text}\n")
    
    print("=" * 60)
    print("LivingEntity - Autonomous Mode")
    print("=" * 60)
    print("AI runs continuously until entity.stop() is called")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Start the entity
    await entity.start()
    
    # Send initial message
    await entity.input_signal("Hello! What is your name?")
    
    # AI runs continuously in background
    # You can send signals at any time
    try:
        # Example: send another signal after 10 seconds
        await asyncio.sleep(10)
        await entity.input_signal("What do you like?")
        
        # AI continues running...
        # Wait another 10 seconds
        await asyncio.sleep(10)
        await entity.input_signal("Tell me something interesting")
        
        # Can wait indefinitely - AI will think and respond
        # In a real app, any logic can be here
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        print("\n⚠️ Stopping via Ctrl+C...")
    
    finally:
        # IMPORTANT: call stop() to stop the AI
        await entity.stop()
        
        print("\n" + "=" * 60)
        print("Session ended")
        print(f"Memories: {entity.get_memory_count()}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
