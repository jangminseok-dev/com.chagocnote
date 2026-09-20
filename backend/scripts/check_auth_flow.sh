#!/usr/bin/env bash
# 개발 환경에서 로그인 → 내 정보 → 갱신 → 재사용 감지 → 로그아웃을 끝까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_auth_flow.sh
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
NAME="flow-check-$(date +%s)"

field() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
post() { curl -s -X POST "$BASE$1" -H 'Content-Type: application/json' -d "$2"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }

login=$(post /v1/auth/social "{\"provider\":\"dev\",\"token\":\"$NAME\"}")
access=$(echo "$login" | field access_token)
refresh1=$(echo "$login" | field refresh_token)
expect "처음 로그인하면 새 유저다" "$(echo "$login" | field is_new_user)" "True"

me=$(curl -s "$BASE/v1/me" -H "Authorization: Bearer $access")
expect "내 정보에 이름이 나온다" "$(echo "$me" | field display_name)" "$NAME"
expect "토큰 없이 내 정보를 부르면 401" "$(status "$BASE/v1/me")" "401"

rotated=$(post /v1/auth/refresh "{\"refresh_token\":\"$refresh1\"}")
refresh2=$(echo "$rotated" | field refresh_token)
if [ "$refresh1" = "$refresh2" ]; then echo "실패  갱신하면 리프레시 토큰이 바뀌어야 한다"; exit 1; fi
echo "통과  갱신하면 리프레시 토큰이 바뀐다"

expect "이미 쓴 리프레시 토큰은 401" \
  "$(status -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh1\"}")" "401"
expect "재사용이 감지되면 새 토큰도 함께 폐기된다" \
  "$(status -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh2\"}")" "401"

again=$(post /v1/auth/social "{\"provider\":\"dev\",\"token\":\"$NAME\"}")
expect "다시 로그인하면 기존 유저다" "$(echo "$again" | field is_new_user)" "False"
refresh3=$(echo "$again" | field refresh_token)
expect "로그아웃은 204" \
  "$(status -X POST "$BASE/v1/auth/logout" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh3\"}")" "204"
expect "로그아웃한 리프레시 토큰은 401" \
  "$(status -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh3\"}")" "401"

echo "전체 흐름 확인 완료"
