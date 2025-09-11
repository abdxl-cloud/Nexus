import importlib.util
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_run_manager_retains_completed_events():
    # stub minimal backend.db.models for utils import
    sys.modules["backend.db.models"] = types.SimpleNamespace(
        User=object,
        Thread=object,
        Message=object,
        Run=object,
    )

    spec = importlib.util.spec_from_file_location(
        "backend.api.utils", Path("backend/api/utils.py")
    )
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)

    manager = utils.RunManager(retention_seconds=60)
    run_id = "run1"
    manager.create_run_data(run_id, "thread", "msg")
    manager.add_event(run_id, "token", "hello")
    manager.update_status(run_id, "completed")

    data = manager.get_run_data(run_id)
    assert data["status"] == "completed"
    events = manager.get_events_since(run_id, 0)
    assert events and events[0]["data"] == "hello"


def test_logs_endpoint_returns_events():
    # stub configuration and dependent modules before importing routes
    def dummy_get_db():
        yield None

    sys.modules["backend.config"] = types.SimpleNamespace(
        get_settings=lambda: types.SimpleNamespace()
    )
    sys.modules["backend.db.models"] = types.SimpleNamespace(
        User=object,
        Thread=object,
        Message=object,
        Run=object,
        get_db=dummy_get_db,
        SessionLocal=None,
    )

    spec_utils = importlib.util.spec_from_file_location(
        "backend.api.utils", Path("backend/api/utils.py")
    )
    utils = importlib.util.module_from_spec(spec_utils)
    spec_utils.loader.exec_module(utils)

    # stub out DB lookup
    utils.get_run_by_id = lambda db, rid: types.SimpleNamespace(id=rid)
    sys.modules["backend.api.utils"] = utils

    sys.modules["backend.agent"] = types.SimpleNamespace(AgentLoop=object)

    spec_routes = importlib.util.spec_from_file_location(
        "backend.api.routes", Path("backend/api/routes.py")
    )
    routes = importlib.util.module_from_spec(spec_routes)
    spec_routes.loader.exec_module(routes)

    app = FastAPI()
    app.include_router(routes.router)

    run_id = "abc"
    rm = routes.run_manager
    rm.create_run_data(run_id, "thread", "hi")
    rm.add_event(run_id, "token", "hello")
    rm.update_status(run_id, "completed")

    client = TestClient(app)
    resp = client.get(f"/runs/{run_id}/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["events"][0]["data"] == "hello"