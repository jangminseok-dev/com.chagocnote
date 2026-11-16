#!/usr/bin/env bash
# ⑫-3 시뮬레이터 흐름(archive_flow_test.dart)의 준비물 — 매장·사장·고객(콩이)·어제 완료한 방문과 기록(몸무게),
# 그 방문의 알림장을 보내고 보호자 계정(웹 세션)이 받은 링크로 이은 뒤, 보호자가 가족 한 명을 초대해 잇는다.
# 매장에서 "보호자 계정 연결됨 · 가족 1명"이 보이는 상태다.
# infra/ 에서 실행(bash ../app/tool/prepare_archive_flow.sh). 개발 스택이 떠 있어야 한다(운영자 지정을 backend 컨테이너에서 한다).
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 알림장 토큰·주소·초대 코드와 액세스 토큰은 찍지 않는다.
# 개발 DB 에 확인용 매장·유저·고객·방문·알림장·연결이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
web_login() { local body="{\"provider\":\"dev\",\"token\":\"$1\",\"session\":\"web\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "arch-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"모아보기앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "arch-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
bath=$(call GET "$S/menus" "$owner_token" | field "['items'][0]['menu_id']")
family_req="{\"customer\":{\"name\":\"김사진\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"비숑\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2022,\"weight_kg\":5.0,\"no_known_conditions\":true}}"
registered=$(call POST "$S/customers" "$owner_token" "$family_req")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); pet=$(echo "$registered" | field "['pets'][0]['pet_id']")
# 어제 11시 예약을 시작하고 기록(몸무게)을 적은 뒤 완료한다 — 실행 시각과 상관없이 자정을 넘기지 않는다.
visit_req="{\"customer_id\":$customer_id,\"pet_ids\":[$pet],\"starts_at\":\"$(at -1 11)\",\"menu_ids\":[$bath]}"
visit=$(call POST "$S/visits" "$owner_token" "$visit_req" | field "['visits'][0]['visit_id']")
start_req="{\"visit_ids\":[$visit],\"action\":\"start\"}"
call POST "$S/visits/transitions" "$owner_token" "$start_req" >/dev/null
record_req="{\"weight_kg\":5.1,\"care_note\":\"콩이가 잘 참았어요.\",\"payment_method\":\"card\",\"total_amount\":30000,\"items\":[{\"menu_id\":$bath,\"amount\":30000}],\"media\":[]}"
call PUT "$S/visits/$visit/record" "$owner_token" "$record_req" >/dev/null
complete_req="{\"visit_ids\":[$visit],\"action\":\"complete\"}"
call POST "$S/visits/transitions" "$owner_token" "$complete_req" >/dev/null

# 알림장을 보내고 보호자 계정이 받은 링크로 잇는다. 토큰은 헤더로만 넘기고 찍지 않는다.
send_req='{"hidden_media_ids":[],"show_review":true}'
url=$(call PUT "$S/visits/$visit/report" "$owner_token" "$send_req" | field "['link']['url']")
report_token="${url##*/}"
[ "${#report_token}" = 43 ]
guardian_token=$(web_login "arch-guardian-$STAMP" | field "['access_token']")
link_id=$(curl -s -X POST "$BASE/v1/me/guardian/links" -H "Authorization: Bearer $guardian_token" -H "X-Report-Token: $report_token" | field "['link_id']")

# 보호자가 가족 한 명을 초대하고, 그 가족이 잇는다. 초대 코드는 헤더로만 넘기고 찍지 않는다.
code=$(call POST "/v1/me/guardian/links/$link_id/family-invites" "$guardian_token" | field "['code']")
[ "${#code}" = 43 ]
family_token=$(web_login "arch-family-$STAMP" | field "['access_token']")
joined=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/me/guardian/family-links" -H "Authorization: Bearer $family_token" -H "X-Family-Invite: $code")
[ "$joined" = 201 ]
link=$(call GET "$S/customers/$customer_id/guardian-link" "$owner_token")
[ "$(echo "$link" | field "['family_count']")" = 1 ]
# 이은 날(매장 시간대)의 월·일 — 흐름이 화면의 글자와 견준다.
linked_at=$(echo "$link" | field "['linked_at']")
month=$((10#${linked_at:5:2})); day=$((10#${linked_at:8:2}))
echo "--dart-define=SHOP=$shop_id --dart-define=CUSTOMER=$customer_id --dart-define=PET=$pet --dart-define=VISIT=$visit --dart-define=MONTH=$month --dart-define=DAY=$day --dart-define=OWNER=arch-owner-$STAMP"
