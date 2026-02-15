"""Natural language to KQL query translator."""

from typing import Optional
import json

from config import Config


class QueryTranslator:
    """Translates natural language queries to KQL."""
    
    SYSTEM_PROMPT = """You are an expert at translating natural language queries into KQL (Kusto Query Language) for Azure Log Analytics.

Your task: Convert ANY user question about Azure logs into a valid KQL query. Be flexible and understand various phrasings.

Common Azure Log Analytics tables and their use cases:
- AppServiceHTTPLogs: Azure App Service HTTP request/response logs (web apps, APIs)
- AppServiceConsoleLogs: App Service console output and application logs
- AppServiceAppLogs: Application-level logs from App Service
- AppServicePlatformLogs: Platform-level App Service logs
- AppServiceFileAuditLogs: File system audit logs for App Service
- FunctionAppLogs: Azure Functions execution logs
- AzureActivity: Azure subscription activity/audit logs (who did what)
- AzureDiagnostics: Diagnostic logs from Azure resources (generic)
- AzureMetrics: Metrics from Azure resources
- Heartbeat: Agent heartbeat/health data
- Perf: Performance counters (CPU, memory, disk)
- Event: Windows Event logs
- Syslog: Linux syslog messages
- SecurityEvent: Security events and alerts
- SigninLogs: Azure AD sign-in logs
- AuditLogs: Azure AD audit logs
- AppTraces: Application Insights traces
- AppRequests: Application Insights HTTP requests
- AppExceptions: Application Insights exceptions
- AppDependencies: Application Insights dependency calls
- ContainerLog: Container/Kubernetes logs from AKS
- KubeEvents: Kubernetes events
- VMConnection: VM connection data
- Update: Update management logs
- SQLSecurityAuditEvents: SQL audit logs

Query interpretation guidelines:
- "app service logs" or "web app logs" → Use AppServiceHTTPLogs or AppServiceConsoleLogs
- "function logs" → Use FunctionAppLogs
- "errors" or "failures" → Filter by Level == 'Error' or Success == false
- "slow requests" or "performance" → Look for requests with high duration
- "who created/deleted/modified" → Use AzureActivity
- "sign ins" or "logins" → Use SigninLogs
- "last hour/day/week" → Use appropriate ago() function

KQL Best Practices:
1. Always use 'where' to filter early
2. Use 'project' to select only needed columns  
3. Use 'summarize' for aggregations
4. Use 'order by' for sorting (usually by TimeGenerated desc)
5. Use 'take' or 'limit' to restrict results (default to 100)
6. Time filters: TimeGenerated > ago(1h), ago(24h), ago(7d)

IMPORTANT: 
- Respond ONLY with valid KQL query - no explanations, no markdown, no code blocks
- If the user's request is vague, make reasonable assumptions and pick the most likely table
- Always include a time filter (default: last 24 hours) and a result limit (default: 100)
- Never return an error unless absolutely impossible to interpret
"""

    COMMON_QUERIES = {
        "errors": "AzureDiagnostics | where Level == 'Error' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "failed requests": "AppRequests | where Success == false | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "exceptions": "AppExceptions | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "activity": "AzureActivity | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "heartbeat": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer | order by LastHeartbeat desc | take 100",
        "performance": "Perf | where ObjectName == 'Processor' and CounterName == '% Processor Time' | where TimeGenerated > ago(1h) | summarize avg(CounterValue) by Computer, bin(TimeGenerated, 5m)",
        "security events": "SecurityEvent | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "container logs": "ContainerLog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "app service": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "app service logs": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "web app": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "function logs": "FunctionAppLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "sign in": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "login": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
    }

    def __init__(self):
        self.client = self._create_openai_client()
    
    def _create_openai_client(self):
        """Create Azure OpenAI client if configured."""
        if Config.AZURE_OPENAI_ENDPOINT and Config.AZURE_OPENAI_KEY:
            from openai import AzureOpenAI
            return AzureOpenAI(
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_key=Config.AZURE_OPENAI_KEY,
                api_version="2024-02-15-preview"
            )
        return None
    
    def translate(self, natural_language_query: str, available_tables: Optional[list] = None) -> str:
        """
        Translate natural language to KQL.
        
        Args:
            natural_language_query: The query in natural language
            available_tables: List of available tables in the workspace
            
        Returns:
            KQL query string
            
        Raises:
            ValueError: If Azure OpenAI is not configured
        """
        # Check for common query shortcuts
        query_lower = natural_language_query.lower().strip()
        for keyword, kql in self.COMMON_QUERIES.items():
            if keyword in query_lower:
                return kql
        
        # If OpenAI is not configured, raise an error
        if not self.client:
            raise ValueError(
                "Azure OpenAI is not configured. Please set AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_KEY, and AZURE_OPENAI_DEPLOYMENT environment variables."
            )
        
        # Use AI for translation
        return self._ai_translate(natural_language_query, available_tables)
    
    def _pattern_based_translation(self, query: str) -> str:
        """Simple pattern-based translation without AI."""
        query_lower = query.lower()
        
        # Extract time mentions
        time_filter = "| where TimeGenerated > ago(24h)"
        if "last hour" in query_lower:
            time_filter = "| where TimeGenerated > ago(1h)"
        elif "last 7 days" in query_lower or "last week" in query_lower:
            time_filter = "| where TimeGenerated > ago(7d)"
        elif "last 30 days" in query_lower or "last month" in query_lower:
            time_filter = "| where TimeGenerated > ago(30d)"
        
        # Detect table
        table = "AzureDiagnostics"
        if any(word in query_lower for word in ["activity", "subscription", "resource changes"]):
            table = "AzureActivity"
        elif any(word in query_lower for word in ["app", "application", "request"]):
            table = "AppRequests"
        elif any(word in query_lower for word in ["exception", "crash", "error"]):
            table = "AppExceptions"
        elif any(word in query_lower for word in ["security", "login", "authentication"]):
            table = "SecurityEvent"
        elif any(word in query_lower for word in ["container", "kubernetes", "k8s", "aks"]):
            table = "ContainerLog"
        elif any(word in query_lower for word in ["performance", "cpu", "memory", "disk"]):
            table = "Perf"
        
        # Build basic query
        return f"{table} {time_filter} | take 100"
    
    def _ai_translate(self, query: str, available_tables: Optional[list] = None) -> str:
        """Use AI to translate the query."""
        context = ""
        if available_tables:
            context = f"\n\nAvailable tables in this workspace: {', '.join(available_tables)}"
        
        try:
            response = self.client.chat.completions.create(
                model=Config.AZURE_OPENAI_DEPLOYMENT or "gpt-4",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT + context},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=500
            )
            
            kql = response.choices[0].message.content.strip()
            
            # Remove code blocks if present
            if kql.startswith("```"):
                lines = kql.split("\n")
                kql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            if kql.startswith("ERROR:"):
                raise ValueError(kql)
            
            return kql
            
        except Exception as e:
            # Fall back to pattern matching
            print(f"⚠️ AI translation failed: {e}. Using pattern matching.")
            return self._pattern_based_translation(query)
