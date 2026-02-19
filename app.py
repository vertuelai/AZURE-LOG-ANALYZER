"""
Flask Web API for Azure Log Analytics Analyzer
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import json
import io
from datetime import datetime, timedelta

from analyzer import LogAnalyzer
from config import Config

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Global analyzer instance
analyzer = None
last_results = None


def get_analyzer():
    """Get or create analyzer instance."""
    global analyzer
    if analyzer is None:
        try:
            analyzer = LogAnalyzer()
        except Exception as e:
            return None, str(e)
    return analyzer, None


@app.route('/')
def index():
    """Serve the main frontend."""
    return render_template('index.html')


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/api/config/status')
def config_status():
    """Check configuration status."""
    try:
        Config.validate()
        return jsonify({
            'configured': True,
            'workspace_id': Config.WORKSPACE_ID[:8] + '...' if Config.WORKSPACE_ID else None,
            'ai_enabled': bool(Config.AZURE_OPENAI_ENDPOINT and Config.AZURE_OPENAI_KEY)
        })
    except Exception as e:
        return jsonify({
            'configured': False,
            'error': str(e)
        })


@app.route('/api/tables')
def get_tables():
    """Get available tables."""
    global analyzer
    try:
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        tables = log_analyzer.available_tables
        return jsonify({'tables': tables})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/table/<table_name>/schema')
def get_table_schema(table_name):
    """Get schema for a specific table."""
    try:
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        df = log_analyzer.client.get_table_schema(table_name)
        schema = df.to_dict(orient='records')
        return jsonify({'table': table_name, 'schema': schema})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/query/natural', methods=['POST'])
def natural_language_query():
    """Execute a natural language query."""
    global last_results
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        time_filter = data.get('timeFilter', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        # Translate to KQL
        kql = log_analyzer.translator.translate(question, log_analyzer.available_tables)
        
        # Apply time filter if provided AND if KQL doesn't already have a time filter
        if time_filter:
            kql_lower = kql.lower()
            # Check if KQL already has a TimeGenerated filter
            has_time_filter = 'timegenerated' in kql_lower and ('ago(' in kql_lower or 'between' in kql_lower or '>=' in kql_lower)
            
            if not has_time_filter:
                # Insert time filter after the table name (first line)
                lines = kql.strip().split('\n')
                if len(lines) > 0:
                    # Insert time filter after first line (table name)
                    lines.insert(1, time_filter)
                    kql = '\n'.join(lines)
        
        # Execute query
        df = log_analyzer.client.query(kql)
        last_results = df
        
        # Convert to JSON-serializable format
        results = df.to_dict(orient='records') if not df.empty else []
        columns = list(df.columns) if not df.empty else []
        
        return jsonify({
            'success': True,
            'kql': kql,
            'results': results,
            'columns': columns,
            'row_count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/results', methods=['POST'])
def analyze_results():
    """AI analysis of query results - provides insights and summary."""
    try:
        data = request.get_json()
        results = data.get('results', [])
        columns = data.get('columns', [])
        question = data.get('question', '')
        kql = data.get('kql', '')
        
        if not results:
            return jsonify({'error': 'No results to analyze'}), 400
        
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        # Check if AI is available
        if not log_analyzer.translator.client:
            return jsonify({'error': 'AI not configured'}), 400
        
        # Generate AI insights
        insights = generate_ai_insights(
            results=results,
            columns=columns,
            question=question,
            kql=kql,
            client=log_analyzer.translator.client
        )
        
        return jsonify({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_ai_insights(results, columns, question, kql, client):
    """Generate AI-powered insights from query results."""
    from config import Config
    
    # Prepare a summary of the data for AI analysis
    row_count = len(results)
    
    # Get sample data (first 10 rows) for context
    sample_data = results[:10] if row_count > 10 else results
    
    # Build a compact data summary
    data_summary = f"""
Query: {question}
KQL: {kql}
Total Records: {row_count}
Columns: {', '.join(columns)}

Sample Data (first {len(sample_data)} rows):
"""
    for i, row in enumerate(sample_data):
        row_str = " | ".join(f"{k}: {str(v)[:50]}" for k, v in row.items())
        data_summary += f"\n{i+1}. {row_str[:200]}"
    
    # If there are numeric columns, add basic stats
    numeric_stats = []
    for col in columns:
        values = [r.get(col) for r in results if r.get(col) is not None]
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if numeric_values and len(numeric_values) > 1:
            avg_val = sum(numeric_values) / len(numeric_values)
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            numeric_stats.append(f"{col}: avg={avg_val:.2f}, min={min_val}, max={max_val}")
    
    if numeric_stats:
        data_summary += f"\n\nNumeric Statistics:\n" + "\n".join(numeric_stats)
    
    # Count unique values for key columns
    unique_counts = []
    for col in columns[:5]:  # First 5 columns
        unique_values = set(str(r.get(col, ''))[:100] for r in results)
        if len(unique_values) <= 10:
            unique_counts.append(f"{col}: {len(unique_values)} unique values - {list(unique_values)[:5]}")
        else:
            unique_counts.append(f"{col}: {len(unique_values)} unique values")
    
    if unique_counts:
        data_summary += f"\n\nUnique Value Counts:\n" + "\n".join(unique_counts)
    
    system_prompt = """You are an Azure Log Analytics expert. Analyze the query results and provide:
1. **Summary**: A brief 1-2 sentence summary of what the data shows
2. **Key Findings**: 3-5 bullet points of important observations
3. **Anomalies/Concerns**: Any issues, errors, or unusual patterns (if any)
4. **Recommendations**: 1-2 actionable suggestions based on the data

Keep your response concise and actionable. Use markdown formatting.
Focus on security implications, performance issues, and operational insights."""

    try:
        response = client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT or "gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze these Azure log query results:\n{data_summary}"}
            ],
            temperature=0.3,
            max_tokens=600
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Unable to generate insights: {str(e)}"


@app.route('/api/chat', methods=['POST'])
def ai_chat():
    """AI Chat endpoint for conversational analysis."""
    try:
        data = request.get_json()
        message = data.get('message', '')
        context = data.get('context', {})
        chat_history = data.get('history', [])
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        if not log_analyzer.translator.client:
            return jsonify({'error': 'AI not configured'}), 400
        
        # Generate chat response
        response = generate_chat_response(
            message=message,
            context=context,
            chat_history=chat_history,
            client=log_analyzer.translator.client,
            translator=log_analyzer.translator,
            available_tables=log_analyzer.available_tables
        )
        
        return jsonify({
            'success': True,
            'response': response['message'],
            'suggested_query': response.get('suggested_query'),
            'action': response.get('action')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_chat_response(message, context, chat_history, client, translator, available_tables):
    """Generate AI chat response with context awareness."""
    from config import Config
    
    # Build context summary
    context_summary = ""
    if context.get('results'):
        results = context['results']
        columns = context.get('columns', [])
        context_summary = f"""
Current Data Context:
- Query: {context.get('question', 'N/A')}
- KQL: {context.get('kql', 'N/A')}
- Records: {len(results)}
- Columns: {', '.join(columns[:10])}
- Sample: {str(results[:3])[:500]}
"""
    
    # Build chat history for context
    history_messages = []
    for msg in chat_history[-6:]:  # Last 6 messages for context
        history_messages.append({
            "role": msg.get('role', 'user'),
            "content": msg.get('content', '')
        })
    
    system_prompt = f"""You are an Azure Log Analytics assistant helping users analyze their logs.

{context_summary}

Available tables: {', '.join(available_tables[:20]) if available_tables else 'Unknown'}

Your capabilities:
1. Answer questions about the current query results
2. Explain patterns, errors, or anomalies in the data
3. Suggest follow-up KQL queries (prefix with "SUGGESTED_QUERY:")
4. Help troubleshoot issues based on log data
5. Provide security and performance insights

Guidelines:
- Be concise and actionable
- If suggesting a query, include the full KQL after "SUGGESTED_QUERY:"
- Reference specific data points when possible
- Use markdown for formatting
- If the user asks for a new query, generate it and mark with SUGGESTED_QUERY:"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": message})
    
    try:
        response = client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT or "gpt-4",
            messages=messages,
            temperature=0.4,
            max_tokens=800
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Check if there's a suggested query
        suggested_query = None
        action = None
        if "SUGGESTED_QUERY:" in response_text:
            parts = response_text.split("SUGGESTED_QUERY:")
            response_text = parts[0].strip()
            if len(parts) > 1:
                # Extract the query (might be in code block or plain text)
                query_part = parts[1].strip()
                # Remove markdown code blocks if present
                query_part = query_part.replace("```kql", "").replace("```", "").strip()
                # Get just the first query (before any newline explanations)
                suggested_query = query_part.split('\n\n')[0].strip()
                action = 'suggest_query'
        
        return {
            'message': response_text,
            'suggested_query': suggested_query,
            'action': action
        }
    except Exception as e:
        return {
            'message': f"Sorry, I encountered an error: {str(e)}",
            'suggested_query': None,
            'action': None
        }


@app.route('/api/query/kql', methods=['POST'])
def kql_query():
    """Execute a raw KQL query."""
    global last_results
    
    try:
        data = request.get_json()
        kql = data.get('kql', '')
        timespan_days = data.get('timespan_days', 1)
        
        if not kql:
            return jsonify({'error': 'KQL query is required'}), 400
        
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        # Execute query
        df = log_analyzer.client.query(kql, timespan=timedelta(days=timespan_days))
        last_results = df
        
        # Convert to JSON-serializable format
        results = df.to_dict(orient='records') if not df.empty else []
        columns = list(df.columns) if not df.empty else []
        
        return jsonify({
            'success': True,
            'results': results,
            'columns': columns,
            'row_count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/<format_type>')
def export_results(format_type):
    """Export last results to CSV or JSON."""
    global last_results
    
    if last_results is None or last_results.empty:
        return jsonify({'error': 'No results to export'}), 400
    
    try:
        if format_type == 'csv':
            output = io.StringIO()
            last_results.to_csv(output, index=False)
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode()),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'log_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
        elif format_type == 'json':
            output = last_results.to_json(orient='records', indent=2)
            
            return send_file(
                io.BytesIO(output.encode()),
                mimetype='application/json',
                as_attachment=True,
                download_name=f'log_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
        else:
            return jsonify({'error': 'Invalid format. Use csv or json'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sample-queries')
def get_sample_queries():
    """Get sample queries for inspiration."""
    samples = [
        {
            'category': 'Errors & Exceptions',
            'queries': [
                'Show me all errors from the last hour',
                'What are the top 10 exceptions today?',
                'List failed requests by status code'
            ]
        },
        {
            'category': 'Security',
            'queries': [
                'Show failed sign-in attempts',
                'List suspicious activities in the last 24 hours',
                'Who accessed the resources yesterday?'
            ]
        },
        {
            'category': 'Performance',
            'queries': [
                'Show slow requests over 5 seconds',
                'What is the average response time by endpoint?',
                'List requests with high CPU usage'
            ]
        },
        {
            'category': 'Activity',
            'queries': [
                'What resources were created today?',
                'Show all deployment activities',
                'List configuration changes this week'
            ]
        }
    ]
    return jsonify({'samples': samples})


@app.route('/api/instructions', methods=['GET'])
def get_instructions():
    """Get current custom instructions."""
    try:
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        instructions = log_analyzer.translator.custom_instructions
        return jsonify({'instructions': instructions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/instructions', methods=['POST'])
def update_instructions():
    """Update custom instructions."""
    try:
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        new_instructions = request.json
        
        # Validate structure
        if not isinstance(new_instructions, dict):
            return jsonify({'error': 'Instructions must be a JSON object'}), 400
        
        # Save to file
        instructions_path = log_analyzer.translator.INSTRUCTIONS_FILE
        with open(instructions_path, 'w', encoding='utf-8') as f:
            json.dump(new_instructions, f, indent=2)
        
        # Reload in translator
        log_analyzer.translator.reload_instructions()
        
        return jsonify({
            'success': True,
            'message': 'Instructions updated successfully',
            'instructions': log_analyzer.translator.custom_instructions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/instructions/reload', methods=['POST'])
def reload_instructions():
    """Reload instructions from file."""
    try:
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        instructions = log_analyzer.translator.reload_instructions()
        return jsonify({
            'success': True,
            'message': 'Instructions reloaded',
            'instructions': instructions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Azure Log Analytics Analyzer Web UI")
    print("📡 Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
