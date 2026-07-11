from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
BUILDER = REPO_ROOT / "scripts/ci/build-proxy-package.js"
SOURCE_ROOT = REPO_ROOT / "tools/intent-tester"
SOURCE_SERVER = SOURCE_ROOT / "browser-automation/midscene_server.js"
SOURCE_NODE_MODULES = SOURCE_ROOT / "node_modules"
EXPANDED_PACKAGE = REPO_ROOT / "dist/intent-test-proxy"
DIST_ZIP = REPO_ROOT / "dist/intent-test-proxy.zip"
FRONTEND_ZIP = SOURCE_ROOT / "frontend/static/intent-test-proxy.zip"
ARCHIVE_ROOT = "intent-test-proxy"
VALID_RUNTIME_ENV = {
    "INTENT_PROXY_TOPOLOGY": "local-host",
    "INTENT_PROXY_TOKEN": "package-proxy-token-with-at-least-32-bytes",
    "INTENT_PUBLIC_ORIGIN": "http://127.0.0.1:5001",
    "OPENAI_API_KEY": "package-smoke-test-key",
    "OPENAI_BASE_URL": "http://127.0.0.1:9999/v1",
    "MIDSCENE_MODEL_NAME": "offline-package-model",
    "MAIN_APP_URL": "http://127.0.0.1:5001/intent-tester/api",
}


def _run_builder() -> None:
    subprocess.run(
        ["node", str(BUILDER)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _archive_files(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {
            info.filename: archive.read(info)
            for info in archive.infolist()
            if not info.is_dir()
        }


def _expanded_files() -> dict[str, bytes]:
    return {
        f"{ARCHIVE_ROOT}/{path.relative_to(EXPANDED_PACKAGE).as_posix()}": path.read_bytes()
        for path in EXPANDED_PACKAGE.rglob("*")
        if path.is_file()
    }


def _extract_frontend_package(tmp_path: Path) -> Path:
    with zipfile.ZipFile(FRONTEND_ZIP) as archive:
        archive.extractall(tmp_path)
    package_root = tmp_path / ARCHIVE_ROOT
    os.symlink(SOURCE_NODE_MODULES, package_root / "node_modules", target_is_directory=True)
    return package_root


def _free_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def test_builder_produces_complete_synchronized_package() -> None:
    _run_builder()

    archive_files = _archive_files(DIST_ZIP)
    with zipfile.ZipFile(DIST_ZIP) as archive:
        assert {
            info.date_time for info in archive.infolist() if not info.is_dir()
        } == {(2000, 1, 1, 0, 0, 0)}
    required = {
        f"{ARCHIVE_ROOT}/midscene_server.js",
        f"{ARCHIVE_ROOT}/package.json",
        f"{ARCHIVE_ROOT}/package-lock.json",
        f"{ARCHIVE_ROOT}/start.sh",
        f"{ARCHIVE_ROOT}/start.bat",
        f"{ARCHIVE_ROOT}/.env.example",
    }
    assert required <= archive_files.keys()
    assert archive_files[f"{ARCHIVE_ROOT}/midscene_server.js"] == SOURCE_SERVER.read_bytes()
    assert not any(
        part in {"node_modules", "__pycache__", ".pytest_cache", ".DS_Store"}
        or name.endswith((".pyc", ".pyo"))
        for name in archive_files
        for part in Path(name).parts
    )

    package = json.loads(archive_files[f"{ARCHIVE_ROOT}/package.json"])
    lock = json.loads(archive_files[f"{ARCHIVE_ROOT}/package-lock.json"])
    assert package["main"] == "midscene_server.js"
    assert package["scripts"]["start"] == "node midscene_server.js"
    assert lock["packages"][""]["dependencies"] == package["dependencies"]
    assert lock["packages"][""]["devDependencies"] == package["devDependencies"]
    env_example = archive_files[f"{ARCHIVE_ROOT}/.env.example"].decode()
    for key in VALID_RUNTIME_ENV:
        assert f"{key}=" in env_example
    assert "your-api-key-here" in env_example
    assert VALID_RUNTIME_ENV["INTENT_PROXY_TOKEN"] not in env_example
    assert archive_files[f"{ARCHIVE_ROOT}/.env.example"] == (
        SOURCE_ROOT / "proxy_templates/.env.example"
    ).read_bytes()
    for script_name in ("start.sh", "start.bat"):
        packaged_script = archive_files[f"{ARCHIVE_ROOT}/{script_name}"]
        source_script = (SOURCE_ROOT / "proxy_templates" / script_name).read_bytes()
        assert packaged_script == source_script
        script_text = packaged_script.decode()
        for key in VALID_RUNTIME_ENV:
            assert key in script_text
        install_position = min(
            position
            for marker in ("npm ci", "npm install")
            if (position := script_text.find(marker)) >= 0
        )
        assert script_text.find("INTENT_PROXY_TOKEN") < install_position

    assert DIST_ZIP.read_bytes() == FRONTEND_ZIP.read_bytes()
    assert archive_files == _archive_files(FRONTEND_ZIP)
    assert archive_files == _expanded_files()


def test_builder_is_byte_deterministic() -> None:
    _run_builder()
    first_hash = _sha256(DIST_ZIP)

    # The old builder inherited copy time in each ZIP entry. Crossing the ZIP
    # timestamp granularity proves a repeated build cannot drift by wall clock.
    time.sleep(2.1)
    _run_builder()

    assert _sha256(DIST_ZIP) == first_hash
    assert _sha256(FRONTEND_ZIP) == first_hash


@pytest.mark.parametrize("topology", ["local-host", "managed"])
def test_frontend_package_starts_real_server_and_serves_health(
    tmp_path: Path, topology: str
) -> None:
    assert SOURCE_NODE_MODULES.is_dir(), (
        "This smoke test intentionally reuses repository-installed dependencies; "
        "it does not prove a fresh npm download."
    )
    _run_builder()
    package_root = _extract_frontend_package(tmp_path)
    port = _free_port()
    env = {
        **os.environ,
        **VALID_RUNTIME_ENV,
        "INTENT_PROXY_TOPOLOGY": topology,
        "PORT": str(port),
    }
    process = subprocess.Popen(
        ["node", "midscene_server.js"],
        cwd=package_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 20
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise AssertionError(f"Packaged server exited before health check:\n{output}")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    payload = json.load(response)
                assert response.status == 200
                assert payload["success"] is True
                break
            except (OSError, URLError) as error:  # bounded polling; preserved on timeout
                last_error = error
                time.sleep(0.1)
        else:
            raise AssertionError(f"Packaged server did not become healthy: {last_error}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        output = process.stdout.read() if process.stdout else ""
        assert VALID_RUNTIME_ENV["INTENT_PROXY_TOKEN"] not in output


@pytest.mark.parametrize("missing_key", tuple(VALID_RUNTIME_ENV))
def test_frontend_package_fails_explicitly_without_required_security_config(
    tmp_path: Path, missing_key: str
) -> None:
    _run_builder()
    package_root = _extract_frontend_package(tmp_path)
    env = {
        **os.environ,
        **VALID_RUNTIME_ENV,
        missing_key: "",
        "PORT": str(_free_port()),
    }

    result = subprocess.run(
        ["node", "midscene_server.js"],
        cwd=package_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert missing_key in output
    assert VALID_RUNTIME_ENV["INTENT_PROXY_TOKEN"] not in output
