"""두 프로세스의 라우트 표를 출력한다. 라우터를 추가하거나 옮긴 변경은 전후를 비교한다.

auth_main 을 import 하려면 JWT 개인키가 필요하므로 auth 서비스 컨테이너에서 실행한다:
    cd infra && docker compose run --rm --no-deps auth python scripts/print_routes.py
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts

_HIDDEN = ("/docs", "/redoc", "/openapi")


def collect_routes(apps: dict[str, FastAPI]) -> list[tuple[str, str, str, str]]:
    rows = [
        (process, method, ctx.path, ctx.name)
        for process, app in apps.items()
        for ctx in iter_route_contexts(app.routes)
        if isinstance(ctx.original_route, APIRoute)
        and not ctx.path.startswith(_HIDDEN)
        for method in sorted(ctx.methods)
    ]
    return sorted(rows, key=lambda row: (row[2], row[1]))


def run() -> None:
    import auth_main
    import main as api_main

    for process, method, path, name in collect_routes(
        {"auth": auth_main.app, "backend": api_main.app}
    ):
        print(f"{process:8} {method:7} {path:44} {name}")


if __name__ == "__main__":
    run()
