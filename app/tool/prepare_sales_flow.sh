#!/usr/bin/env bash
# ⑧-2 시뮬레이터 흐름의 준비물 — 매장·사장·직원·고객 둘(콩이·두부), 어제의 완료 방문 넷(카드 30,000 사진 하나 /
# 현금 50,000 항목 합 45,000 사진 하나 / 계좌 20,000 / 금액 없음)과 노쇼 하나, 지난달 첫날의 완료 방문 하나,
# 내일의 예약 하나(정가 25,000 메뉴), 월 목표 500,000.
# infra/ 에서 실행(bash ../app/tool/prepare_sales_flow.sh). 개발 스택이 떠 있어야 한다(운영자 지정을 backend 컨테이너에서 한다).
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다 — 화면과 견줄 숫자는 서버의 요약에서 읽어 넘긴다.
# 토큰·서명 주소는 찍지 않는다. 개발 DB·버킷에 확인용 매장·유저·고객·방문·사진이 남는다. zsh 에서는 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE_A="010$(printf '%08d' $((STAMP % 100000000)))"
PHONE_B="010$(printf '%08d' $(((STAMP + 1) % 100000000)))"
# 30×40 JPEG 둘(밝은 회색·어두운 회색). 표시용·썸네일에도 그대로 올린다.
LIGHT_JPEG='/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYyLjI4LjEwMgD/2wBDAAgYGBwYHCEhISEhISckJygoKCcnJycoKCgrKyszMzMrKysoKCsrMDAzMzc5NzQ0MzQ5OTw8PEhIRUVUVFdnZ3z/xABLAAEBAAAAAAAAAAAAAAAAAAAABwEBAAAAAAAAAAAAAAAAAAAAABABAAAAAAAAAAAAAAAAAAAAABEBAAAAAAAAAAAAAAAAAAAAAP/AABEIACgAHgMBIgACEQADEQD/2gAMAwEAAhEDEQA/ALQAAAAAAAAAAAD/2Q=='
DARK_JPEG='/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYyLjI4LjEwMgD/2wBDAAgYGBwYHCEhISEhISckJygoKCcnJycoKCgrKyszMzMrKysoKCsrMDAzMzc5NzQ0MzQ5OTw8PEhIRUVUVFdnZ3z/xABLAAEBAAAAAAAAAAAAAAAAAAAABwEBAAAAAAAAAAAAAAAAAAAAABABAAAAAAAAAAAAAAAAAAAAABEBAAAAAAAAAAAAAAAAAAAAAP/AABEIACgAHgMBIgACEQADEQD/2gAMAwEAAhEDEQA/AJ+AAAAAAAAAAAD/2Q=='
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }
prev_first() { TZ=Asia/Seoul python3 -c "import datetime as d; y=d.date.today()-d.timedelta(days=1); print((y.replace(day=1)-d.timedelta(days=1)).replace(day=1))"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "sapp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"매출앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "sapp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
staff_code=$(call POST "$S/invites" "$owner" | field "['code']")
staff=$(login "sapp-staff-$STAMP" | field "['access_token']")
staff_req="{\"code\":\"$staff_code\"}"
call POST /v1/invites/accept "$staff" "$staff_req" >/dev/null
bath=$(call GET "$S/menus" "$owner" | field "['items'][0]['menu_id']")
menu_req='{"name":"매출 확인 미용","default_duration_minutes":60,"price":25000}'
priced=$(call POST "$S/menus" "$owner" "$menu_req" | field "['menu_id']")

family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
read -r kong_owner kong <<<"$(family 김민지 "$PHONE_A" 콩이)"
read -r dubu_owner dubu <<<"$(family 박두부 "$PHONE_B" 두부)"

# photo <base64 JPEG> — 발급·올리기 셋·확인까지 마치고 media_id 를 낸다.
photo() {
  local file; file=$(mktemp); echo "$1" | base64 -d > "$file"
  local req="{\"kind\":\"photo\",\"content_type\":\"image/jpeg\",\"byte_size\":$(wc -c < "$file" | tr -d ' '),\"width\":30,\"height\":40}"
  local issued; issued=$(call POST "$S/media/uploads" "$owner" "$req")
  local name
  for name in original display thumb; do
    [ "$(curl -s -o /dev/null -w '%{http_code}' -X PUT "$(echo "$issued" | field "['puts']['$name']")" \
      -H 'Content-Type: image/jpeg' --data-binary "@$file")" = 200 ]
  done
  rm -f "$file"
  local id; id=$(echo "$issued" | field "['media_id']")
  [ "$(call POST "$S/media/$id/confirm" "$owner" | field "['status']")" = ready ]
  echo "$id"
}
visit() { local body="{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"${4:+,\"menu_ids\":[$4]}}"; call POST "$S/visits" "$owner" "$body" | field "['visits'][0]['visit_id']"; }
move() { local body="{\"visit_ids\":[$1],\"action\":\"$2\"}"; call POST "$S/visits/transitions" "$owner" "$body" >/dev/null; }
done_visit() { local id; id=$(visit "$1" "$2" "$3"); move "$id" start; [ -n "$4" ] && call PUT "$S/visits/$id/record" "$owner" "$4" >/dev/null; move "$id" complete; echo "$id"; }

p1=$(photo "$LIGHT_JPEG"); p2=$(photo "$DARK_JPEG")
card_rec="{\"payment_method\":\"card\",\"total_amount\":30000,\"items\":[{\"menu_id\":$bath,\"amount\":30000}],\"media\":[{\"media_id\":$p1,\"phase\":\"after\",\"sort_order\":0}]}"
cash_rec="{\"payment_method\":\"cash\",\"total_amount\":50000,\"items\":[{\"menu_id\":$bath,\"amount\":45000}],\"media\":[{\"media_id\":$p2,\"phase\":\"after\",\"sort_order\":0}]}"
transfer_rec='{"payment_method":"transfer","total_amount":20000}'
old_rec='{"payment_method":"card","total_amount":40000}'
done_visit "$kong_owner" "$kong" "$(at -1 10)" "$card_rec" >/dev/null
done_visit "$dubu_owner" "$dubu" "$(at -1 12)" "$cash_rec" >/dev/null
done_visit "$kong_owner" "$kong" "$(at -1 14)" "$transfer_rec" >/dev/null
done_visit "$dubu_owner" "$dubu" "$(at -1 16)" "" >/dev/null
noshow=$(visit "$kong_owner" "$kong" "$(at -1 17)"); move "$noshow" no_show
done_visit "$kong_owner" "$kong" "$(prev_first)T11:00:00+09:00" "$old_rec" >/dev/null
visit "$kong_owner" "$kong" "$(at 1 11)" "$priced" >/dev/null
goal_req='{"monthly_amount":500000}'
call PUT "$S/sales/goal" "$owner" "$goal_req" >/dev/null

# 화면과 견줄 숫자 — 서버의 요약에서 읽는다. 어제가 지난달이면(오늘이 1일) 앱에서 ‹ 를 한 번 눌러야 한다.
YDAY="$(day -1)"; TODAY="$(day 0)"
month=$(call GET "$S/sales/summary?span=month&anchor=$YDAY" "$owner")
[ "$(echo "$month" | field "['revenue']")" = 100000 ]
year_revenue=$(call GET "$S/sales/summary?span=year&anchor=$TODAY" "$owner" | field "['revenue']")
back=0; [ "${YDAY:0:7}" = "${TODAY:0:7}" ] || back=1
echo "--dart-define=OWNER=sapp-owner-$STAMP --dart-define=STAFF=sapp-staff-$STAMP --dart-define=BACK=$back --dart-define=MONTH_REVENUE=100000 --dart-define=YEAR_REVENUE=$year_revenue"
