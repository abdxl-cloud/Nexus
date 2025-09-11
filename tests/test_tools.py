import importlib.util
import types
import sys
from pathlib import Path


def test_get_default_tools_names():
    # Provide a lightweight stub for backend.config to avoid reading the real
    # settings (which requires many environment variables).
    class DummySettings:
        COEXISTAI_BASE_URL = ""
        COEXISTAI_API_KEY = ""
        RUNNER_BASE_URL = ""

    sys.modules["backend.config"] = types.SimpleNamespace(
        get_settings=lambda: DummySettings()
    )

    # Create a minimal "backend.agent" package so we can load the tools module
    backend_agent = types.ModuleType("backend.agent")
    backend_agent.__path__ = [str(Path("backend/agent"))]
    sys.modules["backend.agent"] = backend_agent

    spec = importlib.util.spec_from_file_location(
        "backend.agent.tools",
        Path("backend/agent/tools/__init__.py"),
        submodule_search_locations=[str(Path("backend/agent/tools"))],
    )
    tools_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools_module)

    tool_names = {tool.name for tool in tools_module.get_default_tools()}
    assert "web_search" in tool_names
    assert "browser" in tool_names
