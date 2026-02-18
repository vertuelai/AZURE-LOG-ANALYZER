"""Natural language to KQL query translator."""

from typing import Optional
import json
import re
import os

from config import Config


class QueryTranslator:
    """Translates natural language queries to KQL."""
    
    # Path to custom instructions file
    INSTRUCTIONS_FILE = os.path.join(os.path.dirname(__file__), "instructions.json")
    
    # Compact system prompt for AI translation - focused on critical rules only
    SYSTEM_PROMPT_COMPACT = """You are an expert KQL translator for Azure Log Analytics. Convert natural language to valid KQL.

CRITICAL RULES:
1. Use explicit table names when specified by user
2. VM/computer availability → use Heartbeat table (Computer column), NOT AppAvailabilityResults
3. Web test results → use AppAvailabilityResults
4. Always include TimeGenerated filter (default: ago(24h))
5. Add take 100 for non-aggregation queries
6. Return ONLY the KQL query - no explanations or code blocks

KEY TABLES:
- Heartbeat: VM/computer health (Computer, OSType)
- Perf: Performance metrics (Computer, ObjectName, CounterName, CounterValue)
- SigninLogs: Azure AD logins (UserPrincipalName, IPAddress, ResultType 0=success)
- AzureActivity: Resource operations (Caller, OperationNameValue)
- AppServiceHTTPLogs: Web app HTTP logs (CIp, CsMethod, ScStatus, TimeTaken, CsHost)
- AppRequests: App Insights requests (Url, ResultCode, DurationMs)
- AppExceptions: App errors (ExceptionType, Message)
- SecurityEvent: Security logs (Computer, Account, EventID)

COLUMN MAPPINGS:
- IP: CIp (AppService), IPAddress (Signin), CallerIpAddress (Activity)
- User: UserPrincipalName (Signin), Caller (Activity), Account (Security)
- Status: ScStatus (AppService), ResultCode (AppRequests), ResultType (Signin)
"""

    SYSTEM_PROMPT = """You are an expert KQL (Kusto Query Language) translator for Azure Log Analytics. Your ONLY job is to convert natural language into valid KQL queries.

## CRITICAL INSTRUCTIONS:
1. When the user specifies a TABLE NAME explicitly (like "AppServiceHTTPLogs", "SigninLogs", etc.), you MUST use that exact table.
2. When the user asks about VIRTUAL MACHINE availability/health/status, use the Heartbeat table and filter by Computer name.
3. Do NOT confuse "availability" of VMs/computers with "AppAvailabilityResults" which is for Application Insights web tests.

## TABLE SELECTION GUIDE:
| User asks about... | Correct Table | Key Column |
|-------------------|---------------|------------|
| VM availability/health | Heartbeat | Computer |
| VM status/uptime | Heartbeat | Computer |
| Computer heartbeat | Heartbeat | Computer |
| Machine availability | Heartbeat | Computer |
| Server health | Heartbeat | Computer |
| Web test results | AppAvailabilityResults | Name |
| URL availability test | AppAvailabilityResults | Name |
| Ping test | AppAvailabilityResults | Name |

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

### Virtual Machines, Computers & Availability
| Table | Use Case | Key Columns |
|-------|----------|-------------|
| Heartbeat | VM/computer availability, health, uptime | Computer, OSType, Version, ComputerIP, ComputerEnvironment, RemoteIPCountry |
| Perf | CPU, memory, disk performance | Computer, ObjectName, CounterName, InstanceName, CounterValue |
| Event | Windows event logs | Computer, EventLog, EventLevelName, EventID, RenderedDescription, UserName |
| VMComputer | VM inventory | Computer, Ipv4Addresses, OperatingSystemFullName |
| VMConnection | VM network connections | Computer, SourceIp, DestinationIp, DestinationPort |
| InsightsMetrics | VM metrics/insights | Computer, Name, Val, Tags |

### Application Insights (NOT for VM availability!)
| Table | Use Case | Key Columns |
|-------|----------|-------------|
| AppAvailabilityResults | Web URL/ping test results (NOT VM health!) | Name, Location, Success, Message, Duration |
| AppRequests | HTTP requests to your app | Url, Name, ResultCode, DurationMs, Success, ClientIP |
| AppExceptions | Application exceptions/errors | ExceptionType, Message, OuterMessage, Method |
| AppTraces | Application trace logs | Message, SeverityLevel, OperationName |
| AppDependencies | External dependencies | Name, Target, DependencyType, Duration, Success |
| AppEvents | Custom events | Name, Properties, Measurements |

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

### Containers & Kubernetes  
| Table | Key Columns |
|-------|------------|
| ContainerLog | LogEntry, ContainerID, Computer, Image, Name |
| KubeEvents | Name, Namespace, Reason, Message, ObjectKind, SourceComponent |
| KubePodInventory | Name, Namespace, PodStatus, PodIp, ClusterName, ServiceName |

## COMMON QUERY PATTERNS:

### VM/Computer Availability (use Heartbeat table!)
Heartbeat | where Computer == "VMName" | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType | order by LastHeartbeat desc
Heartbeat | where Computer contains "VMName" | summarize LastHeartbeat=max(TimeGenerated) by Computer | order by LastHeartbeat desc
Heartbeat | where Computer =~ "vmname" | where TimeGenerated > ago(1h) | project TimeGenerated, Computer, OSType, ComputerIP, Version
Heartbeat | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer | extend MinutesSinceLastHeartbeat = datetime_diff('minute', now(), LastHeartbeat) | where MinutesSinceLastHeartbeat > 5

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
        "exceptions": "AppExceptions | where TimeGenerated > ago(24h) | project TimeGenerated, ExceptionType, OuterMessage, InnermostMessage, OperationName, AppRoleName | order by TimeGenerated desc | take 100",
        "exception": "AppExceptions | where TimeGenerated > ago(24h) | project TimeGenerated, ExceptionType, OuterMessage, InnermostMessage, OperationName, AppRoleName | order by TimeGenerated desc | take 100",
        "failures": "AppRequests | where Success == false | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "failed": "AppRequests | where Success == false | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "crashes": "AppExceptions | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
        # Application Insights - Requests
        "requests": "AppRequests | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Url, ResultCode, DurationMs, Success, ClientIP, AppRoleName | order by TimeGenerated desc | take 100",
        "app requests": "AppRequests | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Url, ResultCode, DurationMs, Success, ClientIP, AppRoleName | order by TimeGenerated desc | take 100",
        "api requests": "AppRequests | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Url, ResultCode, DurationMs, Success, ClientIP | order by TimeGenerated desc | take 100",
        "slow requests": "AppRequests | where TimeGenerated > ago(24h) | where DurationMs > 3000 | project TimeGenerated, Name, Url, DurationMs, ResultCode, Success | order by DurationMs desc | take 100",
        "failed requests": "AppRequests | where TimeGenerated > ago(24h) | where Success == false | project TimeGenerated, Name, Url, ResultCode, DurationMs, ClientIP | order by TimeGenerated desc | take 100",
        "request performance": "AppRequests | where TimeGenerated > ago(24h) | summarize AvgDuration=avg(DurationMs), P95=percentile(DurationMs, 95), Count=count(), FailureRate=countif(Success==false)*100.0/count() by Name | order by Count desc | take 50",
        
        # Application Insights - Dependencies
        "dependencies": "AppDependencies | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Target, DependencyType, DurationMs, Success, ResultCode | order by TimeGenerated desc | take 100",
        "app dependencies": "AppDependencies | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Target, DependencyType, DurationMs, Success, ResultCode | order by TimeGenerated desc | take 100",
        "external calls": "AppDependencies | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Target, DependencyType, DurationMs, Success | order by TimeGenerated desc | take 100",
        "sql calls": "AppDependencies | where TimeGenerated > ago(24h) | where DependencyType == 'SQL' | project TimeGenerated, Name, Target, DurationMs, Success, Data | order by DurationMs desc | take 100",
        "slow dependencies": "AppDependencies | where TimeGenerated > ago(24h) | where DurationMs > 1000 | project TimeGenerated, Name, Target, DependencyType, DurationMs, Success | order by DurationMs desc | take 100",
        "failed dependencies": "AppDependencies | where TimeGenerated > ago(24h) | where Success == false | project TimeGenerated, Name, Target, DependencyType, DurationMs, ResultCode | order by TimeGenerated desc | take 100",
        "http dependencies": "AppDependencies | where TimeGenerated > ago(24h) | where DependencyType == 'HTTP' | project TimeGenerated, Name, Target, DurationMs, Success, ResultCode | order by TimeGenerated desc | take 100",
        
        # Application Insights - Traces
        "traces": "AppTraces | where TimeGenerated > ago(24h) | project TimeGenerated, Message, SeverityLevel, OperationName, AppRoleName | order by TimeGenerated desc | take 100",
        "app traces": "AppTraces | where TimeGenerated > ago(24h) | project TimeGenerated, Message, SeverityLevel, OperationName, AppRoleName | order by TimeGenerated desc | take 100",
        "app logs": "AppTraces | where TimeGenerated > ago(24h) | project TimeGenerated, Message, SeverityLevel, OperationName, AppRoleName | order by TimeGenerated desc | take 100",
        "application logs": "AppTraces | where TimeGenerated > ago(24h) | project TimeGenerated, Message, SeverityLevel, OperationName | order by TimeGenerated desc | take 100",
        "error traces": "AppTraces | where TimeGenerated > ago(24h) | where SeverityLevel >= 3 | project TimeGenerated, Message, SeverityLevel, OperationName | order by TimeGenerated desc | take 100",
        "warning traces": "AppTraces | where TimeGenerated > ago(24h) | where SeverityLevel == 2 | project TimeGenerated, Message, OperationName | order by TimeGenerated desc | take 100",
        
        # Application Insights - Page Views & Browser
        "page views": "AppPageViews | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Url, DurationMs, ClientBrowser, ClientOS, ClientCity | order by TimeGenerated desc | take 100",
        "pageviews": "AppPageViews | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Url, DurationMs, ClientBrowser, ClientOS | order by TimeGenerated desc | take 100",
        "browser performance": "AppBrowserTimings | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Url, TotalDurationMs, NetworkDurationMs, ProcessingDurationMs | order by TimeGenerated desc | take 100",
        "browser timings": "AppBrowserTimings | where TimeGenerated > ago(24h) | summarize AvgTotal=avg(TotalDurationMs), AvgNetwork=avg(NetworkDurationMs), Count=count() by Name | order by Count desc | take 50",
        
        # Application Insights - Events & Metrics
        "custom events": "AppEvents | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Properties, AppRoleName | order by TimeGenerated desc | take 100",
        "app events": "AppEvents | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Properties, AppRoleName | order by TimeGenerated desc | take 100",
        "custom metrics": "AppMetrics | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Sum, Count, Min, Max, AppRoleName | order by TimeGenerated desc | take 100",
        "app metrics": "AppMetrics | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Sum, Count, Min, Max | order by TimeGenerated desc | take 100",
        
        # Application Insights - Availability
        "availability tests": "AppAvailabilityResults | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Location, Success, Message, DurationMs | order by TimeGenerated desc | take 100",
        "availability results": "AppAvailabilityResults | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Location, Success, Message, DurationMs | order by TimeGenerated desc | take 100",
        "web tests": "AppAvailabilityResults | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Location, Success, DurationMs | order by TimeGenerated desc | take 100",
        "ping tests": "AppAvailabilityResults | where TimeGenerated > ago(24h) | project TimeGenerated, Name, Location, Success, DurationMs | order by TimeGenerated desc | take 100",
        "failed availability": "AppAvailabilityResults | where TimeGenerated > ago(24h) | where Success == false | project TimeGenerated, Name, Location, Message, DurationMs | order by TimeGenerated desc | take 100",
        
        # Application Insights - Performance Counters
        "app performance": "AppPerformanceCounters | where TimeGenerated > ago(1h) | project TimeGenerated, Name, Value, AppRoleName | order by TimeGenerated desc | take 100",
        "performance counters": "AppPerformanceCounters | where TimeGenerated > ago(1h) | project TimeGenerated, Name, Value, AppRoleName | order by TimeGenerated desc | take 100",
        
        # Application Insights - Health & Analysis
        "app health": "AppRequests | where TimeGenerated > ago(1h) | summarize TotalRequests=count(), FailedRequests=countif(Success==false), AvgDuration=avg(DurationMs), P95Duration=percentile(DurationMs, 95) by bin(TimeGenerated, 5m) | order by TimeGenerated desc",
        "app overview": "AppRequests | where TimeGenerated > ago(24h) | summarize Requests=count(), Failures=countif(Success==false), AvgDuration=avg(DurationMs) by AppRoleName | order by Requests desc",
        "error rate": "AppRequests | where TimeGenerated > ago(24h) | summarize Total=count(), Errors=countif(Success==false) by bin(TimeGenerated, 1h) | extend ErrorRate=round(Errors*100.0/Total, 2) | order by TimeGenerated desc",
        "app insights": "AppRequests | where TimeGenerated > ago(24h) | summarize Requests=count(), Failures=countif(Success==false), AvgDuration=avg(DurationMs), P95=percentile(DurationMs, 95) by AppRoleName | order by Requests desc",
        "application insights": "AppRequests | where TimeGenerated > ago(24h) | summarize Requests=count(), Failures=countif(Success==false), AvgDuration=avg(DurationMs), P95=percentile(DurationMs, 95) by AppRoleName | order by Requests desc",
        
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
        
        # VMs and Heartbeat - IMPORTANT: This is for VM availability, NOT web tests!
        "heartbeat": "Heartbeat | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType, ComputerEnvironment | order by LastHeartbeat desc | take 100",
        "vm health": "Heartbeat | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType | order by LastHeartbeat desc | take 100",
        "virtual machines": "Heartbeat | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType, ComputerEnvironment | order by LastHeartbeat desc | take 100",
        "vms": "Heartbeat | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType | order by LastHeartbeat desc | take 100",
        "computers": "Heartbeat | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType | order by LastHeartbeat desc | take 100",
        "servers": "Heartbeat | where TimeGenerated > ago(24h) | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType | order by LastHeartbeat desc | take 100",
        "offline vms": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer | where LastHeartbeat < ago(15m) | order by LastHeartbeat asc",
        "offline machines": "Heartbeat | summarize LastHeartbeat=max(TimeGenerated) by Computer | where LastHeartbeat < ago(15m) | order by LastHeartbeat asc",
        
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
        "web test": "AppAvailabilityResults | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "web tests": "AppAvailabilityResults | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "availability test": "AppAvailabilityResults | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "url test": "AppAvailabilityResults | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        "ping test": "AppAvailabilityResults | where TimeGenerated > ago(24h) | order by TimeGenerated desc | take 100",
        
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
        self.custom_instructions = self._load_instructions()
        # Cache the instructions context to avoid rebuilding on every query
        self._cached_instructions_context = None
    
    def _load_instructions(self) -> dict:
        """Load custom instructions from instructions.json file."""
        try:
            if os.path.exists(self.INSTRUCTIONS_FILE):
                with open(self.INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
                    instructions = json.load(f)
                    print(f"✅ Loaded custom instructions from {self.INSTRUCTIONS_FILE}")
                    return instructions
        except Exception as e:
            print(f"⚠️ Could not load instructions file: {e}")
        return {}
    
    def reload_instructions(self):
        """Reload instructions from file (useful for hot-reloading)."""
        self.custom_instructions = self._load_instructions()
        # Clear cached context when instructions are reloaded
        self._cached_instructions_context = None
        return self.custom_instructions
    
    def _get_instructions_context(self) -> str:
        """Build context string from custom instructions for AI prompt.
        
        Results are cached to avoid rebuilding on every query.
        """
        # Return cached context if available
        if self._cached_instructions_context is not None:
            return self._cached_instructions_context
        
        if not self.custom_instructions:
            self._cached_instructions_context = ""
            return ""
        
        context_parts = []
        
        # Add agent role and identity
        agent_role = self.custom_instructions.get("agent_role", {})
        if agent_role:
            role_text = "## AGENT ROLE:\n"
            role_text += f"Identity: {agent_role.get('identity', 'Azure Log Analytics KQL Expert')}\n"
            responsibilities = agent_role.get("responsibilities", [])
            if responsibilities:
                role_text += "Responsibilities:\n" + "\n".join(f"- {r}" for r in responsibilities)
            context_parts.append(role_text)
        
        # Add behavior priority
        priority = self.custom_instructions.get("behavior_priority", [])
        if priority:
            context_parts.append("## BEHAVIOR PRIORITY:\n" + "\n".join(priority))
        
        # Add global rules
        global_rules = self.custom_instructions.get("global_rules", [])
        if global_rules:
            context_parts.append("## GLOBAL RULES:\n" + "\n".join(f"- {rule}" for rule in global_rules))
        
        # Add time filter rules
        time_rules = self.custom_instructions.get("time_filter_rules", {})
        if time_rules:
            time_text = "## TIME FILTER MAPPINGS:\n"
            mappings = time_rules.get("mappings", {})
            for phrase, kql_time in mappings.items():
                time_text += f"- '{phrase}' → {kql_time}\n"
            time_text += f"Default time: {time_rules.get('default', 'ago(24h)')}\n"
            context_parts.append(time_text)
        
        # Add table mappings
        table_mappings = self.custom_instructions.get("table_mappings", {}).get("mappings", [])
        if table_mappings:
            mapping_text = "## TABLE MAPPINGS (CRITICAL - Use correct table!):\n"
            for mapping in table_mappings:
                terms = ", ".join(mapping.get("terms", []))
                table = mapping.get("table", "")
                key_col = mapping.get("key_column", "")
                notes = mapping.get("notes", "")
                mapping_text += f"- When user says: [{terms}] → Use table: {table} (key column: {key_col}). {notes}\n"
            context_parts.append(mapping_text)
        
        # Add intelligent interpretation (phrase to KQL mappings)
        interpretations = self.custom_instructions.get("intelligent_interpretation", {}).get("phrase_mappings", {})
        if interpretations:
            interp_text = "## PHRASE INTERPRETATIONS:\n"
            for phrase, mapping in interpretations.items():
                if isinstance(mapping, dict):
                    table = mapping.get("table", "")
                    filter_cond = mapping.get("filter", "")
                    pattern = mapping.get("pattern", "")
                    if table and filter_cond:
                        interp_text += f"- '{phrase}' → Table: {table}, Filter: {filter_cond}\n"
                    elif filter_cond:
                        interp_text += f"- '{phrase}' → Filter: {filter_cond}\n"
                    elif pattern:
                        interp_text += f"- '{phrase}' → Pattern: {pattern}\n"
            context_parts.append(interp_text)
        
        # Add KQL patterns
        kql_patterns = self.custom_instructions.get("kql_patterns", {})
        if kql_patterns:
            pattern_text = "## KQL PATTERNS:\n"
            for pattern_name, pattern_val in kql_patterns.items():
                if not pattern_name.startswith("_"):
                    pattern_text += f"- {pattern_name}: {pattern_val}\n"
            context_parts.append(pattern_text)
        
        # Add resource aliases
        aliases = self.custom_instructions.get("resource_aliases", {}).get("aliases", {})
        if aliases:
            alias_text = "## RESOURCE ALIASES:\n"
            for friendly, actual in aliases.items():
                alias_text += f"- '{friendly}' means '{actual}'\n"
            context_parts.append(alias_text)
        
        # Add column mappings
        col_mappings = self.custom_instructions.get("column_mappings", {})
        if col_mappings:
            col_text = "## COLUMN NAME MAPPINGS:\n"
            for concept, tables in col_mappings.items():
                if concept.startswith("_"):
                    continue
                if isinstance(tables, dict):
                    col_text += f"- {concept}: "
                    col_text += ", ".join(f"{t}→{c}" for t, c in tables.items())
                    col_text += "\n"
            context_parts.append(col_text)
        
        # Add performance rules
        perf_rules = self.custom_instructions.get("performance_rules", {})
        if perf_rules:
            perf_text = "## PERFORMANCE RULES:\n"
            must_do = perf_rules.get("must_do", [])
            if must_do:
                perf_text += "MUST DO:\n" + "\n".join(f"- {r}" for r in must_do) + "\n"
            avoid = perf_rules.get("avoid", [])
            if avoid:
                perf_text += "AVOID:\n" + "\n".join(f"- {r}" for r in avoid)
            context_parts.append(perf_text)
        
        # Add security guardrails
        security = self.custom_instructions.get("security_guardrails", {})
        if security:
            sec_text = "## SECURITY GUARDRAILS:\n"
            must_not = security.get("must_not", [])
            if must_not:
                sec_text += "MUST NOT:\n" + "\n".join(f"- {r}" for r in must_not)
            context_parts.append(sec_text)
        
        # Add query templates
        templates = self.custom_instructions.get("query_templates", {}).get("templates", {})
        if templates:
            tmpl_text = "## QUERY TEMPLATES:\n"
            for name, tmpl in templates.items():
                desc = tmpl.get("description", "")
                template = tmpl.get("template", "")
                tmpl_text += f"- {name}: {desc}\n  Template: {template[:100]}...\n"
            context_parts.append(tmpl_text)
        
        # Add business context
        business = self.custom_instructions.get("business_context", {})
        if business:
            biz_text = "## BUSINESS CONTEXT:\n"
            critical = business.get("critical_resources", [])
            if critical:
                biz_text += f"- Critical resources: {', '.join(critical)}\n"
            notes = business.get("notes", [])
            for note in notes:
                biz_text += f"- {note}\n"
            context_parts.append(biz_text)
        
        # Add response format preferences
        response_fmt = self.custom_instructions.get("response_format", {})
        if response_fmt:
            fmt_text = "## OUTPUT FORMAT:\n"
            fmt_text += f"- Max results default: {response_fmt.get('max_results_default', 100)}\n"
            if response_fmt.get("include_explanation"):
                fmt_text += "- Include explanation when helpful\n"
            context_parts.append(fmt_text)
        
        # Cache the result
        self._cached_instructions_context = "\n\n".join(context_parts)
        return self._cached_instructions_context
    
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
        
        STRATEGY: AI-FIRST approach
        1. If AI is available, ALWAYS use AI translation for any meaningful query
        2. Only use pattern matching/shortcuts for trivial single-word queries OR as fallback
        
        Args:
            natural_language_query: The query in natural language
            available_tables: List of available tables in the workspace
            
        Returns:
            KQL query string
        """
        query_lower = natural_language_query.lower().strip()
        
        # If AI is available, use AI for ALL queries that aren't trivial shortcuts
        if self.client:
            # Only use shortcuts for exact single-word matches like "errors", "logins"
            # that don't have any specific filters or entity names
            words = query_lower.split()
            is_simple_shortcut = (
                len(words) <= 2 and 
                query_lower in self.COMMON_QUERIES and
                not self._has_specific_entities(query_lower)
            )
            
            if not is_simple_shortcut:
                # Use AI for everything else
                return self._ai_translate(natural_language_query, available_tables)
        
        # AI not available or simple shortcut - use pattern matching
        # Direct exact match
        if query_lower in self.COMMON_QUERIES:
            return self.COMMON_QUERIES[query_lower]
        
        # Partial match for keywords
        for keyword, kql in self.COMMON_QUERIES.items():
            if keyword in query_lower and len(keyword) > 3:  # Only match keywords > 3 chars
                return kql
        
        # Fall back to pattern-based translation
        return self._pattern_based_translation(natural_language_query)
    
    def _has_specific_entities(self, query: str) -> bool:
        """Check if query contains specific entities that need AI processing."""
        # Check for VM/computer names (anything that looks like a resource name)
        has_potential_name = bool(re.search(r'\b[A-Za-z]+[A-Za-z0-9\-_]+\b', query))
        # Check for IPs
        has_ip = bool(re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', query))
        # Check for emails
        has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', query))
        # Check for filter keywords
        has_filter = any(word in query for word in [
            'filter', 'where', 'only', 'specific', 'named', 'called',
            'from', 'by', 'for', 'of', 'with'
        ])
        # Check for resource identifiers (VM names, etc.)
        has_resource = bool(re.search(r'[Vv][Mm]|[Ss]erver|[Cc]omputer|[Mm]achine', query))
        
        return has_potential_name or has_ip or has_email or has_filter or has_resource
    
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
        
        # Extract potential resource/VM name (capitalized word or word with numbers)
        resource_name_match = re.search(r'\b([A-Z][A-Za-z0-9\-_]+)\b', query)
        resource_name = resource_name_match.group(1) if resource_name_match else None
        
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
        
        # Detect table based on keywords - PRIORITY ORDER MATTERS
        table = "AzureDiagnostics"
        computer_filter = ""
        
        # First check explicit table names
        explicit_tables = [
            "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs",
            "AppServiceAuditLogs", "FunctionAppLogs", "AzureActivity", "SigninLogs",
            "AppRequests", "AppExceptions", "AppTraces", "AppDependencies",
            "SecurityEvent", "SecurityAlert", "ContainerLog", "KubeEvents",
            "Perf", "Heartbeat", "Syslog", "Event", "AzureDiagnostics", "AzureMetrics",
            "AppAvailabilityResults", "VMComputer", "VMConnection", "InsightsMetrics"
        ]
        
        for tbl in explicit_tables:
            if tbl.lower() in query_lower:
                table = tbl
                break
        else:
            # PRIORITY: VM/Computer availability - use Heartbeat (NOT AppAvailabilityResults!)
            if any(word in query_lower for word in ["vm ", "virtual machine", "virtualmachine", "computer", "server", "machine"]):
                if any(word in query_lower for word in ["availability", "health", "status", "uptime", "heartbeat", "alive", "running"]):
                    table = "Heartbeat"
                    if resource_name:
                        computer_filter = f"| where Computer contains '{resource_name}'"
                elif "perf" in query_lower or "performance" in query_lower or "cpu" in query_lower or "memory" in query_lower:
                    table = "Perf"
                    if resource_name:
                        computer_filter = f"| where Computer contains '{resource_name}'"
                else:
                    table = "Heartbeat"
                    if resource_name:
                        computer_filter = f"| where Computer contains '{resource_name}'"
            # App Service
            elif any(word in query_lower for word in ["app service", "appservice", "web app", "webapp", "website", "http log"]):
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
            # Web availability tests (NOT VM!)
            elif "availability" in query_lower and any(word in query_lower for word in ["test", "web", "url", "ping", "site"]):
                table = "AppAvailabilityResults"
            # Application Insights
            elif any(word in query_lower for word in ["request", "api call"]):
                table = "AppRequests"
            elif any(word in query_lower for word in ["exception", "crash"]):
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
            # Performance (general)
            elif any(word in query_lower for word in ["performance", "cpu", "memory", "disk", "perf"]):
                table = "Perf"
            # Heartbeat (general)
            elif any(word in query_lower for word in ["heartbeat"]):
                table = "Heartbeat"
            # Syslog
            elif any(word in query_lower for word in ["syslog", "linux"]):
                table = "Syslog"
            # Windows Events
            elif any(word in query_lower for word in ["windows event", "event log"]):
                table = "Event"
        
        # Build query with all filters
        filters = computer_filter + time_filter + ip_filter + status_filter + method_filter
        
        # For Heartbeat with VM name, return a more useful query
        if table == "Heartbeat" and computer_filter:
            return f"Heartbeat {filters} | summarize LastHeartbeat=max(TimeGenerated), HeartbeatCount=count() by Computer, OSType, ComputerEnvironment | order by LastHeartbeat desc | take 100"
        
        return f"{table} {filters} | order by TimeGenerated desc | take 100"
    
    def _ai_translate(self, query: str, available_tables: Optional[list] = None) -> str:
        """Use AI to translate the query."""
        # Build compact context - only include essential information
        context_parts = []
        
        if available_tables:
            # Only include first 30 tables to avoid bloating the prompt
            tables_to_show = available_tables[:30]
            context_parts.append(f"Available tables: {', '.join(tables_to_show)}")
        
        # Add only essential custom instructions (resource aliases)
        aliases = self.custom_instructions.get("resource_aliases", {}).get("aliases", {})
        if aliases:
            alias_str = ", ".join(f"'{k}'='{v}'" for k, v in aliases.items())
            context_parts.append(f"Resource aliases: {alias_str}")
        
        context = "\n".join(context_parts) if context_parts else ""
        
        # Build a more specific prompt with extracted patterns
        user_prompt = f"Convert this natural language query to KQL: {query}"
        
        hints = []
        
        # CRITICAL: Detect VM/computer availability queries
        query_lower = query.lower()
        if any(word in query_lower for word in ['vm', 'virtual machine', 'virtualmachine', 'computer', 'server', 'machine']):
            if any(word in query_lower for word in ['availability', 'health', 'status', 'uptime', 'alive', 'running', 'online', 'offline']):
                hints.append("IMPORTANT: User is asking about VM/computer availability - use Heartbeat table with Computer column, NOT AppAvailabilityResults!")
                # Try to extract the VM/computer name
                name_match = re.search(r'\b([A-Z][A-Za-z0-9\-_]+)\b', query)
                if name_match:
                    potential_name = name_match.group(1)
                    # Skip common words
                    if potential_name.lower() not in ['vm', 'server', 'machine', 'computer', 'find', 'get', 'show', 'check']:
                        hints.append(f"VM/Computer name to filter: {potential_name}")
        
        # Check for resource aliases from custom instructions
        aliases = self.custom_instructions.get("resource_aliases", {}).get("aliases", {})
        for friendly, actual in aliases.items():
            if friendly.lower() in query_lower:
                hints.append(f"Resource alias detected: '{friendly}' should be translated to '{actual}'")
        
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
        
        # Build system message with compact prompt and context
        system_message = self.SYSTEM_PROMPT_COMPACT
        if context:
            system_message += f"\n\n{context}"
        
        try:
            response = self.client.chat.completions.create(
                model=Config.AZURE_OPENAI_DEPLOYMENT or "gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
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
