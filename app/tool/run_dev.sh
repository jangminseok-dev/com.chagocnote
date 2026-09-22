#!/usr/bin/env bash
# 개발용 실행. 백엔드는 infra/ 에서 docker compose up -d 로 먼저 띄운다.
# iOS 시뮬레이터는 127.0.0.1, Android 에뮬레이터는 10.0.2.2 로 호스트에 닿는다.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE_URL="${API_BASE_URL:-http://127.0.0.1:8080}"
exec flutter run \
  --dart-define=APP_ENV=dev \
  --dart-define=API_BASE_URL="$BASE_URL" \
  "$@"
