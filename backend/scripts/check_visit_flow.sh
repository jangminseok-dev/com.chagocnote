#!/usr/bin/env bash
# 개발 환경에서 예약 등록 → 하루 목록·시간 칸 → 시작·완료 → 다음 예약 → 취소·되돌리기 → 노쇼 → customer 규칙까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_visit_flow.sh
# infra/ 에서 실행해야 한다 (운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문이 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
TODAY="$(TZ=Asia/Seoul date +%Y-%m-%d)"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

# field <경로> — JSON 응답에서 값을 꺼낸다. 예: field "['visits'][0]['visit_id']"
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# calc <식> — JSON 응답(d)으로 식을 계산한다. 예: calc "len(d['visits'])"
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
pet() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}"; }
act() { call POST "$S/visits/transitions" "$1" "{\"visit_ids\":$2,\"action\":\"$3\"${4:+,\"cancel_reason\":\"$4\"}}"; }

op=$(login "vflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"방문흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "vflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "vflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
echo "통과  매장 $shop_id 에 사장과 직원이 있다"
S="/v1/shops/$shop_id"

registered=$(call POST "$S/customers" "$staff_token" \
  "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":$(pet 콩이)}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']")
kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
dubu=$(call POST "$S/customers/$customer_id/pets" "$staff_token" "$(pet 두부)" | field "['pet']['pet_id']")
echo "통과  고객 $customer_id 과 반려동물 $kong, $dubu"

expect "기본 메뉴가 준비된다" "$(call GET "$S/menus" "$staff_token" | calc "[m['name'] for m in d['items']]")" \
  "['목욕', '위생', '부분 미용', '전체 미용', '스포팅']"
bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
booked=$(call POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$kong,$dubu],\"starts_at\":\"$(at 0 13)\",\"menu_ids\":[$bath]}")
visits=$(echo "$booked" | calc "[v['visit_id'] for v in d['visits']]")
expect "두 마리를 한 번에 예약하면 방문이 둘" "$(echo "$booked" | calc "len(d['visits'])")" "2"
expect "메뉴 기본 소요로 채운다" "$(echo "$booked" | field "['visits'][0]['duration_minutes']")" "60"
expect "같은 예약을 또 누르면 409" "$(status POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at 0 13)\"}")" "409"
expect "하루 목록의 마릿수" "$(call GET "$S/visits?date=$TODAY" "$staff_token" | field "['counts']['visit_count']")" "2"
expect "13시 칸은 겹침" "$(call GET "$S/visits/slots?date=$TODAY&duration=60&at=13:00" "$staff_token" | field "['slots'][0]['warnings']")" "['overlap']"

expect "가족 묶음을 한 번에 시작" "$(act "$staff_token" "$visits" start | calc "[v['status'] for v in d['visits']]")" "['in_progress', 'in_progress']"
expect "가족 묶음을 한 번에 완료" "$(act "$staff_token" "$visits" complete | calc "[v['status'] for v in d['visits']]")" "['completed', 'completed']"
first=$(echo "$booked" | field "['visits'][0]['visit_id']")
draft=$(call GET "$S/visits/$first/next-draft" "$staff_token")
expect "다음 예약은 4주 뒤 같은 시각" "$(echo "$draft" | field "['starts_at']")" "$(at 28 13)"
expect "지난번처럼 소요를 채운다" "$(call GET "$S/visits/defaults?pet_id=$kong" "$staff_token" | field "['duration_minutes']")" "60"
expect "최근 방문순 맨 앞" "$(call GET "$S/customers?sort=last_visit" "$staff_token" | field "['items'][0]['customer_id']")" "$customer_id"

later=$(call POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at 3 11)\"}" | field "['visits'][0]['visit_id']")
expect "취소에는 사유" "$(act "$staff_token" "[$later]" cancel | field "['code']")" "VALIDATION_ERROR"
expect "보호자 요청으로 취소" "$(act "$staff_token" "[$later]" cancel customer_request | field "['visits'][0]['cancel_reason']")" "customer_request"
expect "되돌리면 다시 예약됨" "$(act "$staff_token" "[$later]" revert | field "['visits'][0]['status']")" "reserved"
expect "예약 시각 전에는 노쇼 불가" "$(act "$staff_token" "[$later]" no_show | field "['code']")" "VISIT_NOT_YET"
past=$(call POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$dubu],\"starts_at\":\"$(at -1 10)\"}" | field "['visits'][0]['visit_id']")
expect "지난 예약은 노쇼 처리" "$(act "$staff_token" "[$past]" no_show | field "['visits'][0]['status']")" "no_show"
expect "고객 상세에 노쇼 횟수" "$(call GET "$S/customers/$customer_id" "$staff_token" | field "['no_show_count']")" "1"

expect "방문 있는 아이는 지우지 못한다" "$(status DELETE "$S/pets/$dubu" "$staff_token")" "409"
expect "예약 남은 아이는 무지개다리 불가" "$(status POST "$S/pets/$kong/passed-away" "$staff_token")" "409"
expect "예약 남은 고객은 삭제 불가" "$(status DELETE "$S/customers/$customer_id" "$owner_token")" "409"

settings='{"opens_at":"10:00","closes_at":"19:00","default_duration_minutes":120,"closed_weekdays":[0]}'
expect "직원은 일정을 못 바꾼다" "$(status PUT "$S/visit-settings" "$staff_token" "$settings")" "403"
expect "사장은 일정을 바꾼다" "$(call PUT "$S/visit-settings" "$owner_token" "$settings" | field "['closed_weekdays']")" "[0]"
expect "직원은 메뉴를 못 만든다" "$(status POST "$S/menus" "$staff_token" '{"name":"발톱"}')" "403"
expect "사장은 메뉴를 만든다" "$(status POST "$S/menus" "$owner_token" '{"name":"발톱"}')" "201"
expect "달력 한 달" "$(call GET "$S/visits/calendar?month=${TODAY:0:7}" "$staff_token" | calc "len(d['days']) >= 28")" "True"

echo "전체 흐름 확인 완료"
