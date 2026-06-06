# Daylight Microservice -- Stories 1, 2, and 3.
#
# Listens on tcp://*:5555 for ZeroMQ REQ/REP requests.
#
# Supported actions:
#   "get_day"   : single date at one location.
#   "get_range" : N consecutive days starting from a given date.
#
# Run with: python3 daylight_service.py

import json
from datetime import datetime, timedelta, timezone

import zmq
from astral import LocationInfo
from astral.sun import sun


PORT = 5555


# Compute sunrise, sunset, total daylight for one day at one location.
# Returns local-time strings derived from the longitude (15 degrees per hour).
def compute_one_day(lat, lon, date_obj):
    offset_hours = round(lon / 15)
    local_tz = timezone(timedelta(hours=offset_hours))

    location = LocationInfo(latitude=lat, longitude=lon, timezone="UTC")
    s = sun(location.observer, date=date_obj, tzinfo=local_tz)

    sunrise = s["sunrise"]
    sunset = s["sunset"]
    total_minutes = int((sunset - sunrise).total_seconds() // 60)

    return {
        "date": date_obj.strftime("%Y-%m-%d"),
        "sunrise": sunrise.strftime("%H:%M"),
        "sunset": sunset.strftime("%H:%M"),
        "total_daylight_minutes": total_minutes,
    }


# Validate that lat, lon, date_str are the right types and that the date
# string parses. Returns the parsed date object on success.
def validate_common(lat, lon, date_str):
    if not isinstance(lat, (int, float)) or isinstance(lat, bool):
        raise ValueError("latitude must be a number")
    if not isinstance(lon, (int, float)) or isinstance(lon, bool):
        raise ValueError("longitude must be a number")
    if not isinstance(date_str, str):
        raise ValueError("date must be a string in YYYY-MM-DD format")
    return datetime.strptime(date_str, "%Y-%m-%d").date()


# Validate that num_days is an integer (not a float, string, bool, etc.).
def validate_num_days(num_days):
    if isinstance(num_days, bool) or not isinstance(num_days, int):
        raise ValueError("num_days must be an integer")


# Build the response for a single-day lookup.
def compute_single_day(lat, lon, date_str):
    parsed = validate_common(lat, lon, date_str)
    record = compute_one_day(lat, lon, parsed)
    return {
        "latitude": lat,
        "longitude": lon,
        **record,
    }


# Build the response for a date-range lookup.
def compute_date_range(lat, lon, date_str, num_days):
    start_date = validate_common(lat, lon, date_str)
    validate_num_days(num_days)

    days = []
    for offset in range(num_days):
        d = start_date + timedelta(days=offset)
        days.append(compute_one_day(lat, lon, d))

    return {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "num_days": num_days,
        "days": days,
    } 


# Parse one JSON request and produce one JSON response.
# Story 3: never crash. Any failure -> JSON error response, service keeps running.
def handle_request(raw_request):
    try:
        req = json.loads(raw_request)
    except json.JSONDecodeError:
        return json.dumps({"error": "request was not valid JSON"})

    if not isinstance(req, dict):
        return json.dumps({"error": "request must be a JSON object"})

    action = req.get("action")
    lat = req.get("latitude")
    lon = req.get("longitude")
    date_str = req.get("date")

    if action not in ("get_day", "get_range"):
        return json.dumps({
            "error": f"unsupported action '{action}'; supported actions are "
                     f"'get_day' and 'get_range'"
        })
    if lat is None:
        return json.dumps({"error": "missing required field: latitude"})
    if lon is None:
        return json.dumps({"error": "missing required field: longitude"})
    if date_str is None:
        return json.dumps({"error": "missing required field: date"})

    try:
        if action == "get_day":
            result = compute_single_day(lat, lon, date_str)
        else:
            num_days = req.get("num_days")
            if num_days is None:
                return json.dumps({
                    "error": "missing required field for get_range: num_days"
                })
            result = compute_date_range(lat, lon, date_str, num_days)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        # Catch-all so the service never dies from unexpected library errors.
        return json.dumps({"error": f"internal error: {type(e).__name__}: {e}"})

    return json.dumps(result)


# Main server loop.
def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{PORT}")
    print(f"[daylight] Listening on tcp://*:{PORT}")

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