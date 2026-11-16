#!/usr/bin/env bash
# ⑪-A3 시뮬레이터 흐름의 준비물 — 매장·사장, 보호자 둘과 노령 아이 둘("초코" — 지병(심장 질환), "라떼"), 둘 다 내일 예약.
# 초코는 그 자리에서 서명받고(현장 서명), 라떼에게는 동의서 링크를 보낸다.
# infra/ 에서 실행(bash ../app/tool/prepare_consent_flow.sh). 개발 스택이 떠 있어야 한다.
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 액세스 토큰·전화번호·링크 주소는 찍지 않는다.
# 개발 DB 에 확인용 매장·유저·고객·방문이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
phone() { echo "010$(printf '%08d' $(((STAMP + $1) % 100000000)))"; }
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "capp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"동의서앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "capp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"

OLD_YEAR=$(( $(TZ=Asia/Seoul date +%Y) - 12 ))
pet_body() {   # <이름> <지병 JSON 배열>
  local none=true; [ "$2" = "[]" ] || none=false
  echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":$OLD_YEAR,\"weight_kg\":3.2,\"no_known_conditions\":$none,\"conditions\":$2}"
}
# family <보호자 이름> <번호> <반려동물 본문> <예약 시각> — "아이ID 방문ID"
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":false},\"pet\":$3}"
  local registered; registered=$(call POST "$S/customers" "$owner_token" "$body")
  local customer; customer=$(echo "$registered" | field "['customer']['customer_id']")
  local pet; pet=$(echo "$registered" | field "['pets'][0]['pet_id']")
  local visit_req="{\"customer_id\":$customer,\"pet_ids\":[$pet],\"starts_at\":\"$(day 1)T$4:00:00+09:00\"}"
  echo "$pet $(call POST "$S/visits" "$owner_token" "$visit_req" | field "['visits'][0]['visit_id']")"
}
HEART='{"type_code":"heart_disease","custom_label":null,"note":"약 복용 중"}'
read -r choco choco_visit <<<"$(family 김초코 "$(phone 0)" "$(pet_body 초코 "[$HEART]")" 11)"
read -r latte latte_visit <<<"$(family 박라떼 "$(phone 1)" "$(pet_body 라떼 "[]")" 14)"
echo "--dart-define=SHOP=$shop_id --dart-define=PET=$choco --dart-define=VISIT=$choco_visit --dart-define=PET2=$latte --dart-define=VISIT2=$latte_visit --dart-define=OWNER=capp-owner-$STAMP"
