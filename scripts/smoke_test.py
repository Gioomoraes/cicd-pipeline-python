"""Smoke test: poll /health then verify /version matches the expected version."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def get_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception:
        return 0, {}


def poll_health(base_url: str, retries: int, interval: int) -> bool:
    url = f"{base_url}/health"
    for attempt in range(1, retries + 1):
        status, body = get_json(url)
        if status == 200 and body.get("status") == "ok":
            print(f"[{attempt}/{retries}] /health OK")
            return True
        print(
            f"[{attempt}/{retries}] /health not ready "
            f"(status={status}, body={body}), waiting {interval}s..."
        )
        time.sleep(interval)
    return False


def check_version(base_url: str, expected: str) -> bool:
    url = f"{base_url}/version"
    status, body = get_json(url)
    actual = body.get("version")
    if status == 200 and actual == expected:
        print(f"/version OK: {body}")
        return True
    print(f"/version FAILED: status={status}, body={body}, expected version={expected!r}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for cicd-app.")
    parser.add_argument("--url", required=True, help="Base URL, e.g. http://localhost:8000")
    parser.add_argument(
        "--expected-version", required=True, help="Expected value of the 'version' field"
    )
    parser.add_argument(
        "--retries", type=int, default=10, help="Number of /health poll attempts (default: 10)"
    )
    parser.add_argument(
        "--interval", type=int, default=3, help="Seconds between retries (default: 3)"
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    print(
        f"Polling {base_url}/health (up to {args.retries} attempts, {args.interval}s interval)..."
    )
    if not poll_health(base_url, args.retries, args.interval):
        print("ERROR: service did not become healthy in time.")
        sys.exit(1)

    print(f"Checking {base_url}/version for expected version {args.expected_version!r}...")
    if not check_version(base_url, args.expected_version):
        sys.exit(1)

    print("Smoke test passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
