#!/usr/bin/env bash
# 개발 환경에서 매장 개설 → 사장 합류 → 직원 초대·합류 → 역할 변경 → 내보내기를 끝까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_shop_flow.sh
# infra/ 에서 실행해야 한다 (운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장과 유저가 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"

field() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
# call <메서드> <경로> <토큰> [본문] — 응답 본문을 출력한다
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# status <메서드> <경로> <토큰> [본문] — 상태 코드만 출력한다
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "flow-op-$STAMP"); op_token=$(echo "$op" | field access_token); op_id=$(echo "$op" | field user_id)
expect "운영자가 되기 전에는 매장을 개설할 수 없다" "$(status POST /v1/platform/shops "$op_token" '{"name":"x"}')" "403"
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"흐름확인-$STAMP\"}")
shop_id=$(echo "$shop" | field shop_id); owner_code=$(echo "$shop" | field owner_invite_code)
echo "통과  운영자가 매장 $shop_id 을(를) 개설했다"

owner_token=$(login "flow-owner-$STAMP" | field access_token)
expect "사장용 초대 코드로 합류하면 사장이다" "$(call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" | field role)" "owner"

staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field code)
staff_token=$(login "flow-staff-$STAMP" | field access_token)
joined=$(call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}")
expect "직원용 초대 코드로 합류하면 직원이다" "$(echo "$joined" | field role)" "staff"
staff_member_id=$(echo "$joined" | field member_id)

count=$(call GET "/v1/shops/$shop_id/members" "$staff_token" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
expect "멤버 목록에 두 명이 보인다" "$count" "2"
expect "직원은 초대 코드를 만들 수 없다" "$(status POST "/v1/shops/$shop_id/invites" "$staff_token")" "403"
expect "직원을 사장으로 올린다" "$(status PATCH "/v1/shops/$shop_id/members/$staff_member_id" "$owner_token" '{"role":"owner"}')" "200"
expect "사장이 된 직원은 초대 코드를 만들 수 있다" "$(status POST "/v1/shops/$shop_id/invites" "$staff_token")" "201"
expect "다시 직원으로 낮춘다" "$(status PATCH "/v1/shops/$shop_id/members/$staff_member_id" "$owner_token" '{"role":"staff"}')" "200"
expect "직원을 내보낸다" "$(status DELETE "/v1/shops/$shop_id/members/$staff_member_id" "$owner_token")" "204"
expect "내보낸 직원은 바로 접근할 수 없다" "$(status GET "/v1/shops/$shop_id/members" "$staff_token")" "403"

echo "전체 흐름 확인 완료"
