
#Daylight Microservice
#Run with: python3 daylight_service.py

import json
from datetime import datetime, date as date_cls, timedelta, timezone

import zmq
from astral import LocationInfo
from astral.sun import sun


PORT = 5555

def compute_daylight(lat, lon, date_str):
    # Validate latitude.
    if not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
        raise ValueError("latitude must be a number between -90 and 90")

    # Validate longitude.
    if not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
        raise ValueError("longitude must be a number between -180 and 180")

    # Validate date string.
    if not isinstance(date_str, str):
        raise ValueError("date must be a string in YYYY-MM-DD format")
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("date must be a string in YYYY-MM-DD format")

    # Use astral to compute sunrise/sunset for the given coords + date.
    offset_hours = round(lon / 15)
    local_tz = timezone(timedelta(hours=offset_hours))

    location = LocationInfo(latitude=lat, longitude=lon, timezone="UTC")
    s = sun(location.observer, date=parsed, tzinfo=local_tz)

    sunrise = s["sunrise"]
    sunset = s["sunset"]
    total_minutes = int((sunset - sunrise).total_seconds() // 60)

    return {
        "latitude": lat,
        "longitude": lon,
        "date": date_str,
        "sunrise": sunrise.strftime("%H:%M"),
        "sunset": sunset.strftime("%H:%M"),
        "total_daylight_minutes": total_minutes,
    }


def handle_request(raw_request):
    #Parse one JSON request string and return a JSON response string.
    try:
        req = json.loads(raw_request)
    except json.JSONDecodeError:
        return json.dumps({"error": "request was not valid JSON"})

    # Story 1 only handles action=get_day. Other actions: not yet implemented.
    action = req.get("action")
    if action != "get_day":
        return json.dumps({
            "error": f"unsupported action '{action}'; this microservice "
                     f"currently supports only 'get_day'"
        })

    # Pull out required fields.
    lat = req.get("latitude")
    lon = req.get("longitude")
    date_str = req.get("date")

    if lat is None:
        return json.dumps({"error": "missing required field: latitude"})
    if lon is None:
        return json.dumps({"error": "missing required field: longitude"})
    if date_str is None:
        return json.dumps({"error": "missing required field: date"})

    try:
        result = compute_daylight(lat, lon, date_str)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    return json.dumps(result)


def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{PORT}")
    print(f"[daylight] Listening on tcp://*:{PORT}")
    print("[daylight] Send a JSON request with:")
    print('  {"action": "get_day", "latitude": <num>, "longitude": <num>, "date": "YYYY-MM-DD"}')
    print("[daylight] Press Ctrl-C to stop.")

    try:
        while True:
            raw = socket.recv_string()
            print(f"[daylight] Received: {raw}")
            response = handle_request(raw)
            print(f"[daylight] Replying: {response}")
            socket.send_string(response)
    except KeyboardInterrupt:
        print()
        print("[daylight] Shutting down.")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    main()