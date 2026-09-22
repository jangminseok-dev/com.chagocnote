#!/usr/bin/env bash
# 개발 환경에서 고객 등록 → 번호 조회 → 반려동물 추가 → 검색 → 무지개다리 → 고객 삭제(익명화)를 끝까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_customer_flow.sh
# infra/ 에서 실행해야 한다 (운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저와 익명화한 고객이 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
LAST4="${PHONE: -4}"

# field <경로> — JSON 응답에서 값을 꺼낸다. 예: field "['customer']['customer_id']"
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
# call <메서드> <경로> <토큰> [본문] — 응답 본문을 출력한다
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# status <메서드> <경로> <토큰> [본문] — 상태 코드만 출력한다
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

pet() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,$2}"; }

op=$(login "cflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"고객흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "cflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "cflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
echo "통과  매장 $shop_id 에 사장과 직원이 있다"
S="/v1/shops/$shop_id"

expect "등록 전 번호 조회는 404" "$(status GET "$S/customers/lookup?phone=$PHONE" "$staff_token")" "404"
registered=$(call POST "$S/customers" "$staff_token" \
  "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":$(pet 콩이 '"no_known_conditions":true')}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']")
kong_id=$(echo "$registered" | field "['pets'][0]['pet_id']")
echo "통과  직원이 고객 $customer_id 와 첫 반려동물을 등록했다"
expect "같은 번호로 다시 등록하면 409" "$(status POST "$S/customers" "$staff_token" \
  "{\"customer\":{\"name\":\"다른사람\",\"phone\":\"$PHONE\",\"marketing_consent\":false},\"pet\":$(pet 두부 '"no_known_conditions":true')}")" "409"
expect "번호 조회는 보호자와 아이 이름을 준다" "$(call GET "$S/customers/lookup?phone=$PHONE" "$staff_token" | field "['pet_names']")" "['콩이']"

dubu_id=$(call POST "$S/customers/$customer_id/pets" "$staff_token" \
  "$(pet 두부 '"no_known_conditions":false,"conditions":[{"type_code":"patella_luxation","note":"2기"}]')" | field "['pet']['pet_id']")
echo "통과  반려동물 $dubu_id 을(를) 더했다"
expect "질병도 질병 없음도 아니면 422" "$(status PUT "$S/pets/$dubu_id" "$staff_token" "$(pet 두부 '"no_known_conditions":false')")" "422"

expect "뒷자리로 찾으면 가족이 나온다" "$(call GET "$S/customers?q=$LAST4" "$staff_token" | field "['items'][0]['customer_id']")" "$customer_id"
expect "초성 ㅋㅇ 로 찾으면 가족이 나온다" "$(call GET "$S/customers?q=%E3%85%8B%E3%85%87" "$staff_token" | field "['items'][0]['customer_id']")" "$customer_id"
expect "목록의 번호는 가려져 있다" "$(call GET "$S/customers" "$staff_token" | field "['items'][0]['phone_masked'][-4:]")" "$LAST4"
expect "목록 제목의 반려동물 수" "$(call GET "$S/customers" "$staff_token" | field "['pet_count']")" "2"

expect "무지개다리를 표시한다" "$(status POST "$S/pets/$kong_id/passed-away" "$staff_token")" "200"
expect "무지개다리 아이는 목록 기본에서 빠진다" "$(call GET "$S/customers" "$staff_token" | field "['pet_count']")" "1"
expect "잘못 등록한 아이를 지운다" "$(status DELETE "$S/pets/$dubu_id" "$staff_token")" "204"
expect "마지막 아이는 지울 수 없다" "$(status DELETE "$S/pets/$kong_id" "$staff_token")" "409"

expect "직원은 고객을 삭제할 수 없다" "$(status DELETE "$S/customers/$customer_id" "$staff_token")" "403"
expect "사장은 고객을 삭제한다" "$(status DELETE "$S/customers/$customer_id" "$owner_token")" "204"
expect "삭제한 고객은 조회되지 않는다" "$(status GET "$S/customers/$customer_id" "$owner_token")" "404"
expect "삭제한 고객은 번호 조회에 걸리지 않는다" "$(status GET "$S/customers/lookup?phone=$PHONE" "$owner_token")" "404"
expect "삭제한 고객은 검색에 걸리지 않는다" "$(call GET "$S/customers?q=$LAST4&include_passed=true" "$owner_token" | field "['items']")" "[]"

echo "전체 흐름 확인 완료"
