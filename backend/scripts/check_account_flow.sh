#!/usr/bin/env bash
# 개발 환경에서 회원 탈퇴 → 접근 차단 → 같은 이름으로 새 가입을 게이트웨이를 거쳐 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_account_flow.sh
# 개발 DB 에 "탈퇴한 사용자" 행과 확인용 유저가 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
NAME="flow-account-$(date +%s)"

field() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

first=$(login "$NAME"); token=$(echo "$first" | field access_token); refresh=$(echo "$first" | field refresh_token)
first_id=$(echo "$first" | field user_id)

expect "같은 제공자를 또 붙일 수는 없다" "$(status POST /v1/auth/identities "$token" "{\"provider\":\"dev\",\"token\":\"$NAME-2\"}")" "409"
expect "마지막 로그인 수단은 해제할 수 없다" "$(status DELETE /v1/auth/identities/dev "$token")" "409"
expect "탈퇴는 204" "$(status DELETE /v1/auth/account "$token")" "204"
expect "탈퇴한 뒤에는 이미 받은 토큰으로도 내 정보를 볼 수 없다" "$(status GET /v1/me "$token")" "401"
expect "탈퇴한 뒤에는 리프레시 토큰도 쓸 수 없다" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh\"}")" "401"

again=$(login "$NAME")
expect "같은 이름으로 다시 로그인하면 새 유저다" "$(echo "$again" | field is_new_user)" "True"
if [ "$(echo "$again" | field user_id)" = "$first_id" ]; then echo "실패  탈퇴한 유저 ID 가 다시 쓰였다"; exit 1; fi
echo "통과  새 유저 ID 가 발급되었다"

echo "전체 흐름 확인 완료"
