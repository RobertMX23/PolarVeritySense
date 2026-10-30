from sport_assistant_agent import programmatic_agents


def test_cloud_demo_fallback_uses_synthetic_non_personal_evidence(monkeypatch):
    def missing_fit():
        raise FileNotFoundError("no FIT volume mounted")

    monkeypatch.setattr(programmatic_agents, "_load_demo_sessions", missing_fit)

    ingestion = programmatic_agents.prepare_ingestion({}, "local_fit")
    comparison = programmatic_agents.prepare_comparison(ingestion, "local_fit")

    assert ingestion["demo_mode"] == {
        "enabled": True,
        "network_called": False,
        "source": "synthetic_cloud_demo",
        "contains_personal_telemetry": False,
    }
    assert ingestion["raw_polar_telemetry"]["source"] == "synthetic_cloud_demo"
    assert ingestion["raw_polar_telemetry"]["exercise_id"] == "synthetic-candidate-treadmill"
    assert comparison["session_comparison"]["reference_session_id"] == "synthetic-reference-hiit"
