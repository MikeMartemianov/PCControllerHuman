"""
Custom functions example for LivingEntity library.

Demonstrates extending the sandbox with custom functions.
"""

import asyncio
import os
from datetime import datetime

from living_entity import LivingCore, FunctionExecutor


def create_custom_executor() -> FunctionExecutor:
    """
    Create a FunctionExecutor with custom functions.
    
    You can extend the sandbox by creating a custom executor
    and registering additional safe functions.
    """
    executor = FunctionExecutor(sandbox_path="./custom_sandbox")
    
    # The executor uses a restricted globals dict internally
    # To add custom functions, you can subclass FunctionExecutor
    
    return executor


class ExtendedExecutor(FunctionExecutor):
    """
    Extended executor with additional custom functions.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Custom state
        self._notes: list[str] = []
        self._calculation_history: list[tuple[str, float]] = []
    
    def _get_safe_globals(self) -> dict:
        """Override to add custom functions."""
        safe_globals = super()._get_safe_globals()
        
        # Add custom functions
        safe_globals["get_current_time"] = self._get_current_time
        safe_globals["add_note"] = self._add_note
        safe_globals["get_notes"] = self._get_notes
        safe_globals["calculate"] = self._calculate
        safe_globals["get_calc_history"] = self._get_calc_history
        safe_globals["fetch_weather"] = self._mock_fetch_weather
        
        return safe_globals
    
    def _get_current_time(self) -> str:
        """Get current date and time."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _add_note(self, text: str) -> str:
        """Add a note to the internal notebook."""
        self._notes.append(text)
        self.logger.executor(f"Note added: {text}")
        return f"Note added: {text}"
    
    def _get_notes(self) -> list[str]:
        """Get all saved notes."""
        return self._notes.copy()
    
    def _calculate(self, expression: str) -> float:
        """
        Safe calculation of mathematical expressions.
        Uses eval with restricted namespace.
        """
        import math
        
        # Allowed names for calculation
        allowed = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow, "len": len,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
            "pi": math.pi, "e": math.e,
        }
        
        try:
            result = eval(expression, {"__builtins__": {}}, allowed)
            self._calculation_history.append((expression, float(result)))
            return float(result)
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")
    
    def _get_calc_history(self) -> list[tuple[str, float]]:
        """Get calculation history."""
        return self._calculation_history.copy()
    
    def _mock_fetch_weather(self, city: str) -> dict:
        """
        Mock weather API call.
        In real use, you could call an actual weather API here.
        """
        # Simulated weather data
        import random
        
        return {
            "city": city,
            "temperature": random.randint(-10, 35),
            "condition": random.choice(["sunny", "cloudy", "rainy", "snowy"]),
            "humidity": random.randint(30, 90),
            "wind_speed": random.randint(0, 30),
        }
    
    def clear_custom_data(self) -> None:
        """Clear custom data."""
        self._notes.clear()
        self._calculation_history.clear()


async def main():
    """Custom functions demonstration."""
    
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY or CEREBRAS_API_KEY")
        return
    
    # Create extended executor
    custom_executor = ExtendedExecutor(sandbox_path="./custom_sandbox")
    
    # Create entity with custom executor
    entity = LivingCore(
        api_key=api_key,
        base_url=os.getenv("API_BASE_URL"),  # Optional custom base URL
        model=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
        system_params={
            "dm_temperature": 0.5,
            "mm_temperature": 0.2,
        }
    )
    
    # Replace the default executor with our custom one
    entity.executor = custom_executor
    entity.brain.executor = custom_executor
    
    # Update executor output callback
    custom_executor.set_output_callback(lambda text: None)  # Will be set by entity
    
    @entity.on_output
    def handle_output(text):
        print(f"\n🤖 Response: {text}\n")
    
    print("=" * 60)
    print("LivingEntity with Custom Functions")
    print("=" * 60)
    print("\nAvailable functions:")
    print("  - get_current_time() - get current time")
    print("  - add_note(text) - add a note")
    print("  - get_notes() - get all notes")
    print("  - calculate(expr) - evaluate expression")
    print("  - fetch_weather(city) - get weather")
    print("=" * 60)
    
    try:
        await entity.start()
        
        # Test custom function usage
        tasks = [
            "Tell me what time it is now, using the get_current_time() function",
            "Add a note 'Buy milk' using add_note()",
            "Calculate sqrt(144) + pi using the calculate() function",
            "What's the weather in London? Use fetch_weather('London')",
        ]
        
        for task in tasks:
            print(f"\n📤 Task: {task}\n")
            await entity.input_signal(task)
            await asyncio.sleep(8)
        
        # Show notes and history
        print("\n📝 Saved notes:", custom_executor._notes)
        print("📊 Calculation history:", custom_executor._calculation_history)
        
    finally:
        await entity.stop()


if __name__ == "__main__":
    asyncio.run(main())
