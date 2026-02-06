import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright


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


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance) -> Browser:
    browser = playwright_instance.chromium.launch(headless=False, slow_mo=100)
    yield browser
    browser.close()


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


def test_autoplay_moves_remain_valid(model_server, static_server, browser: Browser):
    context = browser.new_context()
    context.add_init_script("window.__ENABLE_TEST_HOOKS__ = true;")
    context.add_init_script(f"window.AUTOPLAY_SERVER_URL = '{model_server}/predict';")
    page = context.new_page()
    try:
        page.goto(f"{static_server}/index.html", wait_until="load")
        page.wait_for_function("() => !!window.__snapshotBoard && window.__snapshotBoard().ready")
        page.wait_for_function("() => !!window.autoplay && typeof window.autoplay.start === 'function'")
        page.evaluate("window.autoplay.start()")

        max_turns = 80

        for _ in range(max_turns):
            response = page.wait_for_response(
                lambda res: res.request.method == "POST" and res.url.endswith("/predict"),
                timeout=10000,
            )
            payload = response.json()

            assert payload["move"] in payload["valid_moves"], (
                "Model predicted invalid move",
                payload,
            )

            snapshot = _wait_for_idle(page)

            if snapshot.get("gameOver"):
                break
        else:
            pytest.fail("Game did not reach a terminal state within 80 moves")

        assert snapshot["gameOver"], "Expected game over overlay"
        assert all(cell != 0 for row in snapshot["grid"] for cell in row), "Board not full at game over"
        moves_available = page.evaluate("window.gameManager.movesAvailable()")
        assert moves_available is False, "Game reported moves available at game over"
    finally:
        context.close()
