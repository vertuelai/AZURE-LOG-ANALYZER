"""Main Azure Log Analytics Analyzer."""

from datetime import timedelta
from typing import Optional
import pandas as pd

from azure_client import AzureLogAnalyticsClient
from query_translator import QueryTranslator
from result_formatter import ResultFormatter
from config import Config


class LogAnalyzer:
    """Main analyzer class for Azure Log Analytics."""
    
    def __init__(self):
        Config.validate()
        self.client = AzureLogAnalyticsClient()
        self.translator = QueryTranslator()
        self.formatter = ResultFormatter()
        self._available_tables = None
    
    @property
    def available_tables(self) -> list:
        """Get available tables (cached)."""
        if self._available_tables is None:
            self._available_tables = self.client.get_available_tables()
        return self._available_tables
    
    def ask(self, question: str, show_kql: bool = True) -> pd.DataFrame:
        """
        Ask a question in natural language and get results.
        
        Args:
            question: Natural language question
            show_kql: Whether to display the generated KQL
            
        Returns:
            DataFrame with results
        """
        self.formatter.display_info(f"Processing: {question}")
        
        # Translate to KQL
        kql = self.translator.translate(question, self.available_tables)
        
        if show_kql:
            self.formatter.display_kql(kql)
        
        # Execute query
        try:
            df = self.client.query(kql)
            self.formatter.display_results(df, title="Results")
            return df
        except Exception as e:
            self.formatter.display_error(str(e))
            return pd.DataFrame()
    
    def query(
        self,
        kql: str,
        timespan: Optional[timedelta] = None
    ) -> pd.DataFrame:
        """
        Execute a raw KQL query.
        
        Args:
            kql: KQL query string
            timespan: Optional time range
            
        Returns:
            DataFrame with results
        """
        self.formatter.display_kql(kql)
        
        try:
            df = self.client.query(kql, timespan=timespan)
            self.formatter.display_results(df, title="Results")
            return df
        except Exception as e:
            self.formatter.display_error(str(e))
            return pd.DataFrame()
    
    def list_tables(self):
        """List all available tables in the workspace."""
        self.formatter.display_tables(self.available_tables)
    
    def describe_table(self, table_name: str):
        """Show schema for a specific table."""
        try:
            df = self.client.get_table_schema(table_name)
            self.formatter.display_schema(df, table_name)
        except Exception as e:
            self.formatter.display_error(str(e))
    
    def export(self, df: pd.DataFrame, filename: str, format: str = "csv"):
        """Export results to file."""
        if format.lower() == "csv":
            self.formatter.export_to_csv(df, filename)
        elif format.lower() == "json":
            self.formatter.export_to_json(df, filename)
        else:
            self.formatter.display_error(f"Unknown format: {format}. Use 'csv' or 'json'.")


# Convenience functions for interactive use
_analyzer = None


def get_analyzer() -> LogAnalyzer:
    """Get or create the global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = LogAnalyzer()
    return _analyzer


def ask(question: str) -> pd.DataFrame:
    """Ask a question in natural language."""
    return get_analyzer().ask(question)


def query(kql: str) -> pd.DataFrame:
    """Execute a raw KQL query."""
    return get_analyzer().query(kql)


def tables():
    """List available tables."""
    get_analyzer().list_tables()


def describe(table_name: str):
    """Describe a table's schema."""
    get_analyzer().describe_table(table_name)
