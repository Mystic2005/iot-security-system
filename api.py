from flask import Flask, jsonify, render_template, request
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

    if 'card_name' in data:
        event_params['card_name'] = data['card_name']

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

@app.route('/api/events', methods=['GET'])
def get_events():
    limit = request.args.get('limit', type=int)
    sensor_name = request.args.get('sensor', type=str)
    from_source = request.args.get('from', type=str)

    events = (db.get_events_by_sensor(sensor_name, limit) if sensor_name
              else db.get_all_events(limit, from_source))

    return success_response(data={'count': len(events), 'events': events})


@app.route('/api/sensors', methods=['POST'])
def add_sensor_event():
    return add_event_helper(
        data=request.get_json(),
        event_type='sensors',
        required_fields=['timestamp', 'sensor_name']
    )


@app.route('/api/rfid', methods=['POST'])
def add_rfid_event():
    return add_event_helper(
        data=request.get_json(),
        event_type='rfid',
        required_fields=['timestamp', 'sensor_name', 'card_name']
    )


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
    return success_response(data=system_state)


@app.route('/api/alarm', methods=['POST'])
def set_alarm():
    return toggle_state('alarm_on', 'Alarm')


@app.route('/api/system', methods=['POST'])
def set_system():
    return toggle_state('system_on', 'System')


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # For Raspberry Pi: change host to '0.0.0.0' for network access
    app.run(host='127.0.0.1', port=5000, debug=False)
