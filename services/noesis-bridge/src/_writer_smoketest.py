from pathlib import Path
from writer import EventWriter

def main() -> None:
    out_dir = Path("/opt/tinymux/out")

    w = EventWriter(out_dir=out_dir)

    # Minimal fake events (no semantics required for TASK 6)
    e1 = {"ts_utc": "2026-01-15T20:31:12.123Z", "run_id": "test-run", "seq": 1, "type": "SAY"}
    e2 = {"ts_utc": "2026-01-15T20:31:13.456Z", "run_id": "test-run", "seq": 2, "type": "SAY", "note": "hello"}
    e3 = {"ts_utc": "2026-01-15T20:31:14.789Z", "run_id": "test-run", "seq": 3, "type": "SAY", "note": "goodbye"}

    p1 = w.write_event(e1)
    p2 = w.write_event(e2)
    p3 = w.write_event(e3)

    w.close()

    print("OK: wrote events to:")
    print(" -", p1)
    print(" -", p2)
    print(" -", p3)

if __name__ == "__main__":
    main()
