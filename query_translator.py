"""Natural language to KQL query translator."""

from typing import Optional
import json

from config import Config


class QueryTranslator:
    """Translates natural language queries to KQL."""
    
    SYSTEM_PROMPT = """You are an expert KQL (Kusto Query Language) translator for Azure Log Analytics. Your ONLY job is to convert natural language into valid KQL queries.

## COMPREHENSIVE AZURE LOG ANALYTICS TABLES REFERENCE:

### App Service & Web Apps
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| AppServiceHTTPLogs | HTTP request/response logs | "web app logs", "app service requests", "http logs", "website traffic" |
| AppServiceConsoleLogs | Console output logs | "console logs", "stdout", "application output" |
| AppServiceAppLogs | Application-level logs | "app logs", "application logs" |
| AppServiceAuditLogs | Audit logs for App Service | "app service audit" |
| AppServiceFileAuditLogs | File system audit | "file audit", "file changes" |
| AppServicePlatformLogs | Platform logs | "platform logs", "app service platform" |
| AppServiceEnvironmentPlatformLogs | ASE platform logs | "app service environment" |
| AppServiceAntivirusScanAuditLogs | Antivirus scan logs | "antivirus", "malware scan" |
| AppServiceAuthenticationLogs | Authentication logs | "app auth logs" |

### Azure Functions
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| FunctionAppLogs | Function execution logs | "function logs", "azure functions", "serverless logs" |

### Application Insights
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| AppTraces | Application traces | "traces", "app traces", "trace logs" |
| AppRequests | HTTP requests | "requests", "http requests", "api calls" |
| AppExceptions | Exceptions/errors | "exceptions", "errors", "crashes", "failures" |
| AppDependencies | External dependencies | "dependencies", "external calls", "outbound requests" |
| AppEvents | Custom events | "custom events", "app events" |
| AppMetrics | Application metrics | "app metrics", "application metrics" |
| AppPageViews | Page views | "page views", "user visits" |
| AppBrowserTimings | Browser performance | "browser timing", "page load time" |
| AppPerformanceCounters | Performance counters | "perf counters" |
| AppAvailabilityResults | Availability tests | "availability", "health checks", "ping tests" |
| AppSystemEvents | System events | "system events" |

### Azure Activity & Management
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| AzureActivity | Subscription activity | "activity logs", "audit logs", "who did what", "resource changes", "deployments" |
| AzureDiagnostics | Resource diagnostics | "diagnostics", "resource logs" |
| AzureMetrics | Resource metrics | "metrics", "azure metrics" |

### Security & Identity
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| SigninLogs | Azure AD sign-ins | "sign in", "login", "logon", "authentication", "user login" |
| AADNonInteractiveUserSignInLogs | Non-interactive sign-ins | "service sign in", "non-interactive login" |
| AADServicePrincipalSignInLogs | Service principal sign-ins | "service principal", "app login" |
| AADManagedIdentitySignInLogs | Managed identity sign-ins | "managed identity login" |
| AuditLogs | Azure AD audit | "ad audit", "directory audit", "aad audit" |
| SecurityEvent | Windows security events | "security events", "windows security", "logon events" |
| SecurityAlert | Security alerts | "security alerts", "threats", "alerts" |
| SecurityIncident | Security incidents | "incidents", "security incidents" |
| SecurityRecommendation | Security recommendations | "recommendations", "security recommendations" |
| CommonSecurityLog | CEF logs | "cef logs", "firewall logs", "common security" |
| Syslog | Linux syslog | "syslog", "linux logs" |

### Virtual Machines & Compute
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| Heartbeat | Agent heartbeat | "heartbeat", "agent status", "vm health", "computer status" |
| Perf | Performance counters | "performance", "cpu", "memory", "disk", "perf counters" |
| Event | Windows events | "windows events", "event log", "system events" |
| VMConnection | VM connections | "connections", "network connections" |
| InsightsMetrics | VM Insights metrics | "vm metrics", "insights" |
| VMBoundPort | Bound ports | "ports", "listening ports" |
| VMComputer | Computer inventory | "computers", "vms", "machines" |
| VMProcess | Running processes | "processes", "running processes" |

### Containers & Kubernetes
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| ContainerLog | Container stdout/stderr | "container logs", "docker logs", "pod logs" |
| ContainerLogV2 | Container logs v2 | "container logs" |
| ContainerInventory | Container inventory | "containers", "container list" |
| ContainerImageInventory | Container images | "images", "container images" |
| ContainerNodeInventory | Node inventory | "nodes", "kubernetes nodes" |
| KubeEvents | Kubernetes events | "kube events", "k8s events", "kubernetes events" |
| KubePodInventory | Pod inventory | "pods", "kubernetes pods" |
| KubeNodeInventory | Node details | "kube nodes" |
| KubeServices | Services | "services", "kubernetes services" |
| KubeMonAgentEvents | Monitoring agent | "monitoring agent" |
| AKSAudit | AKS audit logs | "aks audit", "kubernetes audit" |
| AKSAuditAdmin | AKS admin audit | "aks admin" |
| AKSControlPlane | Control plane logs | "control plane", "aks control" |

### Networking
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| AzureNetworkAnalytics_CL | Network analytics | "network analytics" |
| NetworkMonitoring | Network monitoring | "network monitoring" |
| AzureFirewallApplicationRule | Firewall app rules | "firewall rules", "application rules" |
| AzureFirewallNetworkRule | Firewall network rules | "network rules" |
| AzureFirewallDnsProxy | DNS proxy | "dns proxy" |

### Databases
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| AzureDiagnostics (SQL) | SQL diagnostics | "sql logs", "database logs" |
| SQLSecurityAuditEvents | SQL audit | "sql audit", "database audit" |
| AzureDiagnostics (Cosmos) | Cosmos DB logs | "cosmos logs", "cosmosdb" |

### Storage
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| StorageBlobLogs | Blob storage logs | "blob logs", "storage logs" |
| StorageFileLogs | File storage logs | "file storage logs" |
| StorageQueueLogs | Queue storage logs | "queue logs" |
| StorageTableLogs | Table storage logs | "table storage logs" |

### Other Services
| Table | Description | Common Natural Language |
|-------|-------------|------------------------|
| ADFActivityRun | Data Factory activities | "data factory", "adf logs", "pipeline runs" |
| ADFPipelineRun | Pipeline runs | "pipeline logs" |
| ADFTriggerRun | Trigger runs | "trigger logs" |
| AutoscaleEvaluationsLog | Autoscale logs | "autoscale", "scaling" |
| AutoscaleScaleActionsLog | Scale actions | "scale actions" |
| Operation | Management operations | "operations" |
| Usage | Workspace usage | "usage", "data usage" |
| Update | Update management | "updates", "patches" |
| UpdateSummary | Update summary | "update summary" |

## NATURAL LANGUAGE MAPPING EXAMPLES:

User says → Use table
- "show me errors" → AppExceptions or AzureDiagnostics with Level=='Error'
- "web app traffic" → AppServiceHTTPLogs
- "who logged in" → SigninLogs
- "cpu usage" → Perf with ObjectName=='Processor'
- "memory usage" → Perf with ObjectName=='Memory'
- "disk space" → Perf with ObjectName=='LogicalDisk'
- "failed deployments" → AzureActivity with ActivityStatusValue=='Failed'
- "kubernetes pod issues" → KubeEvents or ContainerLog
- "api response times" → AppRequests with DurationMs
- "slow queries" → AzureDiagnostics with duration_s or query_time_s
- "security issues" → SecurityAlert or SecurityEvent
- "what changed" → AzureActivity
- "resource created/deleted" → AzureActivity with OperationNameValue contains 'write' or 'delete'

## KQL SYNTAX RULES:
1. Start with table name
2. Use | to chain operators
3. where: filter rows (where Level == 'Error')
4. project: select columns
5. summarize: aggregate (count(), avg(), sum())
6. order by: sort results
7. take/limit: restrict rows
8. ago(): time relative to now - ago(1h), ago(24h), ago(7d)
9. between(): time range
10. contains, startswith, endswith: string matching
11. ==, !=, >, <: comparisons

## OUTPUT RULES:
- Return ONLY the KQL query
- NO explanations, NO markdown code blocks, NO comments
- ALWAYS include: time filter (default ago(24h)) and take/limit (default 100)
- If ambiguous, pick the most likely table and make reasonable assumptions
- NEVER return an error - always try to produce a valid query
"""

    # Comprehensive mapping of natural language to KQL queries
    COMMON_QUERIES = {
        # Errors and Exceptions
        "errors": "AzureDiagnostics | where Level == 'Error' or Category contains 'Error' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "error": "AzureDiagnostics | where Level == 'Error' or Category contains 'Error' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "exceptions": "AppExceptions | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "exception": "AppExceptions | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "failures": "AppRequests | where Success == false | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "failed": "AppRequests | where Success == false | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "crashes": "AppExceptions | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # App Service
        "app service": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "app service logs": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "appservice": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "web app": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "web app logs": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "webapp": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "website": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "http logs": "AppServiceHTTPLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "console logs": "AppServiceConsoleLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Functions
        "function": "FunctionAppLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "functions": "FunctionAppLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "function logs": "FunctionAppLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "azure functions": "FunctionAppLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "serverless": "FunctionAppLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Activity and Audit
        "activity": "AzureActivity | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "activity logs": "AzureActivity | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "audit": "AzureActivity | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "audit logs": "AuditLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "who did": "AzureActivity | where TimeGenerated > ago(24h) | project TimeGenerated, Caller, OperationNameValue, ResourceGroup, _ResourceId | order by TimeGenerated desc | take 100",
        "changes": "AzureActivity | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "deployments": "AzureActivity | where OperationNameValue contains 'deploy' or OperationNameValue contains 'write' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Sign-ins and Authentication
        "sign in": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "signin": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "sign-in": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "login": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "logins": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "logon": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "authentication": "SigninLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "who logged in": "SigninLogs | where TimeGenerated > ago(24h) | project TimeGenerated, UserPrincipalName, AppDisplayName, IPAddress, Location, Status | order by TimeGenerated desc | take 100",
        "failed logins": "SigninLogs | where ResultType != '0' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Performance
        "performance": "Perf | where TimeGenerated > ago(1h) | order by TimeGenerated desc | take 100",
        "perf": "Perf | where TimeGenerated > ago(1h) | order by TimeGenerated desc | take 100",
        "cpu": "Perf | where ObjectName == 'Processor' and CounterName == '% Processor Time' | where TimeGenerated > ago(1h) | summarize AvgCPU=avg(CounterValue) by Computer, bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        "cpu usage": "Perf | where ObjectName == 'Processor' and CounterName == '% Processor Time' | where TimeGenerated > ago(1h) | summarize AvgCPU=avg(CounterValue) by Computer, bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        "memory": "Perf | where ObjectName == 'Memory' and CounterName == '% Committed Bytes In Use' | where TimeGenerated > ago(1h) | summarize AvgMemory=avg(CounterValue) by Computer, bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        "memory usage": "Perf | where ObjectName == 'Memory' and CounterName == '% Committed Bytes In Use' | where TimeGenerated > ago(1h) | summarize AvgMemory=avg(CounterValue) by Computer, bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        "disk": "Perf | where ObjectName == 'LogicalDisk' and CounterName == '% Free Space' | where TimeGenerated > ago(1h) | summarize AvgFreeSpace=avg(CounterValue) by Computer, InstanceName, bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        "disk usage": "Perf | where ObjectName == 'LogicalDisk' and CounterName == '% Free Space' | where TimeGenerated > ago(1h) | summarize AvgFreeSpace=avg(CounterValue) by Computer, InstanceName, bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        
        # VMs and Heartbeat
        "heartbeat": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer, OSType, Version | order by LastHeartbeat desc | take 100",
        "vm health": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer, OSType | order by LastHeartbeat desc | take 100",
        "virtual machines": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer, OSType, ComputerEnvironment | order by LastHeartbeat desc | take 100",
        "vms": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer, OSType | order by LastHeartbeat desc | take 100",
        "computers": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer, OSType | order by LastHeartbeat desc | take 100",
        
        # Containers and Kubernetes
        "container": "ContainerLog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "containers": "ContainerLog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "container logs": "ContainerLog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "docker": "ContainerLog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "kubernetes": "KubeEvents | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "k8s": "KubeEvents | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "aks": "KubeEvents | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "pods": "KubePodInventory | where TimeGenerated > ago(1h) | order by TimeGenerated desc | take 100",
        "kube events": "KubeEvents | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Security
        "security": "SecurityEvent | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "security events": "SecurityEvent | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "security alerts": "SecurityAlert | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "alerts": "SecurityAlert | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "threats": "SecurityAlert | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Application Insights
        "requests": "AppRequests | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "traces": "AppTraces | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "dependencies": "AppDependencies | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "page views": "AppPageViews | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "availability": "AppAvailabilityResults | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Diagnostics
        "diagnostics": "AzureDiagnostics | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "diagnostic logs": "AzureDiagnostics | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "resource logs": "AzureDiagnostics | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Syslog
        "syslog": "Syslog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "linux logs": "Syslog | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Windows Events
        "windows events": "Event | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "event log": "Event | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "events": "Event | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Data Factory
        "data factory": "ADFActivityRun | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "adf": "ADFActivityRun | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "pipeline": "ADFPipelineRun | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Storage
        "storage": "StorageBlobLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "blob": "StorageBlobLogs | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # SQL
        "sql": "AzureDiagnostics | where ResourceProvider == 'MICROSOFT.SQL' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "database": "AzureDiagnostics | where ResourceProvider == 'MICROSOFT.SQL' or ResourceProvider == 'MICROSOFT.DBFORMYSQL' or ResourceProvider == 'MICROSOFT.DBFORPOSTGRESQL' | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Metrics
        "metrics": "AzureMetrics | where TimeGenerated > ago(1h) | order by TimeGenerated desc | take 100",
        
        # Updates
        "updates": "Update | where TimeGenerated > ago(7d) | order by TimeGenerated desc | take 100",
        "patches": "Update | where TimeGenerated > ago(7d) | order by TimeGenerated desc | take 100",
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
        # Check for common query shortcuts (case insensitive)
        query_lower = natural_language_query.lower().strip()
        
        # Direct match first
        if query_lower in self.COMMON_QUERIES:
            return self.COMMON_QUERIES[query_lower]
        
        # Partial match - check if any keyword is in the query
        for keyword, kql in self.COMMON_QUERIES.items():
            if keyword in query_lower:
                return kql
        
        # If OpenAI is not configured, use pattern matching
        if not self.client:
            return self._pattern_based_translation(natural_language_query)
        
        # Use AI for translation
        return self._ai_translate(natural_language_query, available_tables)
    
    def _pattern_based_translation(self, query: str) -> str:
        """Simple pattern-based translation without AI."""
        query_lower = query.lower()
        
        # Extract time mentions
        time_filter = "| where TimeGenerated > ago(24h)"
        if "last hour" in query_lower or "1 hour" in query_lower:
            time_filter = "| where TimeGenerated > ago(1h)"
        elif "last 7 days" in query_lower or "last week" in query_lower or "7 days" in query_lower:
            time_filter = "| where TimeGenerated > ago(7d)"
        elif "last 30 days" in query_lower or "last month" in query_lower or "30 days" in query_lower:
            time_filter = "| where TimeGenerated > ago(30d)"
        elif "today" in query_lower:
            time_filter = "| where TimeGenerated > ago(24h)"
        elif "yesterday" in query_lower:
            time_filter = "| where TimeGenerated between(ago(48h)..ago(24h))"
        
        # Detect table based on keywords
        table = "AzureDiagnostics"
        
        # App Service
        if any(word in query_lower for word in ["app service", "appservice", "web app", "webapp", "website", "http log"]):
            table = "AppServiceHTTPLogs"
        # Functions
        elif any(word in query_lower for word in ["function", "azure function", "serverless"]):
            table = "FunctionAppLogs"
        # Activity
        elif any(word in query_lower for word in ["activity", "who did", "changes", "deployment", "created", "deleted", "modified"]):
            table = "AzureActivity"
        # Sign-ins
        elif any(word in query_lower for word in ["sign in", "signin", "login", "logon", "authentication", "logged in"]):
            table = "SigninLogs"
        # Application Insights
        elif any(word in query_lower for word in ["request", "api call"]):
            table = "AppRequests"
        elif any(word in query_lower for word in ["exception", "crash", "error"]):
            table = "AppExceptions"
        elif any(word in query_lower for word in ["trace"]):
            table = "AppTraces"
        elif any(word in query_lower for word in ["dependency", "external call"]):
            table = "AppDependencies"
        # Security
        elif any(word in query_lower for word in ["security", "threat", "alert"]):
            table = "SecurityEvent"
        # Containers
        elif any(word in query_lower for word in ["container", "docker", "kubernetes", "k8s", "aks", "pod"]):
            table = "ContainerLog"
        # Performance
        elif any(word in query_lower for word in ["performance", "cpu", "memory", "disk", "perf"]):
            table = "Perf"
        # VMs
        elif any(word in query_lower for word in ["heartbeat", "vm", "virtual machine", "computer"]):
            table = "Heartbeat"
        # Syslog
        elif any(word in query_lower for word in ["syslog", "linux"]):
            table = "Syslog"
        # Windows Events
        elif any(word in query_lower for word in ["windows event", "event log"]):
            table = "Event"
        
        # Build basic query
        return f"{table} {time_filter} | order by TimeGenerated desc | take 100"
    
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
                    {"role": "user", "content": f"Convert this to KQL: {query}"}
                ],
                temperature=0,
                max_tokens=500
            )
            
            kql = response.choices[0].message.content.strip()
            
            # Remove code blocks if present
            if kql.startswith("```"):
                lines = kql.split("\n")
                kql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            if kql.startswith("```kql"):
                kql = kql[6:]
            if kql.endswith("```"):
                kql = kql[:-3]
            kql = kql.strip()
            
            # Validate it looks like KQL (starts with a table name)
            if kql and not kql.startswith("ERROR"):
                return kql
            
            # Fall back to pattern matching
            return self._pattern_based_translation(query)
            
        except Exception as e:
            # Fall back to pattern matching
            print(f"⚠️ AI translation failed: {e}. Using pattern matching.")
            return self._pattern_based_translation(query)
