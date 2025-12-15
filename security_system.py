import time
import threading
from datetime import datetime

from gpiozero import MotionSensor, DistanceSensor
from mfrc522 import SimpleMFRC522

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
PIR_PIN = 4
ULTRA_TRIG = 23
ULTRA_ECHO = 24

pir = MotionSensor(PIR_PIN)
dist = DistanceSensor(trigger=ULTRA_TRIG, echo=ULTRA_ECHO, max_distance=4)
rfid = SimpleMFRC522()

_running = False

def trigger_alarm(reason):
    if not state["armed"]:
        return

    state["alarm"] = True
    state["alarm_reason"] = reason
    state["alarm_since"] = datetime.utcnow().isoformat()


def reset_alarm():
    state["alarm"] = False
    state["alarm_reason"] = None
    state["alarm_since"] = None


def _thread_pir():
    while _running:
        pir.wait_for_motion()
        state["motion"] = True
        state["motion_last"] = datetime.utcnow().isoformat()
        if state["armed"]:
            trigger_alarm("motion")
        
        pir.wait_for_no_motion()
        state["motion"] = False
gi
def _thread_ultrasonic():
    while _running:
        d = dist.distance * 100
        d = round(d, 1)
        state["distance_cm"] = d
        state["distance_last"] = datetime.utcnow().isoformat()

        if state["armed"] and d <= state["distance_threshold"]:
            trigger_alarm(f"distance<{state['distance_threshold']}cm")

        time.sleep(0.2)


def _thread_rfid():
    while _running:
        try:
            tag, txt = rfid.read()
            state["rfid"] = tag
            state["rfid_last"] = datetime.utcnow().isoformat()

            # toggle armed state
            state["armed"] = not state["armed"]
            reset_alarm()

        except Exception:
            pass

        time.sleep(0.3)

# api pt colegu
def start_sensors():
    """Pornește senzorii în thread-uri."""
    global _running
    _running = True

    threading.Thread(target=_thread_pir, daemon=True).start()
    threading.Thread(target=_thread_ultrasonic, daemon=True).start()
    threading.Thread(target=_thread_rfid, daemon=True).start()


def stop_sensors():
    """Închide thread-urile."""
    global _running
    _running = False


def get_state():
    """Returnează starea completă a sistemului."""
    return state


def arm():
    state["armed"] = True
    reset_alarm()


def disarm():
    state["armed"] = False
    reset_alarm()


def reset():
    reset_alarm()


# test local
if __name__ == "__main__":
    start_sensors()
    while True:
        print(get_state())
        time.sleep(1)
