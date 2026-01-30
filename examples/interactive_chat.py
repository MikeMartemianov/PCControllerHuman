"""
Interactive Chat Mode - Continuous conversation until 'stop' command.

Runs the AI in a loop, accepting user input continuously.
"""

import asyncio
import os
import sys
from living_entity import LivingCore


# Personality for our assistant
PERSONALITY = """
My name is Ava. I am a friendly and curious AI assistant.
I love helping people and learning new things.
I enjoy programming in Python.
I try to be polite and respectful.
If I don't know something - I honestly admit it.
I value giving accurate and helpful answers.
"""


async def main():
    """Interactive chat demonstration."""
    
    # Get API key
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ Please set CEREBRAS_API_KEY environment variable or in .env")
        return
    
    # Create entity
    entity = LivingCore(
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
        model="gpt-oss-120b",
        system_params={
            "dm_temperature": 0.5,
            "mm_temperature": 0.4,
            "dm_interval": 3.0,  # Spirit thinks every 3 seconds
            "mm_interval": 0.5,  # Brain responds every 0.5 seconds
        },
        personality_text=PERSONALITY,
    )
    
    # Output handler
    @entity.on_output
    def handle_output(text):
        print(f"\n🤖 Ava: {text}\n")
        print("You: ", end="", flush=True)
    
    print("=" * 60)
    print("🌟 Interactive Chat with Ava")
    print("=" * 60)
    print("Commands:")
    print("  stop, exit, quit - end chat")
    print("  clear - clear context")
    print("  memory - show memory count")
    print("=" * 60)
    
    try:
        # Start the entity
        await entity.start()
        print("\n✅ Ava is ready to chat!\n")
        
        # Main interaction loop
        while True:
            try:
                # Get user input
                print("You: ", end="", flush=True)
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ["stop", "exit", "quit", "q"]:
                    print("\n👋 Goodbye!")
                    break
                
                # Check for special commands
                if user_input.lower() == "clear":
                    entity.clear_all()
                    print("🧹 Context cleared\n")
                    continue
                
                if user_input.lower() == "memory":
                    count = entity.get_memory_count()
                    print(f"🧠 Memories: {count}\n")
                    continue
                
                if user_input.lower() == "tools":
                    print(f"🔧 Tools: {entity.list_tools()}\n")
                    continue
                
                # Send to AI
                await entity.input_signal(user_input)
                
                # Wait for response (Spirit needs time to process)
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user")
                break
            except EOFError:
                break
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    finally:
        await entity.stop()
        print("\n" + "=" * 60)
        print("Session ended")
        print(f"Memories: {entity.get_memory_count()}")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTerminated")
