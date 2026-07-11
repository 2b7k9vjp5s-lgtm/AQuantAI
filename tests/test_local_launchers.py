import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_URL = "http://127.0.0.1:8200/dashboard"
HEALTH_URL = "http://127.0.0.1:8200/health"


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
    assert 'set "AQUANTAI_PORT=8200"' in windows
    assert 'set "HEALTH_URL=http://127.0.0.1:%AQUANTAI_PORT%/health"' in windows
    assert 'set "DASHBOARD_URL=http://127.0.0.1:%AQUANTAI_PORT%/dashboard"' in windows
    assert "docker compose up --build -d" in windows

    assert "command -v docker" in posix
    assert "docker compose version" in posix
    assert "docker info" in posix
    assert "MAX_ATTEMPTS=30" in posix
    assert 'while [ "$attempt" -le "$MAX_ATTEMPTS" ]' in posix
    assert 'AQUANTAI_PORT="${AQUANTAI_PORT:-8200}"' in posix
    assert 'HEALTH_URL="http://127.0.0.1:${AQUANTAI_PORT}/health"' in posix
    assert 'DASHBOARD_URL="http://127.0.0.1:${AQUANTAI_PORT}/dashboard"' in posix
    assert "docker compose up --build -d" in posix

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"${AQUANTAI_PORT:-8200}:8000"' in compose


def test_stop_scripts_keep_volumes_images_and_env() -> None:
    for name in ("stop-aquantai.bat", "stop-aquantai.sh"):
        script = _read_script(name).lower()

        assert "docker compose down" in script
        assert "down -v" not in script
        assert "--volumes" not in script
        assert "docker volume rm" not in script
        assert "docker image rm" not in script
        assert "remove-item" not in script
        assert "rm -rf" not in script
        assert ".env file, docker volumes, images, and local files will be kept" in script


def test_launchers_avoid_remote_downloads_execution_bypasses_and_trading_commands() -> None:
    scripts = "\n".join(
        _read_script(name).lower()
        for name in ("start-aquantai.bat", "stop-aquantai.bat", "start-aquantai.sh", "stop-aquantai.sh")
    )

    for forbidden in ("https://", "invoke-expression", "-executionpolicy", " eval", "wget ", "irm ", "broker", "order", "trading"):
        assert forbidden not in scripts
    urls = re.findall(r"https?://[^\s\"']+", scripts)
    assert urls
    assert all(url.startswith("http://127.0.0.1:") for url in urls)
