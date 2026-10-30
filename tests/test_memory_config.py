import pytest

from sport_assistant_agent.memory import create_memory_service


def test_memory_defaults_to_local(monkeypatch):
    monkeypatch.delenv("ADK_MEMORY_MODE", raising=False)
    service = create_memory_service()
    assert service.__class__.__name__ == "InMemoryMemoryService"


def test_vertex_mode_requires_configuration(monkeypatch):
    monkeypatch.setenv("ADK_MEMORY_MODE", "vertex")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(KeyError):
        create_memory_service()
