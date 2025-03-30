import pandas as pd
from sklearn.linear_model import LinearRegression

def predict_costs(data):
    X = data[['usage_hours']].values
    y = data['cost_usd'].values
    model = LinearRegression()
    model.fit(X, y)
    predicted = model.predict(X)
    return round(predicted.sum(), 2)

def get_optimization_suggestions(data, provider):
    suggestions = []
    total_savings = 0
    status_key = 'status'
    id_key = 'instance_id' if provider in ['aws', 'gcp'] else 'vm_id'
    stopped_state = 'stopped' if provider == 'aws' else 'TERMINATED' if provider == 'gcp' else 'stopped'
    for _, row in data.iterrows():
        if row[status_key] == stopped_state or (row[status_key] == ('running' if provider != 'gcp' else 'RUNNING') and row['usage_hours'] == 0):
            suggestion = f"Shut down or terminate unused {provider.upper()} instance {row[id_key]} to save ${row['cost_usd']}"
            suggestions.append(suggestion)
            total_savings += row['cost_usd']
        elif row['usage_hours'] < 10 and row[status_key] == ('running' if provider != 'gcp' else 'RUNNING'):
            suggestion = f"Downsize {provider.upper()} instance {row[id_key]} (low usage: {row['usage_hours']} hrs)"
            suggestions.append(suggestion)
            total_savings += row['cost_usd'] * 0.3
    if not suggestions:
        suggestions.append("No immediate optimizations detected.")
    else:
        suggestions.append(f"Total potential savings: ${round(total_savings, 2)}")
    return suggestions
