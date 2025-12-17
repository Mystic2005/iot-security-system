from flask import Flask, jsonify, render_template, request
import requests
from database import db

app = Flask(__name__)

# System state storage
system_state = {
    'alarm_on': False,
    'system_on': True
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def success_response(data=None, message=None, status=200):
    response = {'success': True}
    if data:
        response.update(data)
    if message:
        response['message'] = message
    return jsonify(response), status


def error_response(message, status=400):
    return jsonify({'success': False, 'error': message}), status


def validate_fields(data, required_fields):
    if not data:
        return False, "No data provided"

    missing = [field for field in required_fields if field not in data]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    return True, None


def add_event_helper(data, event_type, required_fields):
    valid, error_msg = validate_fields(data, required_fields)
    if not valid:
        return error_response(error_msg)

    event_params = {
        'timestamp': data['timestamp'],
        'sensor_name': data['sensor_name'],
        'from_source': event_type
    }

    event_id = db.add_event(**event_params)

    return success_response(
        data={'event_id': event_id},
        message=f"{event_type.upper()} event added successfully",
        status=201
    )


def toggle_state(state_key, state_name):
    data = request.get_json()
    valid, error_msg = validate_fields(data, ['active'])
    if not valid:
        return error_response(error_msg)

    system_state[state_key] = bool(data['active'])
    status = 'activated' if system_state[state_key] else 'deactivated'

    return success_response(
        data={state_key: system_state[state_key]},
        message=f"{state_name} {status}"
    )


# ============================================================================
# WEB INTERFACE ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')


# ============================================================================
# API ROUTES - EVENTS
# ============================================================================

@app.route('/api/alert', methods=['POST'])
def add_alert_event():
    data = request.get_json()

    if not data:
        return error_response("No data provided")

    timestamp = data.get('timestamp')
    sensor_name = data.get('sensor_name')
    description = data.get('description')
    from_source = data.get('from_source', 'sensors')

    if not timestamp or not sensor_name:
        return error_response("Missing required fields: timestamp, sensor_name")

    event_id = db.add_event(
        timestamp=timestamp,
        sensor_name=sensor_name,
        description=description,
        from_source=from_source
    )

    return success_response(
        data={'event_id': event_id},
        message="Alert event added successfully",
        status=201
    )

@app.route('/api/events', methods=['GET'])
def get_events():
    limit = request.args.get('limit', type=int)
    sensor_name = request.args.get('sensor', type=str)
    from_source = request.args.get('from_source', type=str)

    if sensor_name:
        events = db.get_events_by_sensor(sensor_name, limit)
    elif from_source:
        events = db.get_all_events(limit, from_source)
    else:
        events = db.get_all_events(limit)

    return success_response(data={'count': len(events), 'events': events})


# ============================================================================
# API ROUTES - STATISTICS
# ============================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    all_events = db.get_all_events()
    sensor_counts = {}

    for event in all_events:
        sensor_name = event['sensor_name']
        sensor_counts[sensor_name] = sensor_counts.get(sensor_name, 0) + 1

    return success_response(data={
        'total_events': db.get_event_count(),
        'sensor_counts': sensor_counts
    })


# ============================================================================
# API ROUTES - SYSTEM CONTROL
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    # Synchronize with the actual security system state
    try:
        response = requests.get('http://127.0.0.1:5001/state', timeout=1)
        if response.status_code == 200:
            security_state = response.json()
            system_state['system_on'] = security_state.get('armed', True)
            system_state['alarm_on'] = security_state.get('alarm', False)
    except Exception as e:
        print(f"Failed to get state from security system: {e}")

    return success_response(data=system_state)


@app.route('/api/alarm', methods=['POST'])
def set_alarm():
    response = toggle_state('alarm_on', 'Alarm')

    if response[1] == 200:
        try:
            if system_state['alarm_on']:
                requests.post('http://127.0.0.1:5001/emergency', timeout=1)
            else:
                requests.post('http://127.0.0.1:5001/reset', timeout=1)
        except Exception as e:
            print(f"Failed to communicate with security system: {e}")

    return response


@app.route('/api/system', methods=['POST'])
def set_system():
    response = toggle_state('system_on', 'System')

    if response[1] == 200:
        try:
            if system_state['system_on']:
                requests.post('http://127.0.0.1:5001/arm', timeout=1)
            else:
                requests.post('http://127.0.0.1:5001/disarm', timeout=1)
        except Exception as e:
            print(f"Failed to communicate with security system: {e}")

    return response


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # app.run(host='127.0.0.1', port=5000, debug=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
