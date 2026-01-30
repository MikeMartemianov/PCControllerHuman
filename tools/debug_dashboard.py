"""
Debug dashboard for LivingEntity - Real-time monitoring utility.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
except ImportError:
    print("Warning: colorama not installed. Colors disabled.")
    class Fore:
        RED = GREEN = BLUE = CYAN = MAGENTA = YELLOW = WHITE = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""
    class Back:
        BLACK = ""


class DebugDashboard:
    """
    Real-time debug dashboard for monitoring LivingEntity.
    
    Displays:
    - Spirit thoughts in real-time
    - Brain actions
    - Memory operations
    - System status
    """
    
    def __init__(self, entity=None):
        """
        Initialize the dashboard.
        
        :param entity: Optional LivingCore instance to monitor
        """
        self.entity = entity
        self._running = False
        
        # Log buffers
        self._thoughts: list[tuple[datetime, str]] = []
        self._actions: list[tuple[datetime, str]] = []
        self._outputs: list[tuple[datetime, str]] = []
        self._errors: list[tuple[datetime, str]] = []
        
        # Limits
        self._max_buffer = 50
        
        # Stats
        self._thought_count = 0
        self._action_count = 0
        self._output_count = 0
        self._error_count = 0
    
    def attach(self, entity) -> None:
        """Attach to a LivingCore entity."""
        self.entity = entity
        
        # Register callbacks
        @entity.on_thought
        def on_thought(text):
            self._add_thought(text)
        
        @entity.on_action
        def on_action(action):
            self._add_action(f"{action.type}: {action.content[:50]}...")
        
        @entity.on_output
        def on_output(text):
            self._add_output(text)
    
    def _add_thought(self, text: str) -> None:
        """Add a thought to the buffer."""
        self._thoughts.append((datetime.now(), text))
        self._thought_count += 1
        if len(self._thoughts) > self._max_buffer:
            self._thoughts.pop(0)
        self._display_thought(text)
    
    def _add_action(self, text: str) -> None:
        """Add an action to the buffer."""
        self._actions.append((datetime.now(), text))
        self._action_count += 1
        if len(self._actions) > self._max_buffer:
            self._actions.pop(0)
        self._display_action(text)
    
    def _add_output(self, text: str) -> None:
        """Add an output to the buffer."""
        self._outputs.append((datetime.now(), text))
        self._output_count += 1
        if len(self._outputs) > self._max_buffer:
            self._outputs.pop(0)
        self._display_output(text)
    
    def _add_error(self, text: str) -> None:
        """Add an error to the buffer."""
        self._errors.append((datetime.now(), text))
        self._error_count += 1
        if len(self._errors) > self._max_buffer:
            self._errors.pop(0)
        self._display_error(text)
    
    def _timestamp(self) -> str:
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def _display_thought(self, text: str) -> None:
        """Display a thought."""
        print(f"{Fore.CYAN}[{self._timestamp()}] 💭 THOUGHT: {text}{Style.RESET_ALL}")
    
    def _display_action(self, text: str) -> None:
        """Display an action."""
        print(f"{Fore.GREEN}[{self._timestamp()}] ⚡ ACTION: {text}{Style.RESET_ALL}")
    
    def _display_output(self, text: str) -> None:
        """Display an output."""
        print(f"{Fore.YELLOW}[{self._timestamp()}] 📢 OUTPUT: {text}{Style.RESET_ALL}")
    
    def _display_error(self, text: str) -> None:
        """Display an error."""
        print(f"{Fore.RED}[{self._timestamp()}] ❌ ERROR: {text}{Style.RESET_ALL}")
    
    def print_header(self) -> None:
        """Print dashboard header."""
        print("\n" + "=" * 70)
        print(f"{Fore.CYAN}{Style.BRIGHT}    🧠 LivingEntity Debug Dashboard 🧠{Style.RESET_ALL}")
        print("=" * 70)
        print(f"{Fore.WHITE}Мониторинг в реальном времени")
        print(f"  💭 Cyan  = Spirit thoughts (Дух)")
        print(f"  ⚡ Green = Brain actions (Мозг)")
        print(f"  📢 Yellow = Entity outputs")
        print(f"  ❌ Red   = Errors")
        print("=" * 70 + "\n")
    
    def print_stats(self) -> None:
        """Print current statistics."""
        print("\n" + "-" * 50)
        print(f"{Style.BRIGHT}📊 Statistics:{Style.RESET_ALL}")
        print(f"  Thoughts: {self._thought_count}")
        print(f"  Actions:  {self._action_count}")
        print(f"  Outputs:  {self._output_count}")
        print(f"  Errors:   {self._error_count}")
        
        if self.entity:
            print(f"  Memories: {self.entity.get_memory_count()}")
            print(f"  Running:  {self.entity.is_running()}")
        
        print("-" * 50 + "\n")
    
    def print_recent(self, count: int = 5) -> None:
        """Print recent events."""
        print("\n" + "-" * 50)
        print(f"{Style.BRIGHT}📜 Recent Events:{Style.RESET_ALL}")
        
        # Combine and sort
        all_events = []
        for ts, text in self._thoughts[-count:]:
            all_events.append((ts, "thought", text))
        for ts, text in self._actions[-count:]:
            all_events.append((ts, "action", text))
        for ts, text in self._outputs[-count:]:
            all_events.append((ts, "output", text))
        
        all_events.sort(key=lambda x: x[0])
        
        for ts, event_type, text in all_events[-count:]:
            time_str = ts.strftime("%H:%M:%S")
            if event_type == "thought":
                print(f"  {Fore.CYAN}[{time_str}] 💭 {text[:60]}...{Style.RESET_ALL}")
            elif event_type == "action":
                print(f"  {Fore.GREEN}[{time_str}] ⚡ {text[:60]}...{Style.RESET_ALL}")
            elif event_type == "output":
                print(f"  {Fore.YELLOW}[{time_str}] 📢 {text[:60]}...{Style.RESET_ALL}")
        
        print("-" * 50 + "\n")


async def interactive_session(api_key: str, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo"):
    """Run an interactive debugging session."""
    from living_entity import LivingCore
    
    # Create entity
    entity = LivingCore(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system_params={
            "dm_temperature": 0.5,
            "mm_temperature": 0.2,
            "log_level": "DEBUG",
        }
    )
    
    # Create and attach dashboard
    dashboard = DebugDashboard()
    dashboard.attach(entity)
    dashboard.print_header()
    
    try:
        await entity.start()
        print(f"{Fore.GREEN}✓ Entity started{Style.RESET_ALL}\n")
        
        print("Commands: 'stats', 'recent', 'memory <query>', 'quit'")
        print("Or type any message to send to the entity.\n")
        
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, f"{Fore.WHITE}> {Style.RESET_ALL}"
                )
            except EOFError:
                break
            
            user_input = user_input.strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                break
            elif user_input.lower() == "stats":
                dashboard.print_stats()
            elif user_input.lower() == "recent":
                dashboard.print_recent()
            elif user_input.lower().startswith("memory "):
                query = user_input[7:]
                results = entity.search_memory(query)
                print(f"\n{Style.BRIGHT}Memory search: '{query}'{Style.RESET_ALL}")
                for r in results:
                    print(f"  [{r.relevance:.2f}] {r.entry.text[:60]}...")
                print()
            else:
                # Send as input signal
                print(f"{Fore.BLUE}📤 Sending: {user_input}{Style.RESET_ALL}\n")
                await entity.input_signal(user_input)
                # Wait a bit for processing
                await asyncio.sleep(0.5)
        
    finally:
        await entity.stop()
        print(f"\n{Fore.GREEN}✓ Entity stopped{Style.RESET_ALL}")
        dashboard.print_stats()


def main():
    """Main entry point for the debug dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LivingEntity Debug Dashboard")
    parser.add_argument("--api-key", help="API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--base-url", help="API base URL for alternative providers")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="Model name")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("CEREBRAS_API_KEY")
    
    if not api_key:
        print("Error: No API key provided.")
        print("Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    asyncio.run(interactive_session(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
    ))


if __name__ == "__main__":
    main()
