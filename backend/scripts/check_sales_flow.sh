#!/usr/bin/env bash
# 개발 환경에서 매출 통계 흐름을 게이트웨이를 거쳐 확인한다 — 어제의 완료 방문 넷(카드·현금·이체 + 금액 없는 하나, 한 건은
# 항목 합이 총액과 다르다)과 노쇼 하나, 지난달 첫날의 완료 방문 하나를 만들고 → 요약(월)의 숫자를 손으로 센 값과 견준다
# (매출·방문 수·평균·결제 수단별·메뉴별·조정·처음/다시 온 아이·노쇼·금액 없는 수·앞 기간의 매출) → 일·주 요약 → 이어지는
# 방문 목록 넷 → 금액을 채우면 매출이 는다 → 월 목표 정하기·읽기·요약에 보임·지우기 → 남은 예약 → 직원은 403.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_sales_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문·기록이 남는다.
# 요약은 "어제"를 anchor 로 읽는다 — 달의 첫날이나 월요일에 돌려도 같은 숫자가 나온다. 단계 이름과 판정만 찍는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE_A="010$(printf '%08d' $((STAMP % 100000000)))"
PHONE_B="010$(printf '%08d' $(((STAMP + 1) % 100000000)))"
# day <며칠 뒤> — 서울의 그 날짜. at <며칠 뒤> <시> — 그 날 그 시각. prev_first — 어제가 든 달의 앞 달 1일.
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }
prev_first() { TZ=Asia/Seoul python3 -c "import datetime as d; y=d.date.today()-d.timedelta(days=1); print((y.replace(day=1)-d.timedelta(days=1)).replace(day=1))"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

YDAY="$(day -1)"; TODAY="$(day 0)"; PREV="$(prev_first)"

# 1. 매장·사장·직원·고객 둘
op=$(login "sflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"매출흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "sflow-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
staff_code=$(call POST "$S/invites" "$owner" | field "['code']")
staff=$(login "sflow-staff-$STAMP" | field "['access_token']")
staff_req="{\"code\":\"$staff_code\"}"
call POST /v1/invites/accept "$staff" "$staff_req" >/dev/null
bath=$(call GET "$S/menus" "$owner" | field "['items'][0]['menu_id']")
# family <이름> <번호> <아이 이름> — "고객ID 아이ID"
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
read -r kong_owner kong <<<"$(family 김민지 "$PHONE_A" 콩이)"
read -r dubu_owner dubu <<<"$(family 박두부 "$PHONE_B" 두부)"

# visit <고객> <아이> <시각> — 예약하고 방문 ID 를 낸다. move <방문> <행동>. record <방문> <본문>.
visit() { local body="{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"}"; call POST "$S/visits" "$owner" "$body" | field "['visits'][0]['visit_id']"; }
move() { local body="{\"visit_ids\":[$1],\"action\":\"$2\"}"; call POST "$S/visits/transitions" "$owner" "$body" >/dev/null; }
record() { call PUT "$S/visits/$1/record" "$owner" "$2" >/dev/null; }
# done_visit <고객> <아이> <시각> <기록 본문 또는 빈 글> — 완료까지
done_visit() { local id; id=$(visit "$1" "$2" "$3"); move "$id" start; [ -n "$4" ] && record "$id" "$4"; move "$id" complete; echo "$id"; }

card_rec="{\"payment_method\":\"card\",\"total_amount\":30000,\"items\":[{\"menu_id\":$bath,\"amount\":30000}]}"
cash_rec="{\"payment_method\":\"cash\",\"total_amount\":50000,\"items\":[{\"menu_id\":$bath,\"amount\":45000}]}"
transfer_rec='{"payment_method":"transfer","total_amount":20000}'
old_rec='{"payment_method":"card","total_amount":40000}'
v_card=$(done_visit "$kong_owner" "$kong" "$(at -1 10)" "$card_rec")
v_cash=$(done_visit "$dubu_owner" "$dubu" "$(at -1 12)" "$cash_rec")
v_transfer=$(done_visit "$kong_owner" "$kong" "$(at -1 14)" "$transfer_rec")
v_blank=$(done_visit "$dubu_owner" "$dubu" "$(at -1 16)" "")
v_noshow=$(visit "$kong_owner" "$kong" "$(at -1 17)"); move "$v_noshow" no_show
done_visit "$kong_owner" "$kong" "${PREV}T11:00:00+09:00" "$old_rec" >/dev/null   # 지난달 첫날 — 콩이는 다시 온 아이가 된다
expect "1 어제 완료 방문 넷과 노쇼 하나, 지난달 방문 하나를 만들었다" "$([ "$v_blank" -gt 0 ] && echo 예)" "예"

# 2. 요약(월) — 손으로 센 값과 견준다
SUM="$S/sales/summary"
m=$(call GET "$SUM?span=month&anchor=$YDAY" "$owner")
expect "2 매출은 30,000 + 50,000 + 20,000 이다" "$(echo "$m" | field "['revenue']")" "100000"
expect "2 완료 방문은 넷이고 금액을 적은 것은 셋이다" "$(echo "$m" | field "['visit_count']") $(echo "$m" | field "['priced_count']")" "4 3"
expect "2 한 번에 평균은 원 단위에서 버린다" "$(echo "$m" | field "['average']")" "33333"
expect "2 금액을 적지 않은 완료 방문이 하나다" "$(echo "$m" | field "['unrecorded_count']")" "1"
expect "2 결제 수단별" "$(echo "$m" | python3 -c "import json,sys; print([(p['method'],p['amount']) for p in json.load(sys.stdin)['payments']])")" "[('card', 30000), ('cash', 50000), ('transfer', 20000)]"
expect "2 메뉴는 항목 합 75,000(2건)이고 조정이 25,000 이다" "$(echo "$m" | python3 -c "import json,sys; print([(x['name'] if x['menu_id'] is None else 'menu',x['amount'],x['count']) for x in json.load(sys.stdin)['menus']])")" "[('menu', 75000, 2), ('조정', 25000, 0)]"
expect "2 결제 수단 합 = 메뉴 합 = 칸의 합 = 매출" "$(echo "$m" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(p['amount'] for p in d['payments'])==sum(x['amount'] for x in d['menus'])==sum(b['revenue'] for b in d['buckets'])==sum(d['weekdays'])==d['revenue'])")" "True"
expect "2 아이는 둘 — 두부는 처음, 콩이는 다시" "$(echo "$m" | python3 -c "import json,sys; p=json.load(sys.stdin)['pets']; print(p['count'],p['new_count'],p['returning_count'],[x['name'] for x in p['new']],[x['name'] for x in p['returning']])")" "2 1 1 ['두부'] ['콩이']"
expect "2 노쇼가 하나다" "$(echo "$m" | field "['bookings']['no_show']")" "1"
expect "2 앞 기간(지난달)의 매출은 40,000 이다" "$(echo "$m" | field "['compare']['previous']['revenue']")" "40000"
expect "2 어제 칸에 그날의 매출과 아이들이 있다" "$(echo "$m" | python3 -c "import json,sys; b=[x for x in json.load(sys.stdin)['buckets'] if x['key']=='$YDAY'][0]; print(b['revenue'],b['visit_count'],[p['name'] for p in b['pets']])")" "100000 4 ['콩이', '두부']"
expect "2 알림장은 아직 보내지 않았다" "$(echo "$m" | python3 -c "import json,sys; r=json.load(sys.stdin)['report']; print(r['completed'],r['sent'],r['opened'])")" "4 0 0"

# 3. 일·주로 봐도 같은 돈이다
expect "3 어제 하루의 매출" "$(call GET "$SUM?span=day&anchor=$YDAY" "$owner" | field "['revenue']")" "100000"
expect "3 어제가 든 주의 매출" "$(call GET "$SUM?span=week&anchor=$YDAY" "$owner" | field "['revenue']")" "100000"
expect "3 그제 하루는 비어 있다" "$(call GET "$SUM?span=day&anchor=$(day -2)" "$owner" | field "['revenue']")" "0"

# 4. 이어지는 방문 목록
L="$S/sales/visits?span=day&anchor=$YDAY"
ids() { python3 -c "import json,sys; print([i['visit_id'] for i in json.load(sys.stdin)['items']])"; }
expect "4 금액을 적지 않은 완료 방문" "$(call GET "$L&filter=unrecorded" "$owner" | ids)" "[$v_blank]"
expect "4 노쇼한 방문" "$(call GET "$L&filter=no_show" "$owner" | ids)" "[$v_noshow]"
expect "4 취소한 방문은 없다" "$(call GET "$L&filter=canceled" "$owner" | ids)" "[]"
expect "4 그 메뉴를 한 방문은 최신순 둘이다" "$(call GET "$L&filter=menu&menu_id=$bath" "$owner" | ids)" "[$v_cash, $v_card]"
expect "4 메뉴로 거르는데 메뉴가 없으면 422" "$(status GET "$L&filter=menu" "$owner")" "422"

# 5. 금액을 채우면 매출이 는다
fill='{"payment_method":"cash","total_amount":15000}'
record "$v_blank" "$fill"
m=$(call GET "$SUM?span=month&anchor=$YDAY" "$owner")
expect "5 금액을 채우면 매출이 늘고 빠진 방문이 없어진다" "$(echo "$m" | field "['revenue']") $(echo "$m" | field "['unrecorded_count']")" "115000 0"

# 6. 월 목표
G="$S/sales/goal"
goal_req='{"monthly_amount":5000000}'
expect "6 목표를 정한다" "$(call PUT "$G" "$owner" "$goal_req" | field "['monthly_amount']")" "5000000"
expect "6 목표를 읽는다" "$(call GET "$G" "$owner" | field "['monthly_amount']")" "5000000"
expect "6 이번 달 요약에 목표가 보인다" "$(call GET "$SUM?span=month&anchor=$TODAY" "$owner" | field "['goal']['monthly_amount']")" "5000000"
expect "6 지난달 요약에는 목표가 없다" "$(call GET "$SUM?span=month&anchor=$PREV" "$owner" | field "['goal']")" "None"
clear_req='{"monthly_amount":0}'
expect "6 0 을 보내면 목표가 지워진다" "$(call PUT "$G" "$owner" "$clear_req" | field "['monthly_amount']")" "None"

# 7. 남은 예약 — 내일 예약 하나. 내일이 해를 넘기는 날(12월 31일)에는 올해의 남은 예약이 아니다.
visit "$kong_owner" "$kong" "$(at 1 11)" >/dev/null
want=1; [ "$(day 1 | cut -c1-4)" = "$(day 0 | cut -c1-4)" ] || want=0
expect "7 올해의 남은 예약" "$(call GET "$SUM?span=year&anchor=$TODAY" "$owner" | field "['bookings']['remaining']")" "$want"
expect "7 다시 올 때가 지난 아이는 아직 없다" "$(call GET "$S/sales/due-pets" "$owner" | field "['items'].__len__()")" "0"

# 8. 직원은 매출을 보지 못한다
expect "8 직원의 요약은 403" "$(call GET "$SUM?span=month" "$staff" | field "['code']")" "PERMISSION_DENIED"
expect "8 직원의 방문 목록은 403" "$(status GET "$L&filter=no_show" "$staff")" "403"
expect "8 직원의 목표 정하기는 403" "$(status PUT "$G" "$staff" "$goal_req")" "403"
expect "8 로그인 없이는 401" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE$SUM?span=month")" "401"
echo "전체 흐름 확인 완료"
