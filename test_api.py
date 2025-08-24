#!/usr/bin/env python3
"""
Test script for the new API endpoints
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api"

def test_create_thread() -> str:
    """Test creating a new thread"""
    print("\n=== Testing POST /threads ===")
    
    response = requests.post(f"{BASE_URL}/threads", json={})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        thread_id = response.json()["thread_id"]
        print(f"✓ Thread created successfully: {thread_id}")
        return thread_id
    else:
        print("✗ Failed to create thread")
        return None

def test_create_message(thread_id: str) -> str:
    """Test creating a message and starting a run"""
    print("\n=== Testing POST /threads/{thread_id}/messages ===")
    
    message_data = {
        "role": "user",
        "content": "Hello! Can you help me with a simple task?"
    }
    
    response = requests.post(
        f"{BASE_URL}/threads/{thread_id}/messages",
        json=message_data
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        run_id = response.json()["run_id"]
        print(f"✓ Message created and run started: {run_id}")
        return run_id
    else:
        print("✗ Failed to create message")
        return None

def test_stream_events(run_id: str):
    """Test streaming run events via SSE"""
    print("\n=== Testing GET /runs/{run_id}/events ===")
    
    try:
        response = requests.get(
            f"{BASE_URL}/runs/{run_id}/events",
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ SSE stream started, receiving events:")
            
            event_count = 0
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"  {line}")
                    event_count += 1
                    
                    # Stop after receiving some events or if we see 'done'
                    if event_count > 20 or 'event: done' in line:
                        print("  ... stopping stream")
                        break
            
            print(f"✓ Received {event_count} SSE events")
        else:
            print("✗ Failed to start SSE stream")
            
    except Exception as e:
        print(f"✗ Error during SSE streaming: {e}")

def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing GET /health ===")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✓ Health check passed")
    else:
        print("✗ Health check failed")

def main():
    """Run all tests"""
    print("Starting API endpoint tests...")
    print(f"Base URL: {BASE_URL}")
    
    # Test health check first
    test_health_check()
    
    # Test thread creation
    thread_id = test_create_thread()
    if not thread_id:
        print("\n✗ Cannot continue without thread_id")
        return
    
    # Test message creation
    run_id = test_create_message(thread_id)
    if not run_id:
        print("\n✗ Cannot continue without run_id")
        return
    
    # Wait a moment for the run to start
    print("\nWaiting 2 seconds for run to start...")
    time.sleep(2)
    
    # Test SSE streaming
    test_stream_events(run_id)
    
    print("\n=== Test Summary ===")
    print(f"Thread ID: {thread_id}")
    print(f"Run ID: {run_id}")
    print("All tests completed!")

if __name__ == "__main__":
    main()