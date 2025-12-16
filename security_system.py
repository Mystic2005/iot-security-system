import time
import threading
import datetime
import os
import requests

from gpiozero import MotionSensor, DistanceSensor, LED
from mfrc522 import SimpleMFRC522
from flask import Flask, request, jsonify

state = {   
    "armed": True,
    "motion": False,
    "motion_last": None,
    "distance_cm": None,
    "distance_last": None,
    "rfid": None,
    "rfid_last": None,
    "alarm": False,
    "alarm_reason": None,
    "alarm_since": None,
    "distance_threshold": 30
}

# senzori initializare
PIR_PIN = 6
ULTRA_TRIG = 27
ULTRA_ECHO = 17
LED_PIN = 21

pir = MotionSensor(PIR_PIN)
dist = DistanceSensor(trigger=ULTRA_TRIG, echo=ULTRA_ECHO, max_distance=4)
rfid = SimpleMFRC522()
led = LED(LED_PIN)

_running = False

ALERT_URL = os.getenv('alert_api', 'http://127.0.0.1:5000/api/alert')
app = Flask(__name__)

def trigger_alarm(reason):
    if not state["armed"]:
        return

    state["alarm"] = True
    state["alarm_reason"] = reason
    state["alarm_since"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    led.on()
    description = get_description(reason)
    data = {
        "time": state["alarm_since"],
        "sensor": reason,
        "description": description
    }
    try:
        requests.post(ALERT_URL, json=data, timeout=5)
    except Exception as e:
        print(f"Failed to send alert: {e}")

def reset_alarm():
    state["alarm"] = False
    state["alarm_reason"] = None
    state["alarm_since"] = None
    led.off()


def get_description(reason):
    if "motion" in reason:
        return "Motion detected"
    elif "distance" in reason:
        return "Front door"
    else:
        return reason


def _thread_pir():
    while _running:
        pir.wait_for_motion()
        state["motion"] = True
        state["motion_last"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if state["armed"]:
            trigger_alarm("motion")
        
        pir.wait_for_no_motion()
        state["motion"] = False

def _thread_ultrasonic():
    while _running:
        d = dist.distance * 100
        d = round(d, 1)
        state["distance_cm"] = d
        state["distance_last"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if state["armed"] and d <= state["distance_threshold"]:
            trigger_alarm(f"distance<{state['distance_threshold']}cm")

        time.sleep(0.2)


def _thread_rfid():
    while _running:
        try:
            tag, txt = rfid.read()
            state["rfid"] = tag
            state["rfid_last"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # toggle armed state
            if state["alarm"]:
                disarm()
            else:
                arm()

            # send rfid info
            data = {
                "type": "rfid",
                "time": state["rfid_last"],
                "tag": "Grandma`s card"
            }
            try:
                requests.post(ALERT_URL, json=data, timeout=5)
            except Exception as e:
                print(f"Failed to send RFID alert: {e}")

        except Exception:
            pass

        time.sleep(0.3)

# api pt colegu
def start_sensors():
    """multi threaded sensors"""
    global _running
    _running = True

    threading.Thread(target=_thread_pir, daemon=True).start()
    threading.Thread(target=_thread_ultrasonic, daemon=True).start()
    threading.Thread(target=_thread_rfid, daemon=True).start()


def stop_sensors():
    """close threads"""
    global _running
    _running = False


def get_state():
    """return the global state"""
    return state


def arm():
    state["armed"] = True
    reset_alarm()
    data = {
        "action": "arm",
        "time": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        requests.post(ALERT_URL, json=data, timeout=5)
    except Exception as e:
        print(f"Failed to send arm alert: {e}")


def disarm():
    state["armed"] = False
    reset_alarm()
    data = {
        "action": "disarm",
        "time": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        requests.post(ALERT_URL, json=data, timeout=5)
    except Exception as e:
        print(f"Failed to send disarm alert: {e}")


@app.route('/arm', methods=['POST'])
def arm_endpoint():
    arm()
    return jsonify({"status": "armed"})

@app.route('/disarm', methods=['POST'])
def disarm_endpoint():
    disarm()
    return jsonify({"status": "disarmed"})

@app.route('/reset', methods=['POST'])
def reset_endpoint():
    reset_alarm()
    return jsonify({"message": "alarm reset"})

@app.route('/emergency', methods=['POST'])
def emergency_endpoint():
    trigger_alarm("emergency")
    return jsonify({"status": "emergency_alarm"})


# test local
if __name__ == "__main__":
    start_sensors()
    app.run(host='0.0.0.0', port=5001)