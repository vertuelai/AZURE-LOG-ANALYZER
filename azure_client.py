"""Azure Log Analytics client wrapper."""

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.core.exceptions import HttpResponseError

from config import Config


class AzureLogAnalyticsClient:
    """Client for querying Azure Log Analytics workspace."""
    
    def __init__(self):
        self.workspace_id = Config.WORKSPACE_ID
        self.client = self._create_client()
    
    def _create_client(self) -> LogsQueryClient:
        """Create the Log Analytics client with appropriate credentials."""
        # Try Service Principal first, then fall back to DefaultAzureCredential
        if Config.TENANT_ID and Config.CLIENT_ID and Config.CLIENT_SECRET:
            credential = ClientSecretCredential(
                tenant_id=Config.TENANT_ID,
                client_id=Config.CLIENT_ID,
                client_secret=Config.CLIENT_SECRET
            )
        else:
            # Uses Azure CLI, Managed Identity, VS Code, etc.
            credential = DefaultAzureCredential()
        
        return LogsQueryClient(credential)
    
    def query(
        self,
        kql_query: str,
        timespan: Optional[timedelta] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Execute a KQL query against Log Analytics.
        
        Args:
            kql_query: The KQL query to execute
            timespan: Time range as timedelta (e.g., timedelta(days=1))
            start_time: Start time for the query
            end_time: End time for the query
            
        Returns:
            pandas DataFrame with query results
        """
        # Default to last 24 hours if no time specified
        if timespan is None and start_time is None:
            timespan = timedelta(days=1)
        
        try:
            if start_time and end_time:
                response = self.client.query_workspace(
                    workspace_id=self.workspace_id,
                    query=kql_query,
                    timespan=(start_time, end_time)
                )
            else:
                response = self.client.query_workspace(
                    workspace_id=self.workspace_id,
                    query=kql_query,
                    timespan=timespan
                )
            
            if response.status == LogsQueryStatus.SUCCESS:
                table = response.tables[0]
                return pd.DataFrame(
                    data=table.rows,
                    columns=table.columns
                )
            elif response.status == LogsQueryStatus.PARTIAL:
                table = response.partial_data[0]
                print(f"⚠️ Partial results returned. Error: {response.partial_error}")
                return pd.DataFrame(
                    data=table.rows,
                    columns=table.columns
                )
            else:
                raise Exception(f"Query failed with status: {response.status}")
                
        except HttpResponseError as e:
            raise Exception(f"Azure API Error: {e.message}")
    
    def get_available_tables(self) -> list:
        """Get list of available tables in the workspace."""
        query = """
        search *
        | distinct $table
        | order by $table asc
        """
        try:
            df = self.query(query, timespan=timedelta(days=1))
            return df['$table'].tolist() if not df.empty else []
        except Exception:
            # Fallback: return common tables
            return [
                "AzureActivity",
                "AzureDiagnostics", 
                "AzureMetrics",
                "Heartbeat",
                "Perf",
                "Event",
                "Syslog",
                "SecurityEvent",
                "AppTraces",
                "AppRequests",
                "AppExceptions",
                "ContainerLog",
                "KubeEvents"
            ]
    
    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """Get schema information for a specific table."""
        query = f"""
        {table_name}
        | getschema
        """
        return self.query(query, timespan=timedelta(hours=1))
