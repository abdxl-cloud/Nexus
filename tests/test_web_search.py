import os
import json
import time
import pytest
import requests
from requests.exceptions import ConnectionError

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
BASE_URL = f"{API_BASE_URL}/api"


def _create_thread():
    response = requests.post(f"{BASE_URL}/threads", json={})
    response.raise_for_status()
    return response.json()["thread_id"]


def _stream_event_payloads(run_id: str, timeout: float = 10.0):
    with requests.get(
        f"{BASE_URL}/runs/{run_id}/events",
        stream=True,
        headers={"Accept": "text/event-stream"},
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        events = []
        current_event = None
        for line in resp.iter_lines(decode_unicode=True):
            if line.startswith("event: "):
                current_event = line.split(": ", 1)[1]
            elif line.startswith("data: "):
                data_json = line.split(": ", 1)[1]
                events.append(json.loads(data_json))
                if current_event == "done":
                    break
        return events


@pytest.mark.integration
def test_web_search_event_stream():
    """Ensure web_search tool results stream as plain dicts"""
    try:
        thread_id = _create_thread()
    except ConnectionError:
        pytest.skip("API service is not running")

    message = {"role": "user", "content": "Search for Python web frameworks"}
    response = requests.post(f"{BASE_URL}/threads/{thread_id}/messages", json=message)
    assert response.status_code == 200, response.text
    run_id = response.json()["run_id"]

    # allow run to start
    time.sleep(1)
    try:
        events = _stream_event_payloads(run_id)
    except ConnectionError:
        pytest.skip("API service is not running")

    tool_results = [
        e for e in events
        if e.get("type") == "tool"
        and isinstance(e.get("data"), dict)
        and e["data"].get("ok") is not None
    ]
    assert any(res["data"].get("name") == "web_search" for res in tool_results)