"""Natural language to KQL query translator."""

from typing import Optional
import json
import re

from config import Config


class QueryTranslator:
    """Translates natural language queries to KQL."""
    
    SYSTEM_PROMPT = """You are an expert KQL (Kusto Query Language) translator for Azure Log Analytics. Your ONLY job is to convert natural language into valid KQL queries.

## CRITICAL INSTRUCTION:
When the user specifies a TABLE NAME explicitly (like "AppServiceHTTPLogs", "SigninLogs", etc.), you MUST use that exact table. Do not substitute with a different table.

## KQL OPERATORS REFERENCE:

### Tabular Operators (use with |)
| Operator | Description | Example |
|----------|-------------|---------|
| where | Filter rows based on condition | where Status == 200 |
| project | Select/rename columns | project TimeGenerated, User, Action |
| project-away | Remove columns | project-away TenantId, _ResourceId |
| extend | Add calculated columns | extend Duration_sec = Duration/1000 |
| summarize | Aggregate data | summarize count() by User |
| order by / sort by | Sort results | order by TimeGenerated desc |
| top | Get top N rows | top 10 by Duration desc |
| take / limit | Limit rows returned | take 100 |
| join | Join tables | join kind=inner (Table2) on Key |
| union | Combine tables | union Table1, Table2 |
| distinct | Unique values | distinct UserName |
| count | Count rows | count |
| parse | Extract data from strings | parse Message with * "IP:" IP " " * |
| mv-expand | Expand arrays | mv-expand PropertyBag |
| make-series | Create time series | make-series count() on TimeGenerated step 1h |
| render | Visualize (chart) | render timechart |

### Comparison Operators (use in where)
| Operator | Description | Example |
|----------|-------------|---------|
| == | Equals (case-sensitive) | where Name == "John" |
| != | Not equals | where Status != 200 |
| =~ | Equals (case-insensitive) | where Name =~ "john" |
| !~ | Not equals (case-insensitive) | where Name !~ "john" |
| > | Greater than | where Value > 100 |
| >= | Greater or equal | where Value >= 100 |
| < | Less than | where Value < 100 |
| <= | Less or equal | where Value <= 100 |
| in | In list | where Status in (200, 201, 204) |
| !in | Not in list | where Status !in (400, 500) |
| between | In range | where Value between (10 .. 100) |
| contains | Contains substring (case-insensitive) | where Message contains "error" |
| !contains | Not contains | where Message !contains "debug" |
| contains_cs | Contains (case-sensitive) | where Message contains_cs "Error" |
| has | Contains word (faster) | where Message has "error" |
| !has | Not has word | where Message !has "debug" |
| has_cs | Has word (case-sensitive) | where Message has_cs "Error" |
| hasprefix | Starts with word | where Name hasprefix "test" |
| hassuffix | Ends with word | where Name hassuffix "prod" |
| startswith | Starts with string | where Url startswith "/api" |
| !startswith | Not starts with | where Url !startswith "/health" |
| endswith | Ends with string | where File endswith ".log" |
| !endswith | Not ends with | where File !endswith ".tmp" |
| matches regex | Regex match | where Message matches regex "error.*failed" |

### Logical Operators
| Operator | Example |
|----------|---------|
| and | where Status >= 400 and Status < 500 |
| or | where Level == "Error" or Level == "Warning" |
| not | where not(Success) |

### Aggregation Functions (use with summarize)
| Function | Description | Example |
|----------|-------------|---------|
| count() | Count rows | summarize count() by User |
| dcount() | Distinct count | summarize dcount(User) |
| sum() | Sum values | summarize sum(BytesSent) |
| avg() | Average | summarize avg(Duration) |
| min() | Minimum | summarize min(TimeGenerated) |
| max() | Maximum | summarize max(Duration) |
| percentile() | Percentile | summarize percentile(Duration, 95) |
| stdev() | Standard deviation | summarize stdev(Value) |
| variance() | Variance | summarize variance(Value) |
| make_list() | Collect to array | summarize make_list(Event) |
| make_set() | Unique values array | summarize make_set(User) |
| countif() | Conditional count | summarize countif(Status >= 400) |
| sumif() | Conditional sum | summarize sumif(Bytes, Success) |
| arg_max() | Row with max value | summarize arg_max(TimeGenerated, *) |
| arg_min() | Row with min value | summarize arg_min(TimeGenerated, *) |

### Date/Time Functions
| Function | Description | Example |
|----------|-------------|---------|
| ago() | Time offset from now | where TimeGenerated > ago(24h) |
| now() | Current time | where TimeGenerated < now() |
| datetime() | Specific datetime | where TimeGenerated > datetime(2024-01-01) |
| startofday() | Start of day | startofday(TimeGenerated) |
| endofday() | End of day | endofday(TimeGenerated) |
| startofweek() | Start of week | startofweek(TimeGenerated) |
| startofmonth() | Start of month | startofmonth(TimeGenerated) |
| bin() | Round to interval | bin(TimeGenerated, 1h) |
| format_datetime() | Format date | format_datetime(TimeGenerated, "yyyy-MM-dd") |
| datetime_diff() | Difference | datetime_diff('hour', end, start) |
| between | Time range | where TimeGenerated between (ago(7d) .. ago(1d)) |

### String Functions
| Function | Description | Example |
|----------|-------------|---------|
| tolower() | Lowercase | tolower(UserName) |
| toupper() | Uppercase | toupper(Status) |
| strlen() | String length | strlen(Message) |
| substring() | Extract substring | substring(Message, 0, 100) |
| split() | Split string | split(Url, "/") |
| strcat() | Concatenate | strcat(FirstName, " ", LastName) |
| replace_string() | Replace | replace_string(Url, "http://", "https://") |
| trim() | Trim whitespace | trim(" ", Message) |
| extract() | Regex extract | extract("IP: ([0-9.]+)", 1, Message) |
| parse_json() | Parse JSON | parse_json(CustomDimensions) |
| parse_url() | Parse URL | parse_url(RequestUri) |

### IP Functions
| Function | Description | Example |
|----------|-------------|---------|
| ipv4_compare() | Compare IPs | ipv4_compare(IP1, IP2) |
| ipv4_is_in_range() | IP in CIDR range | ipv4_is_in_range(ClientIP, "10.0.0.0/8") |
| ipv4_is_private() | Is private IP | ipv4_is_private(ClientIP) |
| parse_ipv4() | Parse IP to number | parse_ipv4(ClientIP) |
| geo_info_from_ip_address() | IP geolocation | geo_info_from_ip_address(ClientIP) |

### Conditional Functions
| Function | Description | Example |
|----------|-------------|---------|
| iff() | If-then-else | iff(Status >= 400, "Error", "OK") |
| case() | Multiple conditions | case(Status < 300, "OK", Status < 400, "Redirect", "Error") |
| coalesce() | First non-null | coalesce(UserName, "Unknown") |
| isnull() | Check null | where isnull(ErrorMessage) |
| isnotnull() | Check not null | where isnotnull(UserAgent) |
| isempty() | Check empty string | where isempty(Details) |
| isnotempty() | Check not empty | where isnotempty(Message) |

## COMPREHENSIVE AZURE LOG ANALYTICS TABLES REFERENCE:

### App Service & Web Apps
| Table | Key Columns |
|-------|------------|
| AppServiceHTTPLogs | CIp (client IP), CsMethod (HTTP method), CsUriStem (URL path), ScStatus (status code), TimeTaken, UserAgent, CsHost, Result |
| AppServiceConsoleLogs | ResultDescription, Host, Level |
| AppServiceAppLogs | CustomLevel, Message, Host, StackTrace |

### Application Insights
| Table | Key Columns |
|-------|------------|
| AppRequests | Url, Name, ResultCode, DurationMs, Success, ClientIP, ClientCity, ClientCountryOrRegion |
| AppExceptions | ExceptionType, Message, OuterMessage, InnermostMessage, Method, Assembly |
| AppTraces | Message, SeverityLevel, OperationName |
| AppDependencies | Name, Target, DependencyType, Data, Duration, Success, ResultCode |
| AppEvents | Name, Properties, Measurements |

### Security & Identity
| Table | Key Columns |
|-------|------------|
| SigninLogs | UserPrincipalName, UserDisplayName, IPAddress, Location, AppDisplayName, ClientAppUsed, ResultType (0=success), Status, DeviceDetail |
| AuditLogs | OperationName, Result, TargetResources, InitiatedBy, Category |
| SecurityEvent | Computer, Account, EventID, Activity, IpAddress, Process |
| SecurityAlert | AlertName, AlertSeverity, Description, Tactics, Entities |

### Azure Activity
| Table | Key Columns |
|-------|------------|
| AzureActivity | Caller, CallerIpAddress, OperationNameValue, ResourceGroup, ResourceProviderValue, ActivityStatusValue, Level |

### Virtual Machines & Performance
| Table | Key Columns |
|-------|------------|
| Heartbeat | Computer, OSType, Version, ComputerIP, RemoteIPCountry |
| Perf | Computer, ObjectName, CounterName, InstanceName, CounterValue |
| Event | Computer, EventLog, EventLevelName, EventID, RenderedDescription, UserName |

### Containers & Kubernetes  
| Table | Key Columns |
|-------|------------|
| ContainerLog | LogEntry, ContainerID, Computer, Image, Name |
| KubeEvents | Name, Namespace, Reason, Message, ObjectKind, SourceComponent |
| KubePodInventory | Name, Namespace, PodStatus, PodIp, ClusterName, ServiceName |

## COMMON QUERY PATTERNS:

### Filter by specific field value
TableName | where FieldName == "value"

### Filter by IP address  
AppServiceHTTPLogs | where CIp == "10.0.0.1"
SigninLogs | where IPAddress == "10.0.0.1"
AzureActivity | where CallerIpAddress == "10.0.0.1"

### Filter by status code
AppServiceHTTPLogs | where ScStatus == 500
AppServiceHTTPLogs | where ScStatus >= 400 and ScStatus < 500
AppRequests | where ResultCode == "500"

### Filter by user
SigninLogs | where UserPrincipalName == "user@domain.com"
SigninLogs | where UserPrincipalName contains "john"
AzureActivity | where Caller contains "user@domain.com"

### Filter by time
| where TimeGenerated > ago(1h)
| where TimeGenerated > ago(24h)
| where TimeGenerated > ago(7d)
| where TimeGenerated between (datetime(2024-01-01) .. datetime(2024-01-31))

### Filter by URL/path
AppServiceHTTPLogs | where CsUriStem contains "/api"
AppServiceHTTPLogs | where CsUriStem startswith "/api/v2"
AppRequests | where Url contains "login"

### Filter by HTTP method
AppServiceHTTPLogs | where CsMethod == "POST"
AppServiceHTTPLogs | where CsMethod in ("POST", "PUT", "DELETE")

### Filter by multiple conditions
AppServiceHTTPLogs | where CIp == "10.0.0.1" and ScStatus >= 400
SigninLogs | where UserPrincipalName contains "admin" and ResultType != "0"

### Aggregation examples
SigninLogs | summarize count() by UserPrincipalName
AppServiceHTTPLogs | summarize count() by CIp, ScStatus
AppRequests | summarize avg(DurationMs), percentile(DurationMs, 95) by Name

### Top N queries
AppServiceHTTPLogs | summarize count() by CIp | top 10 by count_
SigninLogs | summarize FailedLogins=countif(ResultType != "0") by UserPrincipalName | top 10 by FailedLogins

## OUTPUT RULES:
- Return ONLY the KQL query - no explanations, no markdown, no code blocks
- ALWAYS include time filter (default: ago(24h)) unless user specifies otherwise
- ALWAYS include take/limit (default: 100) unless user asks for aggregation
- When user mentions a specific table name, USE THAT TABLE
- Use the correct column names for each table
- For IP filtering, use the right column: CIp (AppServiceHTTPLogs), IPAddress (SigninLogs), CallerIpAddress (AzureActivity), etc.
- NEVER return an error - always produce a valid query
- If ambiguous, make reasonable assumptions and use the most likely interpretation
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
        
        # Check if query has filter conditions (contains filter keywords or IP addresses)
        has_ip_address = bool(re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', query_lower))
        has_filter_keywords = any(word in query_lower for word in [
            'filter', 'where', 'from ip', 'from user', 'only', 'specific', 
            'between', 'greater than', 'less than', 'contains', 'equals',
            'status', 'code', 'response', 'error code', 'ip address', 'client ip',
            'source', 'destination', 'user agent', 'method',
            'exclude', 'include', 'matching', 'like', 'starting with', 'ending with',
            'top', 'last', 'first', 'count', 'sum', 'average', 'group by',
            'user', 'email', 'path', 'url', 'uri', 'endpoint'
        ])
        # Also check for HTTP methods as standalone words
        has_http_method = any(f' {method} ' in f' {query_lower} ' for method in ['get', 'post', 'put', 'delete', 'patch'])
        has_filter_conditions = has_ip_address or has_filter_keywords or has_http_method
        
        # Direct match first - only use if query is simple (no filter conditions)
        if query_lower in self.COMMON_QUERIES and not has_filter_conditions:
            return self.COMMON_QUERIES[query_lower]
        
        # If query has filter conditions, always prefer AI translation
        if has_filter_conditions and self.client:
            return self._ai_translate(natural_language_query, available_tables)
        
        # Partial match - only for simple queries without filter conditions
        if not has_filter_conditions:
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
        
        # Extract IP address if mentioned
        ip_filter = ""
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', query)
        if ip_match:
            ip_address = ip_match.group(1)
            # Determine which IP column to use based on context
            if any(word in query_lower for word in ["client", "source", "from"]):
                ip_filter = f"| where CIp == '{ip_address}' or ClientIP == '{ip_address}' or CallerIpAddress == '{ip_address}' or IPAddress == '{ip_address}'"
            else:
                ip_filter = f"| where CIp == '{ip_address}' or ClientIP == '{ip_address}' or CallerIpAddress == '{ip_address}' or IPAddress == '{ip_address}' or SIp == '{ip_address}'"
        
        # Extract status code if mentioned
        status_filter = ""
        status_match = re.search(r'status\s*(?:code)?\s*(\d{3})', query_lower)
        if status_match:
            status_code = status_match.group(1)
            status_filter = f"| where ScStatus == {status_code} or HttpStatusCode == {status_code} or ResultCode == '{status_code}'"
        elif "error" in query_lower or "failed" in query_lower or "failure" in query_lower:
            status_filter = "| where ScStatus >= 400 or HttpStatusCode >= 400 or Success == false"
        elif "success" in query_lower:
            status_filter = "| where ScStatus < 400 or HttpStatusCode < 400 or Success == true"
        
        # Extract HTTP method if mentioned
        method_filter = ""
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            if method.lower() in query_lower:
                method_filter = f"| where CsMethod == '{method}' or RequestMethod == '{method}'"
                break
        
        # Detect table based on keywords - check explicit table names first
        table = "AzureDiagnostics"
        explicit_tables = [
            "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs",
            "AppServiceAuditLogs", "FunctionAppLogs", "AzureActivity", "SigninLogs",
            "AppRequests", "AppExceptions", "AppTraces", "AppDependencies",
            "SecurityEvent", "SecurityAlert", "ContainerLog", "KubeEvents",
            "Perf", "Heartbeat", "Syslog", "Event", "AzureDiagnostics", "AzureMetrics"
        ]
        
        for tbl in explicit_tables:
            if tbl.lower() in query_lower:
                table = tbl
                break
        else:
            # Detect table based on keywords
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
        
        # Build query with all filters
        filters = time_filter + ip_filter + status_filter + method_filter
        return f"{table} {filters} | order by TimeGenerated desc | take 100"
    
    def _ai_translate(self, query: str, available_tables: Optional[list] = None) -> str:
        """Use AI to translate the query."""
        context = ""
        if available_tables:
            context = f"\n\nAvailable tables in this workspace: {', '.join(available_tables)}"
        
        # Build a more specific prompt with extracted patterns
        user_prompt = f"Convert this natural language query to KQL: {query}"
        
        hints = []
        
        # Extract IP addresses
        ip_matches = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', query)
        if ip_matches:
            hints.append(f"IP address(es) found: {', '.join(ip_matches)}")
        
        # Extract email addresses
        email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', query)
        if email_matches:
            hints.append(f"Email/user(s) found: {', '.join(email_matches)}")
        
        # Extract status codes
        status_matches = re.findall(r'\b[1-5]\d{2}\b', query)
        if status_matches:
            hints.append(f"HTTP status code(s) found: {', '.join(status_matches)}")
        
        # Extract time references
        time_patterns = re.findall(r'\b(?:last\s+)?(\d+)\s*(hour|hours|day|days|week|weeks|minute|minutes|min|mins|h|d|w|m)\b', query.lower())
        if time_patterns:
            hints.append(f"Time reference found: {time_patterns}")
        
        # Extract URLs or paths
        path_matches = re.findall(r'/[\w/\-\.]+', query)
        if path_matches:
            hints.append(f"URL path(s) found: {', '.join(path_matches)}")
        
        # Extract quoted strings (potential exact match values)
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', query)
        if quoted_matches:
            hints.append(f"Quoted values found: {', '.join(quoted_matches)}")
        
        # Extract comparison operators mentioned
        if any(word in query.lower() for word in ['greater than', 'more than', 'above', 'over', '>']):
            hints.append("User wants greater than comparison")
        if any(word in query.lower() for word in ['less than', 'fewer than', 'below', 'under', '<']):
            hints.append("User wants less than comparison")
        if any(word in query.lower() for word in ['between', 'range']):
            hints.append("User wants range/between comparison")
        if any(word in query.lower() for word in ['contains', 'includes', 'has', 'with']):
            hints.append("User wants contains/partial match")
        if any(word in query.lower() for word in ['starts with', 'begins with', 'prefix']):
            hints.append("User wants startswith comparison")
        if any(word in query.lower() for word in ['ends with', 'suffix']):
            hints.append("User wants endswith comparison")
        if any(word in query.lower() for word in ['not', 'exclude', 'except', 'without']):
            hints.append("User wants to exclude/negate")
        
        # Add aggregation hints
        if any(word in query.lower() for word in ['count', 'how many', 'total', 'number of']):
            hints.append("User wants count aggregation")
        if any(word in query.lower() for word in ['average', 'avg', 'mean']):
            hints.append("User wants average aggregation")
        if any(word in query.lower() for word in ['sum', 'total']):
            hints.append("User wants sum aggregation")
        if any(word in query.lower() for word in ['top', 'most', 'highest', 'max']):
            hints.append("User wants top/max results")
        if any(word in query.lower() for word in ['bottom', 'least', 'lowest', 'min']):
            hints.append("User wants bottom/min results")
        if any(word in query.lower() for word in ['group by', 'per', 'by each', 'for each']):
            hints.append("User wants grouping")
        
        if hints:
            user_prompt += "\n\nDetected patterns:\n- " + "\n- ".join(hints)
        
        try:
            response = self.client.chat.completions.create(
                model=Config.AZURE_OPENAI_DEPLOYMENT or "gpt-4",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT + context},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            kql = response.choices[0].message.content.strip()
            
            # Remove code blocks if present (handle various formats)
            if kql.startswith("```"):
                lines = kql.split("\n")
                # Remove first line (```kql or ```)
                lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                kql = "\n".join(lines)
            
            # Clean up any remaining backticks
            kql = kql.replace("```kql", "").replace("```", "").strip()
            
            # Validate it looks like KQL (starts with a table name or let statement)
            if kql and not kql.upper().startswith("ERROR") and not kql.upper().startswith("I CAN") and not kql.upper().startswith("I'M"):
                # Check basic KQL structure
                first_word = kql.split()[0] if kql.split() else ""
                if "|" in kql or first_word.replace("_", "").isalnum():
                    return kql
            
            # Fall back to pattern matching
            return self._pattern_based_translation(query)
            
        except Exception as e:
            # Fall back to pattern matching
            print(f"⚠️ AI translation failed: {e}. Using pattern matching.")
            return self._pattern_based_translation(query)
