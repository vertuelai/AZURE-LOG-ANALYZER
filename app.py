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
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        log_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 500
        
        # Translate to KQL
        kql = log_analyzer.translator.translate(question, log_analyzer.available_tables)
        
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


if __name__ == '__main__':
    print("🚀 Starting Azure Log Analytics Analyzer Web UI")
    print("📡 Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
