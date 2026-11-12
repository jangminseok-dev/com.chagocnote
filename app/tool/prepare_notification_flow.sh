#!/usr/bin/env bash
# ⑥-2 시뮬레이터 흐름의 준비물 — 매장 둘.
#   매장 A(SHOP): 사장·직원, 채널 연동과 템플릿 승인까지 끝낸 매장. 보호자 둘 — 보통 번호(두부)와 끝 네
#     자리가 0000 인 번호(초코, dev 가짜 게이트웨이의 영구 실패). 모레 예약 둘(VISIT_OK·VISIT_FAIL)과
#     어제 완료한 방문 하나(VISIT_DONE, 케어 메모가 있는 기록 — 알림장 보내기용).
#   매장 B(SHOP_NEW): 사장만. 연동하지 않는다 — 흐름이 앱에서 연동 화면을 밟는다.
# infra/ 에서 실행(bash ../app/tool/prepare_notification_flow.sh). 개발 스택이 떠 있어야 한다(운영자 지정과
# 템플릿 승인을 backend 컨테이너에서 한다). dev 는 가짜 게이트웨이라 실제 발송이 없다.
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 토큰·보호자 번호·알림장 주소는 찍지 않는다(ADMIN_PHONE 은 실행 시각으로 만든 가짜 번호다).
# 개발 DB 에 확인용 매장·유저·고객·방문·알림 줄이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE_OK="010$(printf '%04d' $((STAMP % 10000)))1234"
PHONE_FAIL="010$(printf '%04d' $((STAMP % 10000)))0000"
ADMIN_PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# family <이름> <번호> <반려동물 이름> — 보호자와 반려동물을 등록하고 "customer_id pet_id" 를 낸다.
family() {
  local registered; registered=$(call POST "$S/customers" "$owner_token" "{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
  echo "$(echo "$registered" | field "['customer']['customer_id']") $(echo "$registered" | field "['pets'][0]['pet_id']")"
}
# book <customer_id> <pet_id> <며칠 뒤> <시> — 예약하고 visit_id 를 낸다.
book() {
  call POST "$S/visits" "$owner_token" "{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$(at "$3" "$4")\",\"menu_ids\":[$bath]}" \
    | field "['visits'][0]['visit_id']"
}

op=$(login "ntflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null

# --- 매장 A: 연동·승인까지 ---
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림톡앱-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "ntflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "ntflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
bath=$(call GET "$S/menus" "$owner_token" | field "['items'][0]['menu_id']")

# 본문은 변수로 먼저 만든다 — 맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 중괄호 확장으로 쪼갠다.
token_req="{\"search_id\":\"ntflow-$STAMP\",\"admin_phone\":\"$ADMIN_PHONE\",\"category_code\":\"003001\"}"
link_req="${token_req%\}},\"token\":\"000000\"}"
[ "$(call POST "$S/notification/channel/token" "$owner_token" "$token_req" | field "['status']")" = token_requested ]
[ "$(call POST "$S/notification/channel" "$owner_token" "$link_req" | field "['channel']['status']")" = linked ]
docker compose exec -T backend python scripts/reregister_templates.py --refresh --shop "$shop_id" >/dev/null
[ "$(call GET "$S/notification" "$owner_token" | field "['templates'][0]['status']")" = approved ]

read -r ok_customer ok_pet <<<"$(family 김보호 "$PHONE_OK" 두부)"
read -r fail_customer fail_pet <<<"$(family 박실패 "$PHONE_FAIL" 초코)"
# 어제 11시 예약을 시작하고 기록을 적은 뒤 완료한다 — 연동 뒤라 다음 예약 제안은 꺼져 있고(기본값) 줄이 없다.
visit_done=$(book "$ok_customer" "$ok_pet" -1 11)
call POST "$S/visits/transitions" "$owner_token" "{\"visit_ids\":[$visit_done],\"action\":\"start\"}" >/dev/null
call PUT "$S/visits/$visit_done/record" "$owner_token" "{\"weight_kg\":3.4,\"care_note\":\"눈물 자국을 닦았어요.\",\
\"payment_method\":\"card\",\"total_amount\":30000,\"items\":[{\"menu_id\":$bath,\"amount\":30000}],\"media\":[]}" >/dev/null
completed=$(call POST "$S/visits/transitions" "$owner_token" "{\"visit_ids\":[$visit_done],\"action\":\"complete\"}")
[ "$(echo "$completed" | field "['visits'][0]['status']")" = completed ]
# 모레 예약 둘 — 접수 안내가 바로 나가고(초코는 영구 실패) 전날 리마인드가 예정된다.
visit_ok=$(book "$ok_customer" "$ok_pet" 2 14)
visit_fail=$(book "$fail_customer" "$fail_pet" 2 15)

# --- 매장 B: 연동 전 ---
shop_new=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림톡새매장-$STAMP\"}")
new_code=$(echo "$shop_new" | field "['owner_invite_code']")
new_token=$(login "ntflow-new-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$new_token" "{\"code\":\"$new_code\"}" >/dev/null

echo "--dart-define=SHOP=$shop_id --dart-define=VISIT_OK=$visit_ok --dart-define=VISIT_FAIL=$visit_fail --dart-define=VISIT_DONE=$visit_done\
 --dart-define=OWNER=ntflow-owner-$STAMP --dart-define=STAFF=ntflow-staff-$STAMP --dart-define=OWNER_NEW=ntflow-new-$STAMP\
 --dart-define=CHANNEL=ntflow-app-$STAMP --dart-define=ADMIN_PHONE=$ADMIN_PHONE"
