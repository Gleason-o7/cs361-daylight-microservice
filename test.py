
import json
import zmq


PORT = 5555


def call(label, raw_payload, expectation):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{PORT}")

    print("-" * 62)
    print(f"{label}")
    print(f"  SENT     : {raw_payload}")

    socket.send_string(raw_payload)
    reply = socket.recv_string()
    print(f"  RECEIVED : {reply}")

    try:
        parsed = json.loads(reply)
    except json.JSONDecodeError:
        print("  FAIL: reply was not valid JSON")
        socket.close()
        context.term()
        return

    if expectation == "error":
        if "error" in parsed:
            print(f"  OK: service returned an error response without crashing")
        else:
            print(f"  FAIL: expected an 'error' field, got {list(parsed.keys())}")
    elif expectation == "ok":
        if "sunrise" in parsed:
            print(f"  OK: service is still running and handling valid requests")
        else:
            print(f"  FAIL: expected a 'sunrise' field, got {list(parsed.keys())}")

    print()
    socket.close()
    context.term()


def main():
    print("\n=== STORY 3 TESTS ===\n")
    print("Sending a series of malformed/invalid requests. The service")
    print("must respond with a JSON error every time, never crash, and")
    print("still answer a valid request at the end.\n")

    # A. Not valid JSON at all.
    call(
        "TEST A: payload is not JSON",
        "this is not json at all",
        "error",
    )

    # B. Valid JSON, but not an object.
    call(
        "TEST B: JSON is an array, not an object",
        json.dumps([1, 2, 3]),
        "error",
    )

    # C. Valid JSON, but missing every field.
    call(
        "TEST C: empty object",
        json.dumps({}),
        "error",
    )

    # D. Unsupported action.
    call(
        "TEST D: unsupported action",
        json.dumps({
            "action": "make_coffee",
            "latitude": 45.3236,
            "longitude": -121.7300,
            "date": "2026-06-21",
        }),
        "error",
    )

    # E. Missing latitude.
    call(
        "TEST E: missing latitude",
        json.dumps({
            "action": "get_day",
            "longitude": -121.73,
            "date": "2026-06-21",
        }),
        "error",
    )

    # F. Latitude is a string instead of a number.
    call(
        "TEST F: latitude is a string",
        json.dumps({
            "action": "get_day",
            "latitude": "forty-five",
            "longitude": -121.73,
            "date": "2026-06-21",
        }),
        "error",
    )

    # G. Latitude is a boolean instead of a number.
    call(
        "TEST G: latitude is a boolean",
        json.dumps({
            "action": "get_day",
            "latitude": True,
            "longitude": -121.73,
            "date": "2026-06-21",
        }),
        "error",
    )

    # H. Malformed date string.
    call(
        "TEST H: malformed date string",
        json.dumps({
            "action": "get_day",
            "latitude": 45.3236,
            "longitude": -121.73,
            "date": "June 21 2026",
        }),
        "error",
    )

    # I. get_range with missing num_days.
    call(
        "TEST I: get_range with missing num_days",
        json.dumps({
            "action": "get_range",
            "latitude": 45.3236,
            "longitude": -121.73,
            "date": "2026-06-12",
        }),
        "error",
    )

    # J. get_range with num_days as a string.
    call(
        "TEST J: get_range with num_days as a string",
        json.dumps({
            "action": "get_range",
            "latitude": 45.3236,
            "longitude": -121.73,
            "date": "2026-06-12",
            "num_days": "three",
        }),
        "error",
    )

    # K. get_range with num_days as a float.
    call(
        "TEST K: get_range with num_days as a float",
        json.dumps({
            "action": "get_range",
            "latitude": 45.3236,
            "longitude": -121.73,
            "date": "2026-06-12",
            "num_days": 3.5,
        }),
        "error",
    )

    # L. Coordinates that astral cannot resolve (lat too far from real).
    call(
        "TEST L: latitude well outside valid range (astral fails internally)",
        json.dumps({
            "action": "get_day",
            "latitude": 200,
            "longitude": -121.73,
            "date": "2026-06-21",
        }),
        "error",
    )

    # M. Sanity check: a perfectly valid request should still work after
    # the avalanche of bad input above.
    call(
        "TEST M: SANITY -- valid request after all the bad ones",
        json.dumps({
            "action": "get_day",
            "latitude": 45.3236,
            "longitude": -121.7300,
            "date": "2026-06-21",
        }),
        "ok",
    )

    print("=" * 62)
    print("Done. If every test printed 'OK', Story 3 is satisfied:")
    print("  * Every invalid input returned a JSON error response.")
    print("  * The service kept running and answered a valid request.")
    print("=" * 62)


if __name__ == "__main__":
    main()