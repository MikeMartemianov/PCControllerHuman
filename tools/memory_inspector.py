"""
Memory inspector utility for LivingEntity.

Browse and manage the vector memory database.
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Optional

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = BLUE = CYAN = MAGENTA = YELLOW = WHITE = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def print_header():
    """Print header."""
    print("\n" + "=" * 60)
    print(f"{Fore.MAGENTA}{Style.BRIGHT}    📚 LivingEntity Memory Inspector 📚{Style.RESET_ALL}")
    print("=" * 60 + "\n")


def list_memories(memory, limit: int = 20):
    """List all memories."""
    entries = memory.get_all_memories(limit=limit)
    
    print(f"\n{Style.BRIGHT}📋 Все воспоминания ({len(entries)}/{memory.count()}):{Style.RESET_ALL}\n")
    
    for i, entry in enumerate(entries):
        time_str = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        importance = "⭐" * int(entry.importance * 5)
        
        print(f"{Fore.CYAN}[{i+1}] ID: {entry.id}{Style.RESET_ALL}")
        print(f"    📅 {time_str} | 🏷️ {entry.source} | {importance}")
        print(f"    {Fore.WHITE}{entry.text[:80]}{'...' if len(entry.text) > 80 else ''}{Style.RESET_ALL}")
        print()


def search_memories(memory, query: str, threshold: float = 0.5):
    """Search memories."""
    results = memory.retrieve(query, threshold=threshold, max_results=10)
    
    print(f"\n{Style.BRIGHT}🔍 Результаты поиска '{query}':{Style.RESET_ALL}\n")
    
    if not results:
        print(f"{Fore.YELLOW}Ничего не найдено{Style.RESET_ALL}")
        return
    
    for i, result in enumerate(results):
        entry = result.entry
        relevance_pct = int(result.relevance * 100)
        relevance_bar = "█" * (relevance_pct // 10) + "░" * (10 - relevance_pct // 10)
        
        color = Fore.GREEN if result.relevance > 0.7 else Fore.YELLOW if result.relevance > 0.5 else Fore.RED
        
        print(f"{Fore.CYAN}[{i+1}] {color}[{relevance_pct}%] {relevance_bar}{Style.RESET_ALL}")
        print(f"    ID: {entry.id} | Source: {entry.source}")
        print(f"    {Fore.WHITE}{entry.text[:100]}{'...' if len(entry.text) > 100 else ''}{Style.RESET_ALL}")
        print()


def show_stats(memory):
    """Show memory statistics."""
    count = memory.count()
    entries = memory.get_all_memories(limit=1000)
    
    # Calculate stats
    sources = {}
    total_importance = 0
    
    for entry in entries:
        sources[entry.source] = sources.get(entry.source, 0) + 1
        total_importance += entry.importance
    
    avg_importance = total_importance / len(entries) if entries else 0
    
    print(f"\n{Style.BRIGHT}📊 Статистика памяти:{Style.RESET_ALL}\n")
    print(f"  Всего записей: {Fore.CYAN}{count}{Style.RESET_ALL}")
    print(f"  Средняя важность: {Fore.CYAN}{avg_importance:.2f}{Style.RESET_ALL}")
    print(f"\n  По источникам:")
    
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {Fore.WHITE}{source}: {count}{Style.RESET_ALL}")
    
    print()


def delete_memory(memory, memory_id: str):
    """Delete a specific memory."""
    if memory.delete_memory(memory_id):
        print(f"{Fore.GREEN}✓ Удалено: {memory_id}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Не удалось удалить: {memory_id}{Style.RESET_ALL}")


def add_memory(memory, text: str, source: str = "manual", importance: float = 0.5):
    """Add a new memory."""
    memory_id = memory.save_memory(text, source=source, importance=importance)
    print(f"{Fore.GREEN}✓ Добавлено с ID: {memory_id}{Style.RESET_ALL}")


def clear_all(memory):
    """Clear all memories."""
    confirm = input(f"{Fore.RED}Удалить ВСЕ воспоминания? (yes/no): {Style.RESET_ALL}")
    if confirm.lower() == "yes":
        memory.clear()
        print(f"{Fore.GREEN}✓ Все воспоминания удалены{Style.RESET_ALL}")
    else:
        print("Отменено")


def interactive_mode(memory):
    """Run interactive mode."""
    print_header()
    print("Команды: list, search <query>, stats, add <text>, delete <id>, clear, quit\n")
    
    while True:
        try:
            cmd = input(f"{Fore.WHITE}memory> {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not cmd:
            continue
        
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if command == "quit" or command == "exit":
            break
        elif command == "list":
            limit = int(arg) if arg.isdigit() else 20
            list_memories(memory, limit)
        elif command == "search":
            if arg:
                search_memories(memory, arg)
            else:
                print("Usage: search <query>")
        elif command == "stats":
            show_stats(memory)
        elif command == "add":
            if arg:
                add_memory(memory, arg)
            else:
                print("Usage: add <text>")
        elif command == "delete":
            if arg:
                delete_memory(memory, arg)
            else:
                print("Usage: delete <id>")
        elif command == "clear":
            clear_all(memory)
        elif command == "help":
            print("\nCommands:")
            print("  list [n]        - List memories (default 20)")
            print("  search <query>  - Search memories")
            print("  stats           - Show statistics")
            print("  add <text>      - Add new memory")
            print("  delete <id>     - Delete memory by ID")
            print("  clear           - Clear all memories")
            print("  quit            - Exit\n")
        else:
            print(f"Unknown command: {command}")
    
    print("\nДо свидания!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LivingEntity Memory Inspector")
    parser.add_argument("--path", default="./memory_db", help="Memory database path")
    parser.add_argument("--list", action="store_true", help="List all memories")
    parser.add_argument("--search", metavar="QUERY", help="Search memories")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    # Import and create memory
    from living_entity.memory.matrix import MemoryMatrix
    memory = MemoryMatrix(persist_path=args.path)
    
    print(f"Loaded memory from: {args.path}")
    print(f"Total entries: {memory.count()}")
    
    if args.interactive or not any([args.list, args.search, args.stats]):
        interactive_mode(memory)
    else:
        if args.list:
            list_memories(memory)
        if args.search:
            search_memories(memory, args.search)
        if args.stats:
            show_stats(memory)


if __name__ == "__main__":
    main()
