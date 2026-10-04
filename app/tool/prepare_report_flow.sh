#!/usr/bin/env bash
# ⑤-3 시뮬레이터 흐름의 준비물 — 매장·사장·직원·고객(두부 3.2kg)·어제 완료한 방문 하나와 그 기록
# (케어 메모, 진짜 JPEG 사진 둘 — 후 하나는 밝은 회색, 전 하나는 어두운 회색).
# infra/ 에서 실행(bash ../app/tool/prepare_report_flow.sh). 개발 스택이 떠 있어야 한다(운영자 지정을 backend 컨테이너에서 한다).
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 토큰·서명 주소는 찍지 않는다.
# 개발 DB·버킷에 확인용 매장·유저·고객·방문·사진이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
# 30×40 JPEG 둘. 표시용·썸네일에도 그대로 올린다 — 앱과 보호자 웹이 실제로 그릴 수 있는 그림이면 된다.
AFTER_JPEG='/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYyLjI4LjEwMgD/2wBDAAgYGBwYHCEhISEhISckJygoKCcnJycoKCgrKyszMzMrKysoKCsrMDAzMzc5NzQ0MzQ5OTw8PEhIRUVUVFdnZ3z/xABLAAEBAAAAAAAAAAAAAAAAAAAABwEBAAAAAAAAAAAAAAAAAAAAABABAAAAAAAAAAAAAAAAAAAAABEBAAAAAAAAAAAAAAAAAAAAAP/AABEIACgAHgMBIgACEQADEQD/2gAMAwEAAhEDEQA/ALQAAAAAAAAAAAD/2Q=='
BEFORE_JPEG='/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYyLjI4LjEwMgD/2wBDAAgYGBwYHCEhISEhISckJygoKCcnJycoKCgrKyszMzMrKysoKCsrMDAzMzc5NzQ0MzQ5OTw8PEhIRUVUVFdnZ3z/xABLAAEBAAAAAAAAAAAAAAAAAAAABwEBAAAAAAAAAAAAAAAAAAAAABABAAAAAAAAAAAAAAAAAAAAABEBAAAAAAAAAAAAAAAAAAAAAP/AABEIACgAHgMBIgACEQADEQD/2gAMAwEAAhEDEQA/AJ+AAAAAAAAAAAD/2Q=='
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# photo <base64 JPEG> — 사진 하나를 발급·올리기 셋·확인까지 마치고 media_id 를 낸다. 서명 주소로 저장소에 바로 올린다.
photo() {
  local file; file=$(mktemp); echo "$1" | base64 -d > "$file"
  local issued; issued=$(call POST "$S/media/uploads" "$owner_token" \
    "{\"kind\":\"photo\",\"content_type\":\"image/jpeg\",\"byte_size\":$(wc -c < "$file" | tr -d ' '),\"width\":30,\"height\":40}")
  local name
  for name in original display thumb; do
    [ "$(curl -s -o /dev/null -w '%{http_code}' -X PUT "$(echo "$issued" | field "['puts']['$name']")" \
      -H 'Content-Type: image/jpeg' --data-binary "@$file")" = 200 ]
  done
  rm -f "$file"
  local id; id=$(echo "$issued" | field "['media_id']")
  [ "$(call POST "$S/media/$id/confirm" "$owner_token" | field "['status']")" = ready ]
  echo "$id"
}

op=$(login "nflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림장앱-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "nflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "nflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
bath=$(call GET "$S/menus" "$owner_token" | field "['items'][0]['menu_id']")
registered=$(call POST "$S/customers" "$owner_token" "{\"customer\":{\"name\":\"김보호\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"두부\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); pet=$(echo "$registered" | field "['pets'][0]['pet_id']")
# 어제 11시 예약을 시작하고 기록을 적은 뒤 완료한다 — 실행 시각과 상관없이 자정을 넘기지 않는다.
visit=$(call POST "$S/visits" "$owner_token" "{\"customer_id\":$customer_id,\"pet_ids\":[$pet],\"starts_at\":\"$(at -1 11)\",\"menu_ids\":[$bath]}" \
  | field "['visits'][0]['visit_id']")
call POST "$S/visits/transitions" "$owner_token" "{\"visit_ids\":[$visit],\"action\":\"start\"}" >/dev/null
after=$(photo "$AFTER_JPEG"); before=$(photo "$BEFORE_JPEG")
saved=$(call PUT "$S/visits/$visit/record" "$owner_token" "{\"weight_kg\":3.4,\"care_note\":\"눈물 자국을 닦았어요.\",\
\"payment_method\":\"card\",\"total_amount\":30000,\"items\":[{\"menu_id\":$bath,\"amount\":30000}],\
\"media\":[{\"media_id\":$after,\"phase\":\"after\",\"sort_order\":0},{\"media_id\":$before,\"phase\":\"before\",\"sort_order\":0}]}")
[ "$(echo "$saved" | field "['media'].__len__()")" = 2 ]
completed=$(call POST "$S/visits/transitions" "$owner_token" "{\"visit_ids\":[$visit],\"action\":\"complete\"}")
[ "$(echo "$completed" | field "['visits'][0]['status']")" = completed ]
echo "--dart-define=SHOP=$shop_id --dart-define=VISIT=$visit --dart-define=OWNER=nflow-owner-$STAMP --dart-define=STAFF=nflow-staff-$STAMP"
