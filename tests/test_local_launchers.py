import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = (
    "start-aquantai.bat",
    "stop-aquantai.bat",
    "start-aquantai.sh",
    "stop-aquantai.sh",
)
DASHBOARD_URL = "http://127.0.0.1:8000/dashboard"
HEALTH_URL = "http://127.0.0.1:8000/health"
ENV_TEMPLATE = b"APP_ENV=development\nPOSTGRES_USER=aquantai\n"


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _copy_launcher_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "AQuantAI temporary copy"
    repo.mkdir()
    for name in LAUNCHERS:
        shutil.copy2(ROOT / name, repo / name)
    shutil.copy2(ROOT / "docker-compose.yml", repo / "docker-compose.yml")
    (repo / ".env.example").write_bytes(ENV_TEMPLATE)
    return repo


def _write_windows_shims(shim_dir: Path, *, include_docker: bool = True) -> None:
    shim_dir.mkdir()
    if include_docker:
        (shim_dir / "docker.bat").write_text(
            """@echo off
echo docker %*>>"%AQUANTAI_TEST_LOG%"
if /I "%AQUANTAI_DOCKER_MODE%"=="compose-fail" if /I "%1"=="compose" if /I "%2"=="version" exit /b 1
if /I "%AQUANTAI_DOCKER_MODE%"=="daemon-fail" if /I "%1"=="info" exit /b 1
if /I "%AQUANTAI_DOCKER_MODE%"=="config-fail" if /I "%1"=="compose" if /I "%2"=="config" exit /b 1
if /I "%AQUANTAI_DOCKER_MODE%"=="up-fail" if /I "%1"=="compose" if /I "%2"=="up" exit /b 1
exit /b 0
""",
            encoding="ascii",
        )
    (shim_dir / "powershell.bat").write_text(
        """@echo off
set "AQUANTAI_POWERSHELL_COMMAND=%~3"
if /I "%AQUANTAI_POWERSHELL_COMMAND:~0,13%"=="Start-Process" goto browser
echo powershell health http://127.0.0.1:8000/health>>"%AQUANTAI_TEST_LOG%"
if /I "%AQUANTAI_HEALTH_MODE%"=="ready" exit /b 0
exit /b 1

:browser
echo powershell Start-Process http://127.0.0.1:8000/dashboard>>"%AQUANTAI_TEST_LOG%"
if /I "%AQUANTAI_BROWSER_MODE%"=="fail" exit /b 1
exit /b 0
""",
        encoding="ascii",
    )
    (shim_dir / "timeout.bat").write_text(
        """@echo off
echo timeout %*>>"%AQUANTAI_TEST_LOG%"
exit /b 0
""",
        encoding="ascii",
    )


def _windows_env(shim_dir: Path, log_file: Path, **values: str) -> dict[str, str]:
    env = os.environ.copy()
    system_root = Path(env.get("SystemRoot") or env.get("SYSTEMROOT") or r"C:\Windows")
    env["PATH"] = os.pathsep.join((str(shim_dir), str(system_root / "System32")))
    env["AQUANTAI_TEST_LOG"] = str(log_file)
    env["AQUANTAI_DOCKER_MODE"] = "ok"
    env["AQUANTAI_HEALTH_MODE"] = "ready"
    env["AQUANTAI_BROWSER_MODE"] = "ok"
    env.update(values)
    return env


def _run_windows(repo: Path, env: dict[str, str], script: str, *args: str) -> subprocess.CompletedProcess[str]:
    comspec = env.get("ComSpec") or env.get("COMSPEC") or "cmd.exe"
    suffix = " " + " ".join(args) if args else ""
    command = f'"{comspec}" /d /s /c ""{repo / script}"{suffix}"'
    return subprocess.run(
        command,
        cwd=repo.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _write_posix_shims(shim_dir: Path, *, include_docker: bool = True) -> None:
    shim_dir.mkdir()
    shims = {
        "dirname": """#!/bin/sh
case "$1" in
  */*) printf '%s\n' "${1%/*}" ;;
  *) printf '%s\n' "." ;;
esac
""",
        "curl": """#!/bin/sh
printf 'curl %s\n' "$*" >> "$AQUANTAI_TEST_LOG"
if [ "$AQUANTAI_HEALTH_MODE" = "ready" ]; then
  printf '%s' "200"
else
  printf '%s' "503"
fi
""",
        "sleep": """#!/bin/sh
printf 'sleep %s\n' "$*" >> "$AQUANTAI_TEST_LOG"
exit 0
""",
        "uname": """#!/bin/sh
printf '%s\n' "$AQUANTAI_TEST_UNAME"
""",
        "open": """#!/bin/sh
printf 'open %s\n' "$*" >> "$AQUANTAI_TEST_LOG"
[ "$AQUANTAI_BROWSER_MODE" = "fail" ] && exit 1
exit 0
""",
        "xdg-open": """#!/bin/sh
printf 'xdg-open %s\n' "$*" >> "$AQUANTAI_TEST_LOG"
[ "$AQUANTAI_BROWSER_MODE" = "fail" ] && exit 1
exit 0
        """,
    }
    if include_docker:
        shims["docker"] = """#!/bin/sh
printf 'docker %s\n' "$*" >> "$AQUANTAI_TEST_LOG"
if [ "$AQUANTAI_DOCKER_MODE" = "compose-fail" ] && [ "$1" = "compose" ] && [ "$2" = "version" ]; then exit 1; fi
if [ "$AQUANTAI_DOCKER_MODE" = "daemon-fail" ] && [ "$1" = "info" ]; then exit 1; fi
if [ "$AQUANTAI_DOCKER_MODE" = "config-fail" ] && [ "$1" = "compose" ] && [ "$2" = "config" ]; then exit 1; fi
if [ "$AQUANTAI_DOCKER_MODE" = "up-fail" ] && [ "$1" = "compose" ] && [ "$2" = "up" ]; then exit 1; fi
exit 0
"""
    for name, content in shims.items():
        path = shim_dir / name
        path.write_text(content, encoding="ascii")
        path.chmod(0o755)


def _run_posix(
    repo: Path,
    shim_dir: Path,
    log_file: Path,
    os_name: str = "Linux",
    browser_mode: str = "ok",
    docker_mode: str = "ok",
    health_mode: str = "ready",
    script: str = "start-aquantai.sh",
    include_system_path: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    path_parts = (str(shim_dir), "/usr/bin", "/bin") if include_system_path else (str(shim_dir),)
    env["PATH"] = os.pathsep.join(path_parts)
    env["AQUANTAI_TEST_LOG"] = str(log_file)
    env["AQUANTAI_TEST_UNAME"] = os_name
    env["AQUANTAI_BROWSER_MODE"] = browser_mode
    env["AQUANTAI_DOCKER_MODE"] = docker_mode
    env["AQUANTAI_HEALTH_MODE"] = health_mode
    return subprocess.run(
        ("/bin/sh", str(repo / script)),
        cwd=repo.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_launcher_scope_and_fixed_urls() -> None:
    for name in LAUNCHERS:
        assert (ROOT / name).is_file()

    compose = _read("docker-compose.yml")
    scripts = "\n".join(_read(name) for name in LAUNCHERS)
    docs = _read("README.md") + (ROOT / "docs" / "local_usage.md").read_text(encoding="utf-8")

    assert '"8000:8000"' in compose
    assert "AQUANTAI_PORT" not in compose + scripts + docs
    assert HEALTH_URL in scripts
    assert DASHBOARD_URL in scripts
    assert DASHBOARD_URL in docs


def test_launcher_sources_are_bounded_and_non_destructive() -> None:
    starts = _read("start-aquantai.bat").lower() + _read("start-aquantai.sh").lower()
    stops = _read("stop-aquantai.bat").lower() + _read("stop-aquantai.sh").lower()
    all_scripts = starts + stops

    assert "for /l %%i in (1,1,%max_attempts%)" in starts
    assert 'while [ "$attempt" -le "$max_attempts" ]' in starts
    assert "result_wait_seconds=10" in starts + stops
    assert "--no-wait" in starts + stops
    assert "docker compose down" not in starts
    assert "docker compose down" in stops
    for forbidden in (
        "down -v",
        "--volumes",
        "docker volume rm",
        "docker image rm",
        "docker system prune",
        "remove-item",
        "rm -rf",
        "https://",
        "invoke-expression",
        "-executionpolicy",
    ):
        assert forbidden not in all_scripts
    assert not re.search(r"(?im)^\s*(?:eval|wget|irm)(?:\.exe)?\s", all_scripts)
    assert not re.search(r"\b(?:broker|order|trading)\b", all_scripts)


@pytest.mark.skipif(os.name != "nt", reason="Windows batch behavior requires Windows")
def test_windows_existing_env_is_byte_for_byte_unchanged_and_ready_urls_are_exact(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    original = b"SECRET=keep-this-byte-for-byte\r\nBINARY=\xff\x01"
    (repo / ".env").write_bytes(original)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_windows_shims(shim_dir)

    result = _run_windows(repo, _windows_env(shim_dir, log_file), "start-aquantai.bat", "--no-wait")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".env").read_bytes() == original
    log = log_file.read_text(encoding="utf-8")
    assert HEALTH_URL in log
    assert DASHBOARD_URL in log
    assert "Start-Process" in log


@pytest.mark.skipif(os.name != "nt", reason="Windows batch behavior requires Windows")
def test_windows_missing_env_repeated_start_and_repeated_stop_are_safe(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_windows_shims(shim_dir)
    env = _windows_env(shim_dir, log_file)

    first = _run_windows(repo, env, "start-aquantai.bat", "--no-wait")
    second = _run_windows(repo, env, "start-aquantai.bat", "--no-wait")
    stop_first = _run_windows(repo, env, "stop-aquantai.bat", "--no-wait")
    stop_second = _run_windows(repo, env, "stop-aquantai.bat", "--no-wait")

    assert (first.returncode, second.returncode, stop_first.returncode, stop_second.returncode) == (0, 0, 0, 0)
    assert (repo / ".env").read_bytes() == ENV_TEMPLATE
    log = log_file.read_text(encoding="utf-8").lower()
    assert log.count("docker compose up --build -d") == 2
    assert log.count("docker compose down") == 2
    down_lines = [line for line in log.splitlines() if "docker compose down" in line]
    assert all(" -v" not in line and "--volumes" not in line for line in down_lines)


@pytest.mark.skipif(os.name != "nt", reason="Windows batch behavior requires Windows")
@pytest.mark.parametrize(
    ("include_docker", "docker_mode", "expected"),
    (
        (False, "ok", "Docker was not found"),
        (True, "compose-fail", "Docker Compose was not found"),
        (True, "daemon-fail", "Docker Desktop is not running"),
    ),
)
def test_windows_prerequisite_failures_are_actionable(
    tmp_path: Path, include_docker: bool, docker_mode: str, expected: str
) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_windows_shims(shim_dir, include_docker=include_docker)
    env = _windows_env(shim_dir, log_file, AQUANTAI_DOCKER_MODE=docker_mode)

    result = _run_windows(repo, env, "start-aquantai.bat", "--no-wait")

    assert result.returncode != 0
    assert expected in result.stdout


@pytest.mark.skipif(os.name != "nt", reason="Windows batch behavior requires Windows")
def test_windows_health_check_terminates_and_port_conflict_is_actionable(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_windows_shims(shim_dir)

    health_result = _run_windows(
        repo,
        _windows_env(shim_dir, log_file, AQUANTAI_HEALTH_MODE="not-ready"),
        "start-aquantai.bat",
        "--no-wait",
    )
    health_log = log_file.read_text(encoding="utf-8")
    assert health_result.returncode != 0
    assert "health-check timeout" in health_result.stdout
    assert health_log.count(f"powershell health {HEALTH_URL}") == 30
    assert "docker compose ps" in health_log
    assert "docker compose logs --tail 30 app" in health_log

    log_file.write_text("", encoding="utf-8")
    port_result = _run_windows(
        repo,
        _windows_env(shim_dir, log_file, AQUANTAI_DOCKER_MODE="up-fail"),
        "start-aquantai.bat",
        "--no-wait",
    )
    assert port_result.returncode != 0
    assert "close the program using port 8000" in port_result.stdout
    assert "netstat -ano | findstr :8000" in port_result.stdout


@pytest.mark.skipif(os.name != "nt", reason="Windows batch behavior requires Windows")
def test_windows_default_result_window_is_bounded_and_preserves_exit_code(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_windows_shims(shim_dir, include_docker=False)

    result = _run_windows(repo, _windows_env(shim_dir, log_file), "start-aquantai.bat")

    assert result.returncode != 0
    assert "This window will close in 10 seconds" in result.stdout
    assert "timeout /t 10 /nobreak" in log_file.read_text(encoding="utf-8")


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher behavior requires a POSIX host")
@pytest.mark.parametrize(("os_name", "expected_opener", "unexpected_opener"), (("Darwin", "open", "xdg-open"), ("Linux", "xdg-open", "open")))
def test_posix_uses_only_the_platform_browser_opener(
    tmp_path: Path, os_name: str, expected_opener: str, unexpected_opener: str
) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_posix_shims(shim_dir)

    result = _run_posix(repo, shim_dir, log_file, os_name)

    assert result.returncode == 0, result.stdout + result.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith(f"{expected_opener} {DASHBOARD_URL}") for line in log_lines)
    assert not any(line.startswith(f"{unexpected_opener} ") for line in log_lines)


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher behavior requires a POSIX host")
def test_posix_browser_failure_prints_exact_dashboard_url(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_posix_shims(shim_dir)

    result = _run_posix(repo, shim_dir, log_file, "Linux", browser_mode="fail")

    assert result.returncode == 0
    assert f"Open {DASHBOARD_URL}" in result.stdout


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher behavior requires a POSIX host")
def test_posix_preserves_existing_env_and_repeated_start_stop_are_safe(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    original = b"SECRET=keep-this-byte-for-byte\nBINARY=\xff\x01"
    (repo / ".env").write_bytes(original)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_posix_shims(shim_dir)

    first = _run_posix(repo, shim_dir, log_file)
    second = _run_posix(repo, shim_dir, log_file)
    stop_first = _run_posix(repo, shim_dir, log_file, script="stop-aquantai.sh")
    stop_second = _run_posix(repo, shim_dir, log_file, script="stop-aquantai.sh")

    assert (first.returncode, second.returncode, stop_first.returncode, stop_second.returncode) == (0, 0, 0, 0)
    assert (repo / ".env").read_bytes() == original
    log = log_file.read_text(encoding="utf-8").lower()
    assert log.count("docker compose up --build -d") == 2
    assert log.count("docker compose down") == 2
    down_lines = [line for line in log.splitlines() if "docker compose down" in line]
    assert all(" -v" not in line and "--volumes" not in line for line in down_lines)


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher behavior requires a POSIX host")
def test_posix_creates_missing_env_from_template(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_posix_shims(shim_dir)

    result = _run_posix(repo, shim_dir, log_file)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".env").read_bytes() == ENV_TEMPLATE


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher behavior requires a POSIX host")
@pytest.mark.parametrize(
    ("include_docker", "docker_mode", "expected"),
    (
        (False, "ok", "Docker was not found"),
        (True, "compose-fail", "Docker Compose was not found"),
        (True, "daemon-fail", "Docker Desktop is not running"),
    ),
)
def test_posix_prerequisite_failures_are_actionable(
    tmp_path: Path, include_docker: bool, docker_mode: str, expected: str
) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_posix_shims(shim_dir, include_docker=include_docker)

    result = _run_posix(
        repo,
        shim_dir,
        log_file,
        docker_mode=docker_mode,
        include_system_path=include_docker,
    )

    assert result.returncode != 0
    assert expected in result.stdout + result.stderr


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher behavior requires a POSIX host")
def test_posix_health_check_terminates_and_port_conflict_is_actionable(tmp_path: Path) -> None:
    repo = _copy_launcher_repo(tmp_path)
    shim_dir = tmp_path / "command shims"
    log_file = tmp_path / "commands.log"
    _write_posix_shims(shim_dir)

    health_result = _run_posix(repo, shim_dir, log_file, health_mode="not-ready")
    health_log = log_file.read_text(encoding="utf-8")
    assert health_result.returncode != 0
    assert "health-check timeout" in health_result.stderr
    assert health_log.count(f"curl --silent --show-error --output /dev/null --write-out %{{http_code}} --max-time 2 {HEALTH_URL}") == 30
    assert "docker compose ps" in health_log
    assert "docker compose logs --tail 30 app" in health_log

    log_file.write_text("", encoding="utf-8")
    port_result = _run_posix(repo, shim_dir, log_file, docker_mode="up-fail")
    assert port_result.returncode != 0
    assert "close the program using port 8000" in port_result.stderr
    assert "lsof -i :8000 or ss -ltnp | grep :8000" in port_result.stderr
