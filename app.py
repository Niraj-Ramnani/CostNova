from flask import Flask, render_template, request, redirect, url_for, session
import boto3
import pandas as pd
from model import predict_costs, get_optimization_suggestions
from prometheus_client import Counter, generate_latest, REGISTRY

app = Flask(__name__)
app.secret_key = 'hackathon_secret'

REQUESTS = Counter('flask_requests_total', 'Total number of requests')
users = {'admin': 'password123'}

def load_aws_data(access_key=None, secret_key=None):
    try:
        if access_key and secret_key:
            ec2 = boto3.client('ec2', region_name='us-west-1', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        else:
            ec2 = boto3.client('ec2', region_name='us-west-1')
        response = ec2.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append({
                    'instance_id': instance['InstanceId'],
                    'region': instance['Placement']['AvailabilityZone'][:-1],
                    'usage_hours': 24 if instance['State']['Name'] == 'running' else 0,
                    'cost_usd': 10.50 if instance['State']['Name'] == 'running' else 0.0,
                    'status': instance['State']['Name']
                })
        return pd.DataFrame(instances) if instances else pd.read_csv('mock_data.csv')
    except Exception as e:
        print(f"Error fetching AWS data: {e}")
        return pd.read_csv('mock_data.csv')

def load_azure_data():
    return pd.read_csv('mock_data/azure_mock.csv')

def load_gcp_data():
    return pd.read_csv('mock_data/gcp_mock.csv')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    REQUESTS.inc()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        platform = request.form['platform']
        aws_access_key = request.form.get('aws_access_key', '').strip()
        aws_secret_key = request.form.get('aws_secret_key', '').strip()
        if username in users and users[username] == password:
            session['logged_in'] = True
            session['platform'] = platform
            if platform == 'aws' and aws_access_key and aws_secret_key:
                session['aws_access_key'] = aws_access_key
                session['aws_secret_key'] = aws_secret_key
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials, try again.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    REQUESTS.inc()
    platform = session.get('platform')
    
    if platform == 'aws':
        aws_access_key = session.get('aws_access_key')
        aws_secret_key = session.get('aws_secret_key')
        data = load_aws_data(aws_access_key, aws_secret_key)
        chart_data = {'labels': data['instance_id'].tolist(), 'usage': data['usage_hours'].tolist(), 'costs': data['cost_usd'].tolist()}
    elif platform == 'azure':
        data = load_azure_data()
        chart_data = {'labels': data['vm_id'].tolist(), 'usage': data['usage_hours'].tolist(), 'costs': data['cost_usd'].tolist()}
    else:  # gcp
        data = load_gcp_data()
        chart_data = {'labels': data['instance_id'].tolist(), 'usage': data['usage_hours'].tolist(), 'costs': data['cost_usd'].tolist()}
    
    predicted_cost = predict_costs(data)
    suggestions = get_optimization_suggestions(data, platform)
    return render_template('dashboard.html', platform=platform, chart_data=chart_data, predicted_cost=predicted_cost, suggestions=suggestions)

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; version=0.0.4'}

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('platform', None)
    session.pop('aws_access_key', None)
    session.pop('aws_secret_key', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
