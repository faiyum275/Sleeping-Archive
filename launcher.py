from __future__ import annotations

import argparse
from contextlib import closing
from pathlib import Path
import socket
import threading
import time
import webbrowser

import uvicorn

from backend.config import APP_HOME_DIR


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_SEARCH_LIMIT = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Sleeping Archive.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to.")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Preferred port to bind to.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the local server without opening a browser.",
    )
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=20.0,
        help="Seconds to wait for the local server before giving up on auto-open.",
    )
    return parser.parse_args()


def find_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + PORT_SEARCH_LIMIT):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError("사용 가능한 포트를 찾지 못했습니다.")


def wait_for_server(host: str, port: int, timeout_seconds: float) -> bool:
    deadline = time.time() + max(0.5, timeout_seconds)
    while time.time() < deadline:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.2)
    return False


def browser_url(host: str, port: int) -> str:
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    return f"http://{display_host}:{port}"


def open_browser_when_ready(host: str, port: int, timeout_seconds: float) -> None:
    url = browser_url(host, port)
    if wait_for_server(host, port, timeout_seconds):
        webbrowser.open(url, new=2)
        print(f"브라우저를 열었습니다: {url}")
        return
    print(f"브라우저 자동 열기에 실패했습니다. 직접 접속하세요: {url}")


def launch_server(host: str, port: int) -> None:
    config = uvicorn.Config(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
        access_log=False,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


def ensure_app_home() -> None:
    APP_HOME_DIR.mkdir(parents=True, exist_ok=True)


def print_banner(host: str, port: int) -> None:
    print("잠든 서고 실행 준비를 시작합니다.")
    print(f"저장 위치: {APP_HOME_DIR}")
    print(f"접속 주소: {browser_url(host, port)}")
    print("종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.")


def main() -> None:
    args = parse_args()
    ensure_app_home()
    port = find_available_port(args.host, args.port)
    print_banner(args.host, port)

    if not args.no_browser:
        threading.Thread(
            target=open_browser_when_ready,
            args=(args.host, port, args.startup_timeout),
            daemon=True,
        ).start()

    launch_server(args.host, port)


if __name__ == "__main__":
    main()
