"""Opt-in live startup-performance regression tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_LIVE_TESTS_ENABLED = os.environ.get("EXPEDITE_LIVE_TESTS") == "1"
_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.live
@pytest.mark.skipif(
    not _LIVE_TESTS_ENABLED,
    reason="set EXPEDITE_LIVE_TESTS=1 to run browser-level performance tests",
)
def test_cold_startup_stays_within_performance_budgets() -> None:
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    result = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "live_ui_harness.py"),
            "--startup-only",
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: cold startup stayed within performance budgets" in result.stdout
    assert '"server_ready_seconds"' in result.stdout
    assert '"handshake_seconds"' in result.stdout
    assert '"interaction_seconds"' in result.stdout
