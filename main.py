#!/usr/bin/env python3
"""
Azure Log Analytics Analyzer - Interactive CLI

A tool to query Azure Log Analytics using natural language or KQL.
"""

import sys
import argparse
from datetime import timedelta

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from analyzer import LogAnalyzer
from config import Config

console = Console()


WELCOME_MESSAGE = """
# 🔍 Azure Log Analytics Analyzer

Welcome! You can:
- Ask questions in **natural language** (e.g., "show me errors from last hour")
- Run **KQL queries** directly (prefix with `kql:`)
- Use **commands** (type `help` for list)

**Examples:**
- `show me all failed requests in the last 24 hours`
- `what are the top 10 error messages?`
- `kql: AzureActivity | take 10`
- `tables` - list available tables
- `describe AzureActivity` - show table schema
"""

HELP_MESSAGE = """
## Commands

| Command | Description |
|---------|-------------|
| `help` | Show this help message |
| `tables` | List available tables in workspace |
| `describe <table>` | Show schema for a table |
| `kql: <query>` | Execute raw KQL query |
| `export csv <filename>` | Export last results to CSV |
| `export json <filename>` | Export last results to JSON |
| `clear` | Clear the screen |
| `exit` / `quit` | Exit the application |

## Natural Language Examples

- "Show me errors from last hour"
- "What resources were created yesterday?"
- "List all failed sign-in attempts"
- "Show CPU usage for the last 7 days"
- "Count events by type"
"""


def interactive_mode(analyzer: LogAnalyzer):
    """Run the interactive CLI."""
    console.print(Markdown(WELCOME_MESSAGE))
    
    last_results = None
    
    while True:
        try:
            user_input = console.input("\n[bold cyan]Query>[/bold cyan] ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            lower_input = user_input.lower()
            
            if lower_input in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye! 👋[/yellow]")
                break
            
            elif lower_input == "help":
                console.print(Markdown(HELP_MESSAGE))
            
            elif lower_input == "tables":
                analyzer.list_tables()
            
            elif lower_input.startswith("describe "):
                table_name = user_input[9:].strip()
                analyzer.describe_table(table_name)
            
            elif lower_input.startswith("kql:"):
                kql = user_input[4:].strip()
                last_results = analyzer.query(kql)
            
            elif lower_input.startswith("export csv "):
                if last_results is not None and not last_results.empty:
                    filename = user_input[11:].strip()
                    analyzer.export(last_results, filename, "csv")
                else:
                    console.print("[yellow]No results to export. Run a query first.[/yellow]")
            
            elif lower_input.startswith("export json "):
                if last_results is not None and not last_results.empty:
                    filename = user_input[12:].strip()
                    analyzer.export(last_results, filename, "json")
                else:
                    console.print("[yellow]No results to export. Run a query first.[/yellow]")
            
            elif lower_input == "clear":
                console.clear()
            
            else:
                # Natural language query
                last_results = analyzer.ask(user_input)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def single_query_mode(analyzer: LogAnalyzer, query: str, is_kql: bool = False):
    """Execute a single query and exit."""
    if is_kql:
        analyzer.query(query)
    else:
        analyzer.ask(query)


def main():
    parser = argparse.ArgumentParser(
        description="Azure Log Analytics Analyzer - Query logs using natural language or KQL"
    )
    parser.add_argument(
        "-q", "--query",
        help="Execute a single natural language query"
    )
    parser.add_argument(
        "-k", "--kql",
        help="Execute a single KQL query"
    )
    parser.add_argument(
        "-w", "--workspace",
        help="Log Analytics Workspace ID (overrides env variable)"
    )
    parser.add_argument(
        "--list-tables",
        action="store_true",
        help="List available tables and exit"
    )
    
    args = parser.parse_args()
    
    # Override workspace ID if provided
    if args.workspace:
        Config.WORKSPACE_ID = args.workspace
    
    try:
        analyzer = LogAnalyzer()
        
        if args.list_tables:
            analyzer.list_tables()
        elif args.kql:
            single_query_mode(analyzer, args.kql, is_kql=True)
        elif args.query:
            single_query_mode(analyzer, args.query, is_kql=False)
        else:
            interactive_mode(analyzer)
    
    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("\n[yellow]Please set up your .env file with the required configuration.[/yellow]")
        console.print("Copy .env.example to .env and fill in your Azure details.")
        sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
