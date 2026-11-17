#!/usr/bin/env bash
# ⑬-2 시뮬레이터 흐름의 준비물 — 매장·사장·직원·가족 넷: 콩이(35일마다 세 번 → 5주, 다음 5일 뒤 — 곧), 두부(50일마다 세 번
# → 7주, 어제가 다음 올 때 — 지남), 보리(40일 전 한 번 — 기본 4주로 어림, 지남), 망고(어제 완료 — 정가 35,000 메뉴, 기록에
# 케어 노트만 → 결제 안 적음·알림장 안 보냄). infra/ 에서 실행(bash ../app/tool/prepare_revisit_flow.sh). 개발 스택이 떠 있어야
# 한다. 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 토큰은 찍지 않는다. 개발 DB 에 확인용 매장·유저·고객·방문이
# 남는다. zsh 에서는 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
phone() { echo "010$(printf '%08d' $(((STAMP + $1) % 100000000)))"; }
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "rapp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"주기앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "rapp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
staff_code=$(call POST "$S/invites" "$owner" | field "['code']")
staff=$(login "rapp-staff-$STAMP" | field "['access_token']")
staff_req="{\"code\":\"$staff_code\"}"
call POST /v1/invites/accept "$staff" "$staff_req" >/dev/null
menu_req='{"name":"주기 확인 미용","default_duration_minutes":60,"price":35000}'
priced=$(call POST "$S/menus" "$owner" "$menu_req" | field "['menu_id']")

family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
read -r kong_owner kong <<<"$(family 김민지 "$(phone 0)" 콩이)"
read -r dubu_owner dubu <<<"$(family 박두부 "$(phone 1)" 두부)"
read -r bori_owner bori <<<"$(family 이보리 "$(phone 2)" 보리)"
read -r mango_owner mango <<<"$(family 최망고 "$(phone 3)" 망고)"

visit() { local body="{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"${4:+,\"menu_ids\":[$4]}}"; call POST "$S/visits" "$owner" "$body" | field "['visits'][0]['visit_id']"; }
move() { local body="{\"visit_ids\":[$1],\"action\":\"$2\"}"; call POST "$S/visits/transitions" "$owner" "$body" >/dev/null; }
# done_visit <고객> <아이> <며칠 뒤> <기록 본문 또는 빈 글> [메뉴] — 그날 11시에 완료까지
done_visit() { local id; id=$(visit "$1" "$2" "$(at "$3" 11)" "${5:-}"); move "$id" start; [ -n "$4" ] && call PUT "$S/visits/$id/record" "$owner" "$4" >/dev/null; move "$id" complete; echo "$id"; }

for d in -100 -65 -30; do done_visit "$kong_owner" "$kong" "$d" "" >/dev/null; done
for d in -150 -100 -50; do done_visit "$dubu_owner" "$dubu" "$d" "" >/dev/null; done
done_visit "$bori_owner" "$bori" -40 "" >/dev/null
done_visit "$mango_owner" "$mango" -1 '{"care_note":"잘 참았어요."}' "$priced" >/dev/null

# 서버의 판단을 먼저 확인한다 — 곧 1(콩이)·지남 2(보리·두부), 어제의 남은 일 결제 1·알림장 1.
counts=$(call GET "$S/revisits/counts" "$owner")
[ "$(echo "$counts" | field "['soon']") $(echo "$counts" | field "['due']")" = "1 2" ]
yday=$(call GET "$S/visits?date=$(day -1)" "$owner")
[ "$(echo "$yday" | field "['counts']['unpaid']") $(echo "$yday" | field "['counts']['report_unsent']")" = "1 1" ]
echo "--dart-define=OWNER=rapp-owner-$STAMP --dart-define=STAFF=rapp-staff-$STAMP --dart-define=KONG=$kong --dart-define=YDAY=$(day -1)"
