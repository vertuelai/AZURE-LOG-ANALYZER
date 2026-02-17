# 🔍 Azure Log Analytics Analyzer

A powerful tool to query Azure Log Analytics using **natural language** or **KQL (Kusto Query Language)**.

## ✨ Features

- **Natural Language Queries**: Ask questions in plain English
- **AI-Powered Translation**: Converts your questions to KQL (with OpenAI/Azure OpenAI)
- **🆕 Custom Instructions**: Define business rules and mappings for query translation
- **Interactive CLI**: User-friendly command-line interface
- **🆕 Futuristic Web UI**: Beautiful, modern web interface with real-time analytics
- **KQL Support**: Run raw KQL queries directly
- **Table Discovery**: List available tables and view schemas
- **Export Results**: Save results to CSV or JSON
- **Rich Output**: Beautiful formatted tables with syntax highlighting

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd azure-log-analyzer
pip install -r requirements.txt
```

### 2. Configure Azure Credentials

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your Azure details:

```env
# Required
AZURE_LOG_ANALYTICS_WORKSPACE_ID=your-workspace-id

# Optional: For natural language support
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### 3. Authenticate with Azure

```bash
# Option 1: Use Azure CLI (recommended)
az login

# Option 2: Service Principal (set in .env)
```

### 4. Run the Application

#### 🌐 Web UI (Recommended)
```bash
python app.py
```
Then open **http://localhost:5000** in your browser.

#### 💻 CLI Mode
```bash
python main.py
```

## 📖 Usage

### 🌐 Web Interface

The futuristic web UI provides:
- **Query Terminal**: Enter natural language questions or KQL queries
- **Data Stream**: View results in a beautiful table format
- **Data Sources**: Browse available tables and schemas
- **Real-time Stats**: Track query performance and connection status

Features:
- Press `Ctrl+Enter` to execute queries
- Press `/` to focus the query input
- Click on sample queries for quick testing
- Export results to CSV or JSON
- Copy generated KQL to clipboard

### 💻 Interactive CLI Mode

```bash
python main.py
```

Then ask questions:

```
Query> show me errors from the last hour
Query> what are the top 10 most common exceptions?
Query> list all failed deployments in the last week
Query> kql: AzureActivity | take 10
```

### Single Query Mode

```bash
# Natural language
python main.py -q "show me all errors from today"

# KQL query
python main.py -k "AzureActivity | take 10"

# List tables
python main.py --list-tables
```

### Commands

| Command | Description |
|---------|-------------|
| `help` | Show help message |
| `tables` | List available tables |
| `describe <table>` | Show table schema |
| `kql: <query>` | Execute raw KQL |
| `export csv <file>` | Export results to CSV |
| `export json <file>` | Export results to JSON |
| `exit` | Exit the application |

## 📋 Custom Instructions

The analyzer supports custom instructions via `instructions.json` that guide AI query translation.

### Instructions File Structure

```json
{
  "global_rules": [
    "Always use TimeGenerated for time filtering",
    "Default time range is last 24 hours"
  ],
  
  "table_mappings": {
    "mappings": [
      {
        "terms": ["VM availability", "server status"],
        "table": "Heartbeat",
        "key_column": "Computer",
        "notes": "Use Heartbeat for VM health"
      }
    ]
  },
  
  "resource_aliases": {
    "aliases": {
      "prod-web": "webapp-production-001",
      "main-vm": "VMuaenapp"
    }
  },
  
  "column_mappings": {
    "ip_address": {
      "AppServiceHTTPLogs": "CIp",
      "SigninLogs": "IPAddress"
    }
  },
  
  "business_context": {
    "critical_resources": ["VMuaenapp"],
    "notes": ["Production VMs start with 'prod-'"]
  }
}
```

### Managing Instructions

**Via API:**
```bash
# Get current instructions
curl http://localhost:5000/api/instructions

# Update instructions
curl -X POST http://localhost:5000/api/instructions \
  -H "Content-Type: application/json" \
  -d @instructions.json

# Reload from file
curl -X POST http://localhost:5000/api/instructions/reload
```

**Edit `instructions.json` directly** and restart the app, or call the reload endpoint.

## 🎯 Example Queries

### Natural Language

- "Show me all errors from the last 24 hours"
- "What resources were created yesterday?"
- "List failed sign-in attempts"
- "Show CPU usage trends for the last week"
- "Count events by severity level"
- "What are the top error messages?"

### KQL

```kql
// Recent activity
AzureActivity
| where TimeGenerated > ago(1h)
| take 100

// Error summary
AzureDiagnostics
| where Level == "Error"
| summarize count() by ResourceType

// Performance metrics
Perf
| where ObjectName == "Processor"
| summarize avg(CounterValue) by Computer, bin(TimeGenerated, 5m)
```

## 📊 Sample Queries

The `sample_queries.py` file contains ready-to-use KQL queries for:

- Activity logs
- Diagnostics
- Performance metrics
- Security events
- Application Insights
- Container/Kubernetes logs
- Agent heartbeats

## 🔧 Programmatic Usage

```python
from analyzer import LogAnalyzer, ask, query, tables

# Create analyzer
analyzer = LogAnalyzer()

# Natural language query
results = analyzer.ask("show me errors from last hour")

# KQL query
results = analyzer.query("AzureActivity | take 10")

# List tables
analyzer.list_tables()

# Describe table
analyzer.describe_table("AzureActivity")

# Export results
analyzer.export(results, "output.csv", "csv")

# Shortcut functions
results = ask("what are the recent failures?")
results = query("Heartbeat | take 5")
tables()
```

## 🔐 Authentication Methods

### Azure CLI (Recommended for Development)

```bash
az login
```

### Service Principal

Set in `.env`:
```env
AZURE_TENANT_ID=xxx
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx
```

### Managed Identity

Works automatically in Azure VMs, App Service, Functions, etc.

## 📁 Project Structure

```
azure-log-analyzer/
├── main.py              # CLI entry point
├── analyzer.py          # Main analyzer class
├── azure_client.py      # Azure SDK wrapper
├── query_translator.py  # NL to KQL translation
├── result_formatter.py  # Output formatting
├── config.py            # Configuration
├── sample_queries.py    # Example KQL queries
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
└── README.md            # This file
```

## 🤝 Contributing

Feel free to extend this tool with:
- Additional query patterns
- More export formats
- Web UI interface
- Alerting capabilities
- Query history
- Saved queries

## 📝 License

MIT License
