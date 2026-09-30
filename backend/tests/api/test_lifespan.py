from fastapi.testclient import TestClient

import app.main as main_module


def test_fastapi_lifespan_initializes_and_releases_rag_manager(monkeypatch) -> None:
    events: list[str] = []

    class RecordingManager:
        def initialize(self):
            events.append("initialize")
            return object()

        def close(self) -> None:
            events.append("close")

    manager = RecordingManager()
    monkeypatch.setattr(main_module, "get_rag_index_manager", lambda: manager)

    with TestClient(main_module.app) as client:
        assert client.app.state.rag_index_manager is manager
        assert events == ["initialize"]

    assert events == ["initialize", "close"]
