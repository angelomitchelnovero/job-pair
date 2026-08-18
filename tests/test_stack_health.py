"""Stack health smoke tests (run only when both backend + frontend are reachable)."""
import os

import pytest
import requests

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND = os.getenv("FRONTEND_URL", "http://localhost:3000")


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION", "0") != "1",
    reason="Set RUN_INTEGRATION=1 to run live stack tests",
)
def test_backend_health():
    res = requests.get(f"{BACKEND}/health", timeout=5)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION", "0") != "1",
    reason="Set RUN_INTEGRATION=1 to run live stack tests",
)
def test_frontend_home():
    res = requests.get(FRONTEND, timeout=5)
    assert res.status_code == 200
    assert "JobPair.aloe" in res.text
