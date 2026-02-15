"""Result formatting utilities."""

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from typing import Optional


class ResultFormatter:
    """Formats query results for display."""
    
    def __init__(self):
        self.console = Console()
    
    def display_results(
        self,
        df: pd.DataFrame,
        title: str = "Query Results",
        max_rows: int = 50,
        max_col_width: int = 50
    ):
        """Display results in a formatted table."""
        if df.empty:
            self.console.print(Panel("No results found.", title=title, style="yellow"))
            return
        
        # Create rich table
        table = Table(title=title, show_lines=True)
        
        # Add columns
        for col in df.columns:
            table.add_column(str(col), overflow="fold", max_width=max_col_width)
        
        # Add rows (limit to max_rows)
        display_df = df.head(max_rows)
        for _, row in display_df.iterrows():
            table.add_row(*[self._truncate(str(val), max_col_width) for val in row])
        
        self.console.print(table)
        
        # Show summary
        if len(df) > max_rows:
            self.console.print(f"\n[dim]Showing {max_rows} of {len(df)} total rows[/dim]")
        else:
            self.console.print(f"\n[dim]Total rows: {len(df)}[/dim]")
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text if too long."""
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text
    
    def display_kql(self, kql: str):
        """Display KQL query with syntax highlighting."""
        syntax = Syntax(kql, "sql", theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title="KQL Query", border_style="blue"))
    
    def display_error(self, message: str):
        """Display error message."""
        self.console.print(Panel(f"[red]{message}[/red]", title="Error", border_style="red"))
    
    def display_info(self, message: str):
        """Display info message."""
        self.console.print(f"[blue]ℹ️ {message}[/blue]")
    
    def display_success(self, message: str):
        """Display success message."""
        self.console.print(f"[green]✅ {message}[/green]")
    
    def display_tables(self, tables: list):
        """Display available tables."""
        table = Table(title="Available Tables")
        table.add_column("Table Name", style="cyan")
        
        for t in tables:
            table.add_row(t)
        
        self.console.print(table)
    
    def display_schema(self, df: pd.DataFrame, table_name: str):
        """Display table schema."""
        table = Table(title=f"Schema for {table_name}")
        table.add_column("Column Name", style="cyan")
        table.add_column("Data Type", style="green")
        
        for _, row in df.iterrows():
            table.add_row(str(row.get('ColumnName', '')), str(row.get('DataType', '')))
        
        self.console.print(table)
    
    def export_to_csv(self, df: pd.DataFrame, filename: str):
        """Export results to CSV."""
        df.to_csv(filename, index=False)
        self.display_success(f"Results exported to {filename}")
    
    def export_to_json(self, df: pd.DataFrame, filename: str):
        """Export results to JSON."""
        df.to_json(filename, orient="records", indent=2)
        self.display_success(f"Results exported to {filename}")
