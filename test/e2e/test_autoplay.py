import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

import pytest
from playwright.sync_api import Page


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "service"


@pytest.fixture(scope="session")
def model_server():
    env = os.environ.copy()
    env.setdefault("RF_ALLOWED_ORIGINS", "http://127.0.0.1:5500")
    env.setdefault("PORT", "5050")
    proc = subprocess.Popen(
        [sys.executable, str(SERVICE_DIR / "model_server.py")],
        cwd=str(PROJECT_ROOT),
        env=env,
    )

    try:
        for _ in range(40):
            if proc.poll() is not None:
                raise RuntimeError("model server exited before responding")
            try:
                with socket.create_connection(("127.0.0.1", 5050), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("model server did not accept connections in time")

        yield "http://127.0.0.1:5050"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture(scope="session")
def static_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "5500"],
        cwd=str(PROJECT_ROOT),
    )

    try:
        for _ in range(40):
            if proc.poll() is not None:
                raise RuntimeError("static server exited before responding")
            try:
                with socket.create_connection(("127.0.0.1", 5500), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("static server did not accept connections in time")

        yield "http://127.0.0.1:5500"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def test_servers_boot(model_server, static_server):
    assert model_server and static_server


def _wait_for_idle(page: Page, timeout: float = 7.5) -> dict:
    deadline = time.time() + timeout
    snapshot = None
    while time.time() < deadline:
        snapshot = page.evaluate("window.__snapshotBoard && window.__snapshotBoard()")
        if snapshot and snapshot.get("ready") and not snapshot.get("busy"):
            return snapshot
        time.sleep(0.05)
    raise TimeoutError(f"Board did not settle within {timeout} seconds: {snapshot}")


def _warm_up_model_server(model_server_url: str) -> None:
    warmup_payload = json.dumps(
        {
            "grid": [[2, 0, 0, 2], [0, 4, 0, 4], [0, 0, 8, 0], [16, 0, 0, 0]],
            "score": 0,
        }
    ).encode("utf-8")

    warmup_request = urllib_request.Request(
        url=f"{model_server_url}/predict",
        data=warmup_payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        urllib_request.urlopen(warmup_request, timeout=30)
    except urllib_error.URLError as exc:  # pragma: no cover - diagnostic aid
        raise AssertionError(f"Warm-up predict request failed: {exc}") from exc


def _configure_test_context(context, model_server_url: str) -> None:
    context.add_init_script("window.__ENABLE_TEST_HOOKS__ = true;")
    context.add_init_script(f"window.AUTOPLAY_SERVER_URL = '{model_server_url}/predict';")


def _attach_page_listeners(page: Page):
    console_messages = []
    failed_requests = []

    page.on(
        "console",
        lambda message: console_messages.append(f"{message.type}: {message.text}"),
    )

    def _record_failure(request):
        failure = request.failure()
        error_text = failure.get("errorText") if failure else "unknown"
        failed_requests.append(f"{request.method} {request.url} -> {error_text}")

    page.on("requestfailed", _record_failure)
    return console_messages, failed_requests


def _predict_event_count(page: Page) -> int:
    return page.evaluate(
        "() => (window.__predictEvents && window.__predictEvents.length) || 0"
    )


def _get_predict_event(page: Page, idx: int):
    return page.evaluate(
        "(index) => (window.__predictEvents && window.__predictEvents[index]) || null",
        idx,
    )


def _await_predict_payload(
    page: Page,
    event_index: int,
    console_messages,
    observed_events,
    failed_requests,
):
    deadline = time.time() + 30.0
    event_count = _predict_event_count(page)

    while event_count <= event_index and time.time() < deadline:
        time.sleep(0.05)
        event_count = _predict_event_count(page)

    if event_count <= event_index:
        debug = page.evaluate(
            "() => ({"
            " running: window.autoplay && window.autoplay.running,"
            " timerActive: !!(window.autoplay && window.autoplay.timer),"
            " grid: window.__snapshotBoard && window.__snapshotBoard().grid,"
            " nextIndex: window.__predictEvents ? window.__predictEvents.length : undefined,"
            " url: window.AUTOPLAY_SERVER_URL"
            " })"
        )
        pytest.fail(
            "Timed out waiting for /predict response\n"
            f"Console: {console_messages}\n"
            f"Predict events captured: {event_count}\n"
            f"Events observed: {observed_events}\n"
            f"Requests failed: {failed_requests}\n"
            f"Autoplay state: {debug}"
        )

    event = _get_predict_event(page, event_index)
    assert event is not None, "Model server returned no payload"
    assert isinstance(event, dict), f"Predict event not dict: {event!r}"

    payload = event.get("payload")
    observed_events.append(
        {
            "status": event.get("status"),
            "has_payload": isinstance(payload, dict),
        }
    )

    assert isinstance(payload, dict), f"Predict response not JSON object: {payload!r}"
    assert "move" in payload and "valid_moves" in payload, (
        "Predict response missing keys",
        payload,
    )

    return payload

# Test game is not over if more moves can be taken and invalid moves are not accepted
def test_autoplay_moves_remain_valid(model_server, static_server, context):
    _warm_up_model_server(model_server)
    _configure_test_context(context, model_server)
    page = context.new_page()

    console_messages, failed_requests = _attach_page_listeners(page)
    observed_events = []

    page.goto(f"{static_server}/index.html", wait_until="load")
    page.wait_for_function("() => !!window.__snapshotBoard && window.__snapshotBoard().ready")
    page.wait_for_function("() => !!window.autoplay && typeof window.autoplay.start === 'function'")

    page.click(".restart-button")
    page.evaluate("window.autoplay.start()")
    page.evaluate("window.autoplay.step()")

    max_turns = 240
    event_index = 0
    previous_snapshot = None

    for _ in range(max_turns):
        # call model server for next move suggestion
        payload = _await_predict_payload(
            page,
            event_index,
            console_messages,
            observed_events,
            failed_requests,
        )
        event_index += 1

        snapshot = _wait_for_idle(page)

        if payload["move"] not in payload["valid_moves"]:
            if previous_snapshot and snapshot.get("grid") != previous_snapshot.get("grid"):
                pytest.fail(
                    "Invalid move altered board state\n"
                    f"Previous grid: {previous_snapshot['grid']}\n"
                    f"Current grid: {snapshot['grid']}\n"
                    f"Payload: {payload}\n"
                    f"Console: {console_messages}"
                )
            previous_snapshot = snapshot
            continue

        moves_available = page.evaluate("window.gameManager.movesAvailable()")
        if moves_available and snapshot.get("gameOver"):
            pytest.fail(
                "Game reported moves available but overlay indicates game over"
                f"\nGrid: {snapshot['grid']}"
            )

        if snapshot.get("gameOver"):
            previous_snapshot = snapshot
            break

        previous_snapshot = snapshot
    else:
        pytest.fail(f"Game did not reach a terminal state within {max_turns} moves")

    assert snapshot["gameOver"], "Expected game over overlay"
    assert all(cell != 0 for row in snapshot["grid"] for cell in row), "Board not full at game over"
    final_moves_available = page.evaluate("window.gameManager.movesAvailable()")
    assert final_moves_available is False, "Game reported moves available at game over"
