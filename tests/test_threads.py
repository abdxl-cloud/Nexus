import os
import pytest
import requests
from requests.exceptions import ConnectionError

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
BASE_URL = f"{API_BASE_URL}/api"

@pytest.mark.integration
def test_create_thread():
    """Ensure a thread can be created"""
    try:
        response = requests.post(f"{BASE_URL}/threads", json={})
    except ConnectionError:
        pytest.skip("API service is not running")

    assert response.status_code == 200, response.text
    data = response.json()
    assert "thread_id" in data
    assert isinstance(data["thread_id"], str)
