#!/usr/bin/env bash
# 개발 환경에서 ⑭-1 반복 예약 흐름을 게이트웨이를 거쳐 확인한다 — 알림톡 연동(가짜 업체) → 간격·횟수 기본값 →
# 회차 미리 보기 → 가족 6번 잡기 → 알림 줄(접수 한 통·리마인드 회차마다) → 보낼 것 묶음에 회차 전부 → 이후 전부 옮기기:
# 걸린 회차 409 → 빼고 다시 → 이후 전부 취소(보낼 글에 회차 전부) → 지난 회차로 시작한 짧은 묶음의 마지막 회차 완료 →
# 이어 잡기 초안 → 직원도 반복으로 잡는다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_repeat_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정과 템플릿 승인을 docker compose 로 한다). dev 는 가짜 게이트웨이라 실제 발송이 없다.
# 개발 DB 에 확인용 매장·유저·고객·방문·알림 줄이 남는다. 단계 이름과 판정만 찍는다 — 보낼 글은 찍지 않는다(줄 수만 센다).
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
phone() { echo "010$(printf '%04d' $(((STAMP + $1) % 10000)))1234"; }   # 끝이 1234 — 가짜 업체가 성공으로 답한다
ADMIN_PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
TOKEN_REQ="{\"search_id\":\"repeat-$STAMP\",\"admin_phone\":\"$ADMIN_PHONE\",\"category_code\":\"003001\"}"
LINK_REQ="${TOKEN_REQ%\}},\"token\":\"000000\"}"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
enc() { python3 -c "import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$1"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

# 1. 매장·사장·직원, 알림톡 연동(토큰 000000)과 템플릿 승인
op=$(login "repeat-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"반복흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "repeat-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
staff_code=$(call POST "$S/invites" "$owner" | field "['code']")
staff=$(login "repeat-staff-$STAMP" | field "['access_token']")
staff_req="{\"code\":\"$staff_code\"}"
call POST /v1/invites/accept "$staff" "$staff_req" >/dev/null
call POST "$S/notification/channel/token" "$owner" "$TOKEN_REQ" >/dev/null
expect "1 알림톡을 잇는다(가짜 업체)" "$(call POST "$S/notification/channel" "$owner" "$LINK_REQ" | field "['channel']['status']")" "linked"
docker compose run --rm backend python scripts/reregister_templates.py --refresh --shop "$shop_id" >/dev/null

# family <이름> <번호> <아이 이름> — "고객ID 아이ID"
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}}"
  call POST "$S/customers" "$owner" "$body" | calc "f\"{d['customer']['customer_id']} {d['pets'][0]['pet_id']}\""
}
read -r kim kong <<<"$(family 김민지 "$(phone 0)" 콩이)"
dubu_req='{"name":"두부","species":"dog","breed":"푸들","sex":"male","neutered":true,"birth_year":2022,"weight_kg":4.1,"no_known_conditions":true}'
dubu=$(call POST "$S/customers/$kim/pets" "$owner" "$dubu_req" | field "['pet']['pet_id']")

# 2. 기본값과 미리 보기 — 방문이 없으면 매장의 기본 간격(4주)·6번
expect "2 간격·횟수의 기본값은 매장 값과 6번" \
  "$(call GET "$S/visits/repeat-defaults?customer_id=$kim&pet_ids=$kong&pet_ids=$dubu" "$owner" | calc "(d['interval_weeks'], d['source'], d['count'])")" "(4, 'shop', 6)"
FIRST="$(at 2 14)"
preview=$(call GET "$S/visits/repeat-preview?customer_id=$kim&pet_ids=$kong&pet_ids=$dubu&starts_at=$(enc "$FIRST")&interval_weeks=1&count=6" "$owner")
expect "2 미리 보기는 여섯 회차이고 1년 밖은 없다" "$(echo "$preview" | calc "(len(d['occurrences']), d['beyond_horizon'], any(o['taken'] for o in d['occurrences']))")" "(6, 0, False)"

# 3. 가족 6번 잡기 — 한 묶음, 방문 열둘
book_req="{\"customer_id\":$kim,\"pet_ids\":[$kong,$dubu],\"starts_at\":\"$FIRST\",\"duration_minutes\":60,\"repeat\":{\"interval_weeks\":1,\"count\":6}}"
booked=$(call POST "$S/visits" "$owner" "$book_req")
expect "3 방문 열둘·회차 여섯" "$(echo "$booked" | calc "(len(d['visits']), len(d['series']['occurrences']))")" "(12, 6)"
read -r -a ids <<<"$(echo "$booked" | calc "' '.join(str(v['visit_id']) for v in d['visits'] if v['pet']['pet_id'] == $kong)")"
series_id=$(echo "$booked" | field "['series']['id']")

# 4. 알림 줄 — 접수는 첫 회차 한 통, 리마인드는 회차마다(가족 묶음 한 통). 취소된 줄은 세지 않는다.
kinds() {
  for v in $(echo "$booked" | calc "' '.join(str(v['visit_id']) for v in d['visits'])"); do
    call GET "$S/visits/$v/notifications" "$owner" | calc "'\n'.join(m['kind'] for m in d['items'] if m['status'] != 'canceled')"
  done | grep -c "^$1$" || true
}
expect "4 접수 안내는 한 통" "$(kinds confirm)" "1"
expect "4 리마인드는 회차마다 한 통" "$(kinds reminder)" "6"

# 5. 보낼 것 묶음 — 접수 안내 한 토막에 회차 여섯이 다 있다(글은 찍지 않고 줄 수만)
expect "5 예약 토막 하나에 회차 여섯 줄" \
  "$(call POST "$S/visits/${ids[0]}/send-bundle" "$owner" | calc "(d['parts'][0]['kind'], d['parts'][0]['text'].count('\n· '))")" "('reservation', 6)"
expect "5 방문 상세는 6번 중 2번째" \
  "$(call GET "$S/visits/${ids[1]}" "$owner" | calc "(d['series']['position'], d['series']['total'], d['series']['is_last'])")" "(2, 6, False)"

# 6. 이후 전부 옮기기 — 3회차의 새 자리에 따로 잡은 예약이 있으면 409, 그 회차만 빼고 다시
outside_req="{\"customer_id\":$kim,\"pet_ids\":[$kong],\"starts_at\":\"$(at 16 15)\"}"
call POST "$S/visits" "$owner" "$outside_req" >/dev/null
move_req="{\"visit_ids\":[${ids[1]}],\"starts_at\":\"$(at 9 15)\",\"scope\":\"following\",\"family\":false}"
conflict=$(call POST "$S/visits/reschedule" "$owner" "$move_req")
expect "6 걸린 회차가 있으면 409 와 그 회차" "$(echo "$conflict" | calc "(d['code'], [c['visit_id'] for c in d['details']['conflicts']] == [${ids[2]}], d['details']['conflicts'][0]['reason'])")" "('VISIT_SERIES_CONFLICT', True, 'taken')"
expect "6 409 뒤 아무것도 옮겨지지 않았다" "$(call GET "$S/visits/${ids[1]}" "$owner" | field "['visit']['starts_at']")" "$(at 9 14)"
skip_req="${move_req%\}},\"skip_visit_ids\":[${ids[2]}]}"
moved=$(call POST "$S/visits/reschedule" "$owner" "$skip_req")
expect "6 빼고 다시 보내면 안내 글 하나와 함께 옮긴다" "$(echo "$moved" | calc "(len(d['visits']), d['notice'][0]['kind'])")" "(4, 'series_change')"
expect "6 뺀 회차는 그대로" "$(call GET "$S/visits/${ids[2]}" "$owner" | field "['visit']['starts_at']")" "$(at 16 14)"

# 7. 이후 전부 취소 — 콩이의 5회차(6 에서 15시로 옮김)부터 가족 함께. 두부의 5회차(14시)는 그보다 앞이라 남는다.
cancel_req="{\"visit_ids\":[${ids[4]}],\"action\":\"cancel\",\"cancel_reason\":\"shop_reason\",\"scope\":\"following\"}"
canceled=$(call POST "$S/visits/transitions" "$owner" "$cancel_req")
expect "7 콩이 5·6회차와 두부 6회차를 취소하고 글에 그 시각 셋" "$(echo "$canceled" | calc "(len(d['visits']), d['notice'][0]['kind'], d['notice'][0]['text'].count('\n· '))")" "(3, 'series_cancel', 3)"
expect "7 묶음 목록은 상태와 상관없이 열두 줄(따로 잡은 예약은 묶음 밖)" "$(call GET "$S/visit-series/$series_id" "$owner" | calc "len(d['visits'])")" "12"

# 8. 지난 회차로 시작한 짧은 묶음(2주 전·1주 전·오늘 11시) — 마지막 회차를 마치면 이어 잡기 초안
read -r lee bori <<<"$(family 이보리 "$(phone 1)" 보리)"
past_req="{\"customer_id\":$lee,\"pet_ids\":[$bori],\"starts_at\":\"$(at -14 11)\",\"duration_minutes\":60,\"repeat\":{\"interval_weeks\":1,\"count\":3}}"
past=$(call POST "$S/visits" "$owner" "$past_req")
last=$(echo "$past" | calc "d['visits'][-1]['visit_id']")
for action in start complete; do
  body="{\"visit_ids\":[$last],\"action\":\"$action\"}"; call POST "$S/visits/transitions" "$owner" "$body" >/dev/null
done
expect "8 마지막 회차의 초안은 같은 간격으로 6번 더" \
  "$(call GET "$S/visits/$last/next-draft" "$owner" | calc "(d['repeat']['interval_weeks'], d['repeat']['count'], d['repeat']['starts_at'][:10], d['upcoming_starts_at'])")" \
  "(1, 6, '$(at 7 11 | cut -c1-10)', None)"

# 9. 직원도 반복으로 잡는다(reservation:write)
staff_req="{\"customer_id\":$lee,\"pet_ids\":[$bori],\"starts_at\":\"$(at 30 10)\",\"repeat\":{\"interval_weeks\":2,\"count\":2}}"
expect "9 직원의 반복 등록은 201" "$(status POST "$S/visits" "$staff" "$staff_req")" "201"
echo "반복 예약 흐름 끝"
