import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_URL = "http://127.0.0.1:8000/dashboard"
HEALTH_URL = "http://127.0.0.1:8000/health"


def _read_script(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_cross_platform_launcher_files_exist() -> None:
    for name in ("start-aquantai.bat", "stop-aquantai.bat", "start-aquantai.sh", "stop-aquantai.sh"):
        assert (ROOT / name).is_file()


def test_start_scripts_resolve_repository_root_and_preserve_existing_env() -> None:
    windows = _read_script("start-aquantai.bat")
    posix = _read_script("start-aquantai.sh")

    assert "%~dp0" in windows
    assert 'pushd "%SCRIPT_DIR%"' in windows
    assert 'if not exist ".env" (' in windows
    assert 'copy /-y ".env.example" ".env"' in windows
    assert "Keeping your existing .env file unchanged." in windows

    assert 'cd -- "$(dirname -- "$0")"' in posix
    assert 'if [ ! -f .env ]; then' in posix
    assert "cp .env.example .env" in posix
    assert "Keeping your existing .env file unchanged." in posix


def test_start_scripts_check_docker_and_use_bounded_local_health_check() -> None:
    windows = _read_script("start-aquantai.bat")
    posix = _read_script("start-aquantai.sh")

    assert "where docker" in windows
    assert "docker compose version" in windows
    assert "docker info" in windows
    assert 'set "MAX_ATTEMPTS=30"' in windows
    assert "for /L %%I in (1,1,%MAX_ATTEMPTS%)" in windows
    assert 'set "AQUANTAI_PORT=8000"' in windows
    assert 'set "HEALTH_URL=http://127.0.0.1:%AQUANTAI_PORT%/health"' in windows
    assert 'set "DASHBOARD_URL=http://127.0.0.1:%AQUANTAI_PORT%/dashboard"' in windows
    assert "docker compose up --build -d" in windows
    assert "docker compose config --quiet" in windows
    assert "docker compose ps" in windows
    assert "docker compose logs --tail 30 app" in windows

    assert "command -v docker" in posix
    assert "docker compose version" in posix
    assert "docker info" in posix
    assert "MAX_ATTEMPTS=30" in posix
    assert 'while [ "$attempt" -le "$MAX_ATTEMPTS" ]' in posix
    assert 'AQUANTAI_PORT="${AQUANTAI_PORT:-8000}"' in posix
    assert 'HEALTH_URL="http://127.0.0.1:${AQUANTAI_PORT}/health"' in posix
    assert 'DASHBOARD_URL="http://127.0.0.1:${AQUANTAI_PORT}/dashboard"' in posix
    assert "docker compose up --build -d" in posix
    assert "docker compose config --quiet" in posix
    assert "docker compose ps" in posix
    assert "docker compose logs --tail 30 app" in posix

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"${AQUANTAI_PORT:-8000}:8000"' in compose


def test_launchers_document_platforms_and_actionable_diagnostics() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    usage = (ROOT / "docs" / "local_usage.md").read_text(encoding="utf-8")
    scripts = _read_script("start-aquantai.bat") + _read_script("start-aquantai.sh")

    assert DASHBOARD_URL in readme
    assert DASHBOARD_URL in usage
    assert "### Windows" in usage
    assert "### macOS" in usage
    assert "### Linux" in usage
    for expected in ("pip", "setuptools", "package download", "internet", "proxy", "port", "health-check timeout"):
        assert expected.lower() in scripts.lower() or expected.lower() in usage.lower()


def test_stop_scripts_keep_volumes_images_and_env() -> None:
    for name in ("stop-aquantai.bat", "stop-aquantai.sh"):
        script = _read_script(name).lower()

        assert "docker compose down" in script
        assert "down -v" not in script
        assert "--volumes" not in script
        assert "docker volume rm" not in script
        assert "docker image rm" not in script
        assert "docker system prune" not in script
        assert "remove-item" not in script
        assert "rm -rf" not in script
        assert ".env file, docker volumes, images, and local files will be kept" in script


def test_launchers_avoid_remote_downloads_execution_bypasses_and_trading_commands() -> None:
    scripts = "\n".join(
        _read_script(name).lower()
        for name in ("start-aquantai.bat", "stop-aquantai.bat", "start-aquantai.sh", "stop-aquantai.sh")
    )

    for forbidden in ("https://", "invoke-expression", "-executionpolicy"):
        assert forbidden not in scripts
    assert not re.search(r"(?im)^\s*(?:eval|wget|irm)(?:\.exe)?\s", scripts)
    assert not re.search(r"\b(?:broker|order|trading)\b", scripts)
    urls = re.findall(r"https?://[^\s\"']+", scripts)
    assert urls
    assert all(url.startswith("http://127.0.0.1:") for url in urls)
    assert "docker compose down" not in _read_script("start-aquantai.bat").lower()
    assert "docker compose down" not in _read_script("start-aquantai.sh").lower()
