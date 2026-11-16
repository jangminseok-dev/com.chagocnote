#!/usr/bin/env bash
# 개발 환경에서 ⑬ 미용 주기 흐름을 게이트웨이를 거쳐 확인한다 — 방문 몇 번(콩이 35일마다·두부 50일마다·보리 한 번) →
# 반려동물 상세의 주기를 손계산과 견준다 → 다시 올 때가 된 아이의 두 묶음(곧·지남)과 수, 매출 요약의 지난 아이 수 →
# 직접 정하기·지우기 → 예약을 잡으면 빠진다 → 안내한 날 → 어제 완료한 방문의 남은 일(결제 안 적음·알림장 안 보냄)과
# 하루 마무리의 장 → 금액을 적으면 결제 완료(paid)이고 장이 줄어든다 → 보내지 않음 → 매장의 기본 간격을 바꾸면 묶음이
# 바뀐다 → 직원은 목록을 보고 설정은 403.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_revisit_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문·기록이 남는다.
# 단계 이름과 판정만 찍는다 — 안내 글은 찍지 않는다(아이 이름이 들었는지만 본다).
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
phone() { echo "010$(printf '%08d' $(((STAMP + $1) % 100000000)))"; }
# day <며칠 뒤> — 서울의 그 날짜. at <며칠 뒤> <시> — 그 날 그 시각.
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

YDAY="$(day -1)"; TODAY="$(day 0)"

# 1. 매장·사장·직원·가족 넷
op=$(login "rflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"주기흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "rflow-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
staff_code=$(call POST "$S/invites" "$owner" | field "['code']")
staff=$(login "rflow-staff-$STAMP" | field "['access_token']")
staff_req="{\"code\":\"$staff_code\"}"
call POST /v1/invites/accept "$staff" "$staff_req" >/dev/null
# family <이름> <번호> <아이 이름> — "고객ID 아이ID"
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
read -r kong_owner kong <<<"$(family 김민지 "$(phone 0)" 콩이)"
read -r dubu_owner dubu <<<"$(family 박두부 "$(phone 1)" 두부)"
read -r bori_owner bori <<<"$(family 이보리 "$(phone 2)" 보리)"
read -r mango_owner mango <<<"$(family 최망고 "$(phone 3)" 망고)"

# visit <고객> <아이> <시각> — 예약하고 방문 ID 를 낸다. move <방문> <행동>. record <방문> <본문>.
visit() { local body="{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"}"; call POST "$S/visits" "$owner" "$body" | field "['visits'][0]['visit_id']"; }
move() { local body="{\"visit_ids\":[$1],\"action\":\"$2\"}"; call POST "$S/visits/transitions" "$owner" "$body" >/dev/null; }
record() { call PUT "$S/visits/$1/record" "$owner" "$2" >/dev/null; }
# done_visit <고객> <아이> <며칠 뒤> <기록 본문 또는 빈 글> — 그날 11시에 완료까지
done_visit() { local id; id=$(visit "$1" "$2" "$(at "$3" 11)"); move "$id" start; [ -n "$4" ] && record "$id" "$4"; move "$id" complete; echo "$id"; }

for d in -100 -65 -30; do done_visit "$kong_owner" "$kong" "$d" "" >/dev/null; done     # 35일마다 → 5주, 다음 5일 뒤
for d in -150 -100 -50; do done_visit "$dubu_owner" "$dubu" "$d" "" >/dev/null; done    # 50일마다 → 7주, 다음 어제
done_visit "$bori_owner" "$bori" -40 "" >/dev/null                                      # 한 번 → 기본 4주로 어림, 12일 지남
expect "1 콩이 셋·두부 셋·보리 하나의 완료 방문을 만들었다" "$(call GET "$S/pets/$kong" "$owner" | field "['revisit']['interval_count']")" "2"

# 2. 반려동물 상세의 주기 — 손계산(35·35일의 가운데 35일 = 5주, 마지막 방문 + 35일)
rv() { call GET "$S/pets/$1" "$owner" | python3 -c "import json,sys; r=json.load(sys.stdin)['revisit']; print(r['cycle_weeks'], r['cycle_source'], r['last_interval_weeks'], r['due_date'], r['estimated'], r['has_upcoming'])"; }
expect "2 콩이는 계산한 5주, 다음은 5일 뒤" "$(rv "$kong")" "5 computed 5 $(day 5) False False"
expect "2 두부는 50일 → 7주, 다음은 어제" "$(rv "$dubu")" "7 computed 7 $YDAY False False"
expect "2 보리는 한 번뿐이라 매장의 기본 4주로 어림한다" "$(rv "$bori")" "4 none None $(day -12) True False"

# 3. 다시 올 때가 된 아이 — 곧·지남, 수, 매출 요약의 지난 아이 수
R="$S/revisits"
names() { python3 -c "import json,sys; print([i['pet']['name'] for i in json.load(sys.stdin)['items']])"; }
counts() { call GET "$R/counts" "$1" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['soon'], d['due'])"; }
expect "3 곧 — 콩이" "$(call GET "$R?bucket=soon" "$owner" | names)" "['콩이']"
expect "3 지남 — 오래 지난 순(보리 12일, 두부 1일)" "$(call GET "$R?bucket=due" "$owner" | names)" "['보리', '두부']"
expect "3 수는 목록과 같다" "$(counts "$owner")" "1 2"
expect "3 매출 요약의 다시 올 때가 지난 아이는 지남의 수다" "$(call GET "$S/sales/summary?span=month" "$owner" | field "['due_pet_count']")" "2"
expect "3 안내 글에 아이 이름과 미용한 뒤 지난 주(30일 → 4주)가 들었다(글은 찍지 않는다)" "$(call GET "$R?bucket=soon" "$owner" | python3 -c "import json,sys; m=json.load(sys.stdin)['items'][0]['message']; print('콩이' in m and '4주' in m)")" "True"
expect "3 직원도 목록을 본다" "$(status GET "$R?bucket=due" "$staff")" "200"

# 4. 직접 정하기 — 콩이를 3주로 정하면 지남(9일 지남)으로, 지우면 다시 곧
cycle_req='{"weeks":3}'
expect "4 콩이의 주기를 3주로 정한다" "$(status PUT "$S/pets/$kong/grooming-cycle" "$owner" "$cycle_req")" "204"
expect "4 직접 정한 주기가 앞선다" "$(rv "$kong")" "3 manual 5 $(day -9) False False"
expect "4 콩이가 지남으로 옮겼다(보리 · 콩이 · 두부)" "$(call GET "$R?bucket=due" "$owner" | names)" "['보리', '콩이', '두부']"
expect "4 53주는 422" "$(status PUT "$S/pets/$kong/grooming-cycle" "$owner" '{"weeks":53}')" "422"
expect "4 지우면 계산한 주기로 돌아간다" "$(status DELETE "$S/pets/$kong/grooming-cycle" "$owner")" "204"
expect "4 콩이는 다시 곧" "$(counts "$owner")" "1 2"

# 5. 예약을 잡으면 빠진다 — 두부를 사흘 뒤로
visit "$dubu_owner" "$dubu" "$(at 3 11)" >/dev/null
expect "5 앞날 예약이 있는 두부는 목록에 없다" "$(call GET "$R?bucket=due" "$owner" | names)" "['보리']"
expect "5 상세에도 앞날 예약이 보인다" "$(rv "$dubu" | cut -d' ' -f6)" "True"

# 6. 안내한 날 — 보리에게 안내했다고 적는다
expect "6 안내한 날을 적는다" "$(status PUT "$S/pets/$bori/revisit-nudge" "$owner")" "204"
expect "6 목록의 보리에 오늘이 안내한 날로 보인다" "$(call GET "$R?bucket=due" "$owner" | field "['items'][0]['nudged_on']")" "$TODAY"

# 7. 남은 일과 하루 마무리 — 어제 망고의 완료 방문(기록에 케어 노트만)
mango_visit=$(done_visit "$mango_owner" "$mango" -1 '{"care_note":"잘 참았어요."}')
W="$S/days/$YDAY/wrap-up"
kinds() { call GET "$W" "$1" | python3 -c "import json,sys; print([c['kind'] for c in json.load(sys.stdin)['cards']])"; }
day_counts() { call GET "$S/visits?date=$YDAY" "$owner" | python3 -c "import json,sys; c=json.load(sys.stdin)['counts']; print(c['unpaid'], c['report_unsent'])"; }
expect "7 어제 하루 머리 — 결제 안 적음 1 · 알림장 안 보냄 1" "$(day_counts)" "1 1"
expect "7 달력의 어제 칸에도 같은 수" "$(call GET "$S/visits/calendar?month=${YDAY:0:7}" "$owner" | python3 -c "import json,sys; d=[x for x in json.load(sys.stdin)['days'] if x['date']=='$YDAY'][0]; print(d['unpaid_count'], d['report_unsent_count'])")" "1 1"
expect "7 하루 마무리의 장은 결제 → 알림장 차례다(직원도)" "$(kinds "$staff")" "['unpaid', 'report_unsent']"
expect "7 결제 장의 수단은 아직 근거가 없어 비어 있다" "$(call GET "$W" "$owner" | field "['cards'][0]['prefill']['payment_method']")" "None"

# 8. 금액을 적으면 결제 완료이고 장이 줄어든다 → 보내지 않음이면 장이 없다
version=$(call GET "$S/visits/$mango_visit" "$owner" | field "['record']['version']")
paid_req="{\"care_note\":\"잘 참았어요.\",\"total_amount\":35000,\"payment_method\":\"card\",\"version\":$version}"
record "$mango_visit" "$paid_req"
expect "8 어제 하루의 줄에 결제 완료가 붙는다" "$(call GET "$S/visits?date=$YDAY" "$owner" | field "['items'][0]['marks']")" "['paid']"
expect "8 하루 마무리에는 알림장 장만 남는다" "$(kinds "$owner")" "['report_unsent']"
expect "8 보내지 않음으로 넘긴다" "$(status PUT "$S/visits/$mango_visit/report-skip" "$staff")" "204"
expect "8 하루 마무리가 비었다" "$(kinds "$owner")" "[]"
expect "8 하루 머리의 남은 일도 0 이다" "$(day_counts)" "0 0"
expect "8 방문 상세에서 되돌린다" "$(status DELETE "$S/visits/$mango_visit/report-skip" "$owner")" "204"
expect "8 되돌리면 알림장 장이 돌아온다" "$(kinds "$owner")" "['report_unsent']"
expect "8 앞날의 하루 마무리는 비어 있다" "$(call GET "$S/days/$(day 3)/wrap-up" "$owner" | field "['cards']")" "[]"

# 9. 매장의 값 — 기본 간격을 8주로 바꾸면 보리(어림)는 아직 때가 아니다. 직원은 바꾸지 못한다.
settings_req='{"default_cycle_weeks":8}'
expect "9 직원은 다시 올 때의 설정을 바꾸지 못한다" "$(status PUT "$S/revisit-settings" "$staff" "$settings_req")" "403"
expect "9 사장이 기본 간격을 8주로 바꾼다" "$(call PUT "$S/revisit-settings" "$owner" "$settings_req" | field "['default_cycle_weeks']")" "8"
expect "9 보리가 지남에서 빠졌다" "$(counts "$owner")" "1 0"
expect "9 로그인 없이는 401" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE$R/counts")" "401"
echo "전체 흐름 확인 완료"
