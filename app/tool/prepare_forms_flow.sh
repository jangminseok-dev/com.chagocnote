#!/usr/bin/env bash
# ⑪-B 시뮬레이터 흐름의 준비물 — 매장·사장, 보호자 하나와 노령 아이 "초코"(12살, 예약 없음).
# 흐름이 예약을 잡고(보낼 것 시트) 서류 설정을 바꾼다 — 기기마다 새로 돌린다.
# infra/ 에서 실행(bash ../app/tool/prepare_forms_flow.sh). 개발 스택이 떠 있어야 한다.
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 액세스 토큰·전화번호·링크 주소는 찍지 않는다.
# 개발 DB 에 확인용 매장·유저·고객이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "fapp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"서류앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "fapp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
OLD_YEAR=$(( $(TZ=Asia/Seoul date +%Y) - 12 ))
family_req="{\"customer\":{\"name\":\"김서류\",\"phone\":\"$PHONE\",\"marketing_consent\":false},\"pet\":{\"name\":\"초코\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":$OLD_YEAR,\"weight_kg\":3.2,\"no_known_conditions\":true,\"conditions\":[]}}"
pet=$(call POST "/v1/shops/$shop_id/customers" "$owner_token" "$family_req" | field "['pets'][0]['pet_id']")
echo "--dart-define=SHOP=$shop_id --dart-define=PET=$pet --dart-define=DATE=$(day 2) --dart-define=OWNER=fapp-owner-$STAMP"
