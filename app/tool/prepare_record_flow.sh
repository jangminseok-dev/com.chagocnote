#!/usr/bin/env bash
# ④-2a 시뮬레이터 흐름의 준비물 — 매장·사장·직원·고객(콩이 3.2kg)·목욕 정가 30000·오늘 미용 중 방문 둘.
# infra/ 에서 실행(bash ../app/tool/prepare_record_flow.sh). 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다.
# 개발 DB·버킷에 확인용 매장·유저·고객·방문이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "rflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"기록흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "rflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "rflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
bath=$(call GET "$S/menus" "$owner_token" | field "['items'][0]")
bath_id=$(echo "$bath" | python3 -c "import json,sys; print(eval(sys.stdin.read())['menu_id'])")
call PUT "$S/menus/$bath_id" "$owner_token" "{\"name\":\"목욕\",\"default_duration_minutes\":60,\"sort_order\":1,\"price\":30000}" >/dev/null
registered=$(call POST "$S/customers" "$owner_token" "{\"customer\":{\"name\":\"김기록\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
visit() { call POST "$S/visits" "$owner_token" "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at 0 "$1")\",\"menu_ids\":[$bath_id]}" | field "['visits'][0]['visit_id']"; }
a=$(visit 9); b=$(visit 11)
call POST "$S/visits/transitions" "$owner_token" "{\"visit_ids\":[$a],\"action\":\"start\"}" >/dev/null
call POST "$S/visits/transitions" "$owner_token" "{\"visit_ids\":[$b],\"action\":\"start\"}" >/dev/null
echo "--dart-define=SHOP=$shop_id --dart-define=VISIT_A=$a --dart-define=VISIT_B=$b --dart-define=OWNER=rflow-owner-$STAMP --dart-define=STAFF=rflow-staff-$STAMP"
