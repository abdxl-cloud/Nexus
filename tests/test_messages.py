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


def _stream_events(run_id: str, timeout: float = 5.0):
    with requests.get(
        f"{BASE_URL}/runs/{run_id}/events",
        stream=True,
        headers={"Accept": "text/event-stream"},
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        lines = []
        for line in resp.iter_lines(decode_unicode=True):
            if line:
                lines.append(line)
                if line.startswith("event: done"):
                    break
        return "\n".join(lines)


@pytest.mark.integration
def test_post_message_and_search():
    """Post a message and verify search results are produced"""
    try:
        thread_id = _create_thread()
    except ConnectionError:
        pytest.skip("API service is not running")

    message = {"role": "user", "content": "Search for Python web frameworks"}
    response = requests.post(f"{BASE_URL}/threads/{thread_id}/messages", json=message)
    assert response.status_code == 200, response.text
    run_id = response.json()["run_id"]

    # give the run a moment to start
    time.sleep(1)
    try:
        events_text = _stream_events(run_id)
    except ConnectionError:
        pytest.skip("API service is not running")

    assert "tool" in events_text.lower() or "search" in events_text.lower()