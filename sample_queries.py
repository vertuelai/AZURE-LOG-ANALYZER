"""
Sample queries for Azure Log Analytics Analyzer.

This file contains example KQL queries for common scenarios.
"""

SAMPLE_QUERIES = {
    # Activity Logs
    "recent_activity": """
        AzureActivity
        | where TimeGenerated > ago(24h)
        | project TimeGenerated, OperationName, ActivityStatus, Caller, ResourceGroup
        | order by TimeGenerated desc
        | take 100
    """,
    
    "failed_operations": """
        AzureActivity
        | where TimeGenerated > ago(24h)
        | where ActivityStatus == "Failed"
        | summarize FailureCount = count() by OperationName, ResourceGroup
        | order by FailureCount desc
    """,
    
    "resource_changes": """
        AzureActivity
        | where TimeGenerated > ago(7d)
        | where OperationName contains "Write" or OperationName contains "Delete"
        | project TimeGenerated, OperationName, Caller, ResourceGroup, Resource
        | order by TimeGenerated desc
    """,
    
    # Diagnostics
    "error_summary": """
        AzureDiagnostics
        | where TimeGenerated > ago(24h)
        | where Level == "Error"
        | summarize ErrorCount = count() by ResourceType, Resource
        | order by ErrorCount desc
    """,
    
    "top_error_messages": """
        AzureDiagnostics
        | where TimeGenerated > ago(24h)
        | where Level == "Error"
        | summarize Count = count() by Message
        | order by Count desc
        | take 10
    """,
    
    # Performance
    "cpu_usage": """
        Perf
        | where TimeGenerated > ago(1h)
        | where ObjectName == "Processor" and CounterName == "% Processor Time"
        | summarize AvgCPU = avg(CounterValue) by Computer, bin(TimeGenerated, 5m)
        | order by TimeGenerated desc
    """,
    
    "memory_usage": """
        Perf
        | where TimeGenerated > ago(1h)
        | where ObjectName == "Memory" and CounterName == "% Used Memory"
        | summarize AvgMemory = avg(CounterValue) by Computer, bin(TimeGenerated, 5m)
        | order by TimeGenerated desc
    """,
    
    "disk_space": """
        Perf
        | where TimeGenerated > ago(1h)
        | where ObjectName == "LogicalDisk" and CounterName == "% Free Space"
        | summarize AvgFreeSpace = avg(CounterValue) by Computer, InstanceName
        | order by AvgFreeSpace asc
    """,
    
    # Security
    "failed_logins": """
        SecurityEvent
        | where TimeGenerated > ago(24h)
        | where EventID == 4625
        | summarize FailedAttempts = count() by Account, Computer, IpAddress
        | order by FailedAttempts desc
    """,
    
    "successful_logins": """
        SecurityEvent
        | where TimeGenerated > ago(24h)
        | where EventID == 4624
        | summarize LoginCount = count() by Account, Computer
        | order by LoginCount desc
        | take 50
    """,
    
    # Application Insights
    "request_performance": """
        AppRequests
        | where TimeGenerated > ago(1h)
        | summarize 
            RequestCount = count(),
            AvgDuration = avg(DurationMs),
            P95Duration = percentile(DurationMs, 95)
          by Name, bin(TimeGenerated, 5m)
        | order by TimeGenerated desc
    """,
    
    "failed_requests": """
        AppRequests
        | where TimeGenerated > ago(24h)
        | where Success == false
        | summarize FailureCount = count() by Name, ResultCode
        | order by FailureCount desc
    """,
    
    "exceptions": """
        AppExceptions
        | where TimeGenerated > ago(24h)
        | summarize ExceptionCount = count() by ExceptionType, ProblemId
        | order by ExceptionCount desc
        | take 20
    """,
    
    # Container/Kubernetes
    "container_logs": """
        ContainerLog
        | where TimeGenerated > ago(1h)
        | where LogEntry contains "error" or LogEntry contains "Error"
        | project TimeGenerated, ContainerID, LogEntry
        | order by TimeGenerated desc
        | take 100
    """,
    
    "pod_restarts": """
        KubeEvents
        | where TimeGenerated > ago(24h)
        | where Reason == "Started"
        | summarize RestartCount = count() by Name, Namespace
        | order by RestartCount desc
    """,
    
    # Heartbeat/Availability
    "agent_heartbeat": """
        Heartbeat
        | summarize LastHeartbeat = max(TimeGenerated) by Computer, OSType, Version
        | extend MinutesAgo = datetime_diff('minute', now(), LastHeartbeat)
        | order by MinutesAgo desc
    """,
    
    "offline_agents": """
        Heartbeat
        | summarize LastHeartbeat = max(TimeGenerated) by Computer
        | where LastHeartbeat < ago(30m)
        | project Computer, LastHeartbeat, MinutesOffline = datetime_diff('minute', now(), LastHeartbeat)
        | order by MinutesOffline desc
    """
}


def get_query(name: str) -> str:
    """Get a sample query by name."""
    return SAMPLE_QUERIES.get(name, "").strip()


def list_queries() -> list:
    """List all available sample queries."""
    return list(SAMPLE_QUERIES.keys())
