#!/usr/bin/env python3
"""Run repeatable browser-level checks against the NiceGUI preview server."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote

from websockets.sync.client import ClientConnection, connect

ROOT = Path(__file__).resolve().parents[1]


class LiveUiError(RuntimeError):
    """Raised when a live UI assertion or process startup fails."""


@dataclass(frozen=True)
class StartupBudgets:
    """Maximum durations for local cold-start phases."""

    server_ready_seconds: float = 5.0
    chrome_ready_seconds: float = 5.0
    first_control_seconds: float = 2.0
    handshake_seconds: float = 3.0
    interaction_seconds: float = 1.0


@dataclass(frozen=True)
class StartupMetrics:
    """Measured cold-start durations for the preview application."""

    server_ready_seconds: float
    chrome_ready_seconds: float
    first_control_seconds: float
    handshake_seconds: float
    interaction_seconds: float


class CdpPage:
    """Small synchronous Chrome DevTools Protocol client for one page."""

    def __init__(self, websocket_url: str) -> None:
        self._connection: ClientConnection = connect(
            websocket_url,
            open_timeout=10,
            max_size=None,
        )
        self._next_id = 0
        self.console_messages: list[str] = []
        self.command("Runtime.enable")
        self.command("Log.enable")
        self.command("Network.enable")
        self.command("Network.setCacheDisabled", {"cacheDisabled": True})

    def close(self) -> None:
        self._connection.close()

    def command(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        command_id = self._next_id
        self._connection.send(
            json.dumps({"id": command_id, "method": method, "params": params or {}})
        )
        while True:
            message = json.loads(self._connection.recv())
            if "method" in message:
                self._record_event(message)
                continue
            if message.get("id") != command_id:
                continue
            if "error" in message:
                raise LiveUiError(f"CDP {method} failed: {message['error']}")
            return message.get("result", {})

    def _record_event(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params", {})
        if method == "Runtime.consoleAPICalled":
            values = [
                str(item.get("value", item.get("description", "")))
                for item in params["args"]
            ]
            self.console_messages.append(f"{params.get('type', 'console')}: {' '.join(values)}")
        elif method == "Log.entryAdded":
            entry = params["entry"]
            self.console_messages.append(
                f"{entry.get('level', 'log')}: {entry.get('text', '')}"
            )

    def evaluate(self, expression: str) -> object:
        result = self.command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            raise LiveUiError(details.get("text", "JavaScript evaluation failed"))
        return result.get("result", {}).get("value")

    def navigate(self, url: str) -> None:
        self.command("Page.enable")
        self.command("Page.navigate", {"url": url})
        self.wait_for("document.readyState === 'complete'", description=f"load {url}")

    def wait_for(
        self,
        expression: str,
        *,
        description: str,
        timeout: float = 10,
    ) -> object:
        deadline = time.monotonic() + timeout
        last_value: object = None
        while time.monotonic() < deadline:
            try:
                last_value = self.evaluate(expression)
            except (LiveUiError, TimeoutError):
                last_value = None
            if last_value:
                return last_value
            time.sleep(0.05)
        raise LiveUiError(f"Timed out waiting for {description}; last value: {last_value!r}")

    def click(self, selector: str, *, times: int = 1) -> None:
        selector_json = json.dumps(selector)
        clicked = self.evaluate(
            "(() => {"
            f" const element = document.querySelector({selector_json});"
            " if (!element) return false;"
            f" for (let index = 0; index < {times}; index += 1) element.click();"
            " return true;"
            "})()"
        )
        if not clicked:
            raise LiveUiError(f"Could not click missing element {selector}")

    def wait_for_selector(self, selector: str, *, timeout: float = 10) -> None:
        selector_json = json.dumps(selector)
        self.wait_for(
            f"Boolean(document.querySelector({selector_json}))",
            description=selector,
            timeout=timeout,
        )

    def is_disabled(self, selector: str) -> bool:
        selector_json = json.dumps(selector)
        return bool(
            self.evaluate(
                "(() => {"
                f" const element = document.querySelector({selector_json});"
                " return Boolean(element && (element.disabled"
                " || element.getAttribute('aria-disabled') === 'true'"
                " || element.classList.contains('disabled')));"
                "})()"
            )
        )

    def wait_for_disabled(self, selector: str, disabled: bool, *, timeout: float = 10) -> None:
        selector_json = json.dumps(selector)
        expected = "true" if disabled else "false"
        self.wait_for(
            "(() => {"
            f" const element = document.querySelector({selector_json});"
            " if (!element) return false;"
            " const disabled = Boolean(element.disabled"
            " || element.getAttribute('aria-disabled') === 'true'"
            " || element.classList.contains('disabled'));"
            f" return disabled === {expected};"
            "})()",
            description=f"{selector} to become {'disabled' if disabled else 'enabled'}",
            timeout=timeout,
        )

    def save_artifacts(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        html_value = self.evaluate("document.documentElement.outerHTML")
        html = html_value if isinstance(html_value, str) else ""
        (directory / "page.html").write_text(html, encoding="utf-8")
        (directory / "console.log").write_text(
            "\n".join(self.console_messages), encoding="utf-8"
        )
        screenshot = self.command("Page.captureScreenshot", {"format": "png"})["data"]
        (directory / "screenshot.png").write_bytes(base64.b64decode(screenshot))


class LiveUiHarness:
    """Own the disposable data, preview server, headless Chrome, and artifacts."""

    def __init__(self, *, keep_artifacts: bool = False, print_delay: float = 1.0) -> None:
        self.keep_artifacts = keep_artifacts
        self.print_delay = print_delay
        self.artifact_dir = Path(tempfile.mkdtemp(prefix="expedite-live-ui-"))
        self.data_dir = self.artifact_dir / "data"
        self.profile_dir = self.artifact_dir / "chrome-profile"
        self.server_log_path = self.artifact_dir / "preview.log"
        self.chrome_log_path = self.artifact_dir / "chrome.log"
        self.server: subprocess.Popen[bytes] | None = None
        self.chrome: subprocess.Popen[bytes] | None = None
        self.page: CdpPage | None = None
        self.port = _free_port()
        self.debug_port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.server_ready_seconds = 0.0
        self.chrome_ready_seconds = 0.0
        self._failed = False

    def __enter__(self) -> LiveUiHarness:
        try:
            self._start_server()
            self._start_chrome()
            self.page = CdpPage(self._page_websocket_url())
            return self
        except Exception:
            self._failed = True
            self.close()
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._failed = exc is not None
        if self._failed and self.page is not None:
            try:
                self.page.save_artifacts(self.artifact_dir)
            except Exception as artifact_error:  # pragma: no cover - failure diagnostics only
                print(f"Could not save browser artifacts: {artifact_error}", file=sys.stderr)
        self.close()

    def close(self) -> None:
        if self.page is not None:
            self.page.close()
            self.page = None
        _terminate_process_tree(self.chrome)
        _terminate_process_tree(self.server)
        self.chrome = None
        self.server = None
        if self._failed or self.keep_artifacts:
            print(f"Live UI artifacts: {self.artifact_dir}")
        else:
            shutil.rmtree(self.artifact_dir, ignore_errors=True)

    def _start_server(self) -> None:
        self.data_dir.mkdir(parents=True)
        log = self.server_log_path.open("wb")
        started = time.monotonic()
        self.server = _popen(
            [
                sys.executable,
                str(ROOT / "scripts" / "ui_preview.py"),
                "--port",
                str(self.port),
                "--data-dir",
                str(self.data_dir),
                "--fake-print-delay",
                str(self.print_delay),
            ],
            log,
        )
        _wait_for_port(self.port, process=self.server, timeout=15)
        self.server_ready_seconds = time.monotonic() - started

    def _start_chrome(self) -> None:
        chrome_path = _find_chrome()
        log = self.chrome_log_path.open("wb")
        started = time.monotonic()
        self.chrome = _popen(
            [
                chrome_path,
                "--headless=new",
                "--disable-gpu",
                "--disable-background-networking",
                "--no-first-run",
                "--no-default-browser-check",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={self.debug_port}",
                f"--user-data-dir={self.profile_dir}",
                "about:blank",
            ],
            log,
        )
        _wait_for_http(
            f"http://127.0.0.1:{self.debug_port}/json/version",
            process=self.chrome,
            timeout=15,
        )
        self.chrome_ready_seconds = time.monotonic() - started

    def _page_websocket_url(self) -> str:
        deadline = time.monotonic() + 10
        url = f"http://127.0.0.1:{self.debug_port}/json/list"
        while time.monotonic() < deadline:
            with urllib.request.urlopen(url, timeout=1) as response:
                targets = json.load(response)
            page = next((target for target in targets if target["type"] == "page"), None)
            if page is not None:
                return str(page["webSocketDebuggerUrl"])
            time.sleep(0.05)
        raise LiveUiError("Chrome did not expose a page target")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _popen(command: list[str], log: BinaryIO) -> subprocess.Popen[bytes]:
    if os.name == "nt":
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process


def _terminate_process_tree(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def _wait_for_port(port: int, *, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LiveUiError(
                f"Process exited with status {process.returncode} while waiting for port {port}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError as error:
            last_error = error
        time.sleep(0.05)
    raise LiveUiError(f"Timed out waiting for port {port}: {last_error}")


def _wait_for_http(url: str, *, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LiveUiError(
                f"Process exited with status {process.returncode} while waiting for {url}"
            )
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
        time.sleep(0.05)
    raise LiveUiError(f"Timed out waiting for {url}: {last_error}")


def _find_chrome() -> str:
    configured = os.environ.get("CHROME_PATH")
    candidates = [
        configured,
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise LiveUiError("Chrome not found; set CHROME_PATH to its executable")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise LiveUiError(message)


def measure_startup(
    harness: LiveUiHarness,
    budgets: StartupBudgets,
) -> StartupMetrics:
    """Measure a cold page render, handshake, and first server-backed interaction."""
    page = harness.page
    assert page is not None
    page.command("Page.enable")
    started = time.monotonic()
    page.command("Page.navigate", {"url": f"{harness.base_url}/?startup-performance=1"})

    first_control_seconds: float | None = None
    handshake_seconds: float | None = None
    deadline = started + max(budgets.first_control_seconds, budgets.handshake_seconds) + 5
    while time.monotonic() < deadline:
        try:
            state = page.evaluate(
                "({"
                " control: Boolean(document.querySelector('[data-testid=\"new-event\"]')) ,"
                " handshake: Boolean(window.did_handshake)"
                "})"
            )
        except (LiveUiError, TimeoutError):
            state = None
        now = time.monotonic()
        if isinstance(state, dict):
            if state.get("control") and first_control_seconds is None:
                first_control_seconds = now - started
            if state.get("handshake") and handshake_seconds is None:
                handshake_seconds = now - started
        if first_control_seconds is not None and handshake_seconds is not None:
            break
        time.sleep(0.01)

    if first_control_seconds is None:
        raise LiveUiError("The first actionable control did not render")
    if handshake_seconds is None:
        raise LiveUiError("The NiceGUI handshake did not complete")

    interaction_started = time.monotonic()
    page.click('[data-testid="new-event"]')
    page.wait_for(
        "(() => {"
        " const element = document.querySelector('[data-testid=\"new-event-dialog\"]');"
        " if (!element) return false;"
        " const bounds = element.getBoundingClientRect();"
        " const style = getComputedStyle(element);"
        " return bounds.width > 0 && bounds.height > 0"
        " && style.display !== 'none' && style.visibility !== 'hidden';"
        "})()",
        description="the New Event dialog to become visible",
        timeout=budgets.interaction_seconds + 2,
    )
    interaction_seconds = time.monotonic() - interaction_started

    metrics = StartupMetrics(
        server_ready_seconds=harness.server_ready_seconds,
        chrome_ready_seconds=harness.chrome_ready_seconds,
        first_control_seconds=first_control_seconds,
        handshake_seconds=handshake_seconds,
        interaction_seconds=interaction_seconds,
    )
    (harness.artifact_dir / "startup-metrics.json").write_text(
        json.dumps(asdict(metrics), indent=2) + "\n",
        encoding="utf-8",
    )

    for name, measured in asdict(metrics).items():
        budget = getattr(budgets, name)
        _assert(
            measured <= budget,
            f"Startup performance regression: {name} took {measured:.3f}s "
            f"(budget {budget:.3f}s)",
        )

    print("PASS: cold startup stayed within performance budgets")
    print(json.dumps({name: round(value, 3) for name, value in asdict(metrics).items()}))
    return metrics


def run_print_lock_checks(harness: LiveUiHarness) -> None:
    """Exercise submit and receipt-print locking in a real browser."""
    os.environ["EVENT_INTAKE_DATA_DIR"] = str(harness.data_dir)
    from expedite.storage.database import dispose_engine
    from expedite.storage.events import create_event
    from expedite.storage.sqlite_store import list_order_records

    dispose_engine()
    event = create_event("Live UI Print Lock", "2026-01-02")
    page = harness.page
    assert page is not None

    submit_selector = '[data-testid="submit-order"]'
    created_print_selector = '[data-testid="print-created-receipt"]'
    selected_print_selector = '[data-testid="print-selected-receipt"]'
    row_selector = '[data-testid="order-row-1"]'

    page.navigate(f"{harness.base_url}/events/{quote(event.folder_name())}?live-test=1")
    page.wait_for_selector(submit_selector)
    page.click(submit_selector, times=2)
    page.wait_for_disabled(submit_selector, True)
    page.wait_for_disabled(submit_selector, False, timeout=15)
    page.wait_for_selector(created_print_selector)

    deadline = time.monotonic() + 5
    records = []
    while time.monotonic() < deadline:
        records = list_order_records(event)
        if records:
            break
        time.sleep(0.05)
    _assert(len(records) == 1, f"Rapid submit created {len(records)} orders instead of one")
    print("PASS: rapid Submit clicks create one order")

    page.click(created_print_selector)
    page.wait_for_disabled(created_print_selector, True)
    page.wait_for_disabled(created_print_selector, False, timeout=15)
    print("PASS: created-receipt Print is disabled while printing")

    page.navigate(f"{harness.base_url}/events/{quote(event.folder_name())}/orders?live-test=2")
    page.wait_for_selector(row_selector)
    page.click(row_selector)
    page.wait_for_disabled(selected_print_selector, False)
    page.click(selected_print_selector)
    page.wait_for_disabled(selected_print_selector, True)
    page.click(row_selector)
    _assert(
        page.is_disabled(selected_print_selector),
        "Selecting an order re-enabled Print while a print was active",
    )
    page.wait_for_disabled(selected_print_selector, False, timeout=15)
    print("PASS: Orders Print remains disabled across row selection while printing")

    dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep temporary data, logs, and the Chrome profile after a successful run.",
    )
    parser.add_argument("--print-delay", type=float, default=1.0)
    parser.add_argument(
        "--startup-only",
        action="store_true",
        help="Run only the cold-start performance regression check.",
    )
    parser.add_argument(
        "--startup-budget-scale",
        type=float,
        default=1.0,
        help="Multiply all startup-performance budgets for slower test environments.",
    )
    args = parser.parse_args()
    if args.startup_budget_scale <= 0:
        parser.error("--startup-budget-scale must be positive")
    default_budgets = StartupBudgets()
    budgets = StartupBudgets(
        **{
            name: value * args.startup_budget_scale
            for name, value in asdict(default_budgets).items()
        }
    )

    try:
        with LiveUiHarness(
            keep_artifacts=args.keep_artifacts,
            print_delay=args.print_delay,
        ) as harness:
            measure_startup(harness, budgets)
            if not args.startup_only:
                run_print_lock_checks(harness)
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("All live UI checks passed.")


if __name__ == "__main__":
    main()
