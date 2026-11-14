#!/usr/bin/env bash
# ③-B2 시뮬레이터 흐름의 준비물 — 매장·사장, 노령(15살)이고 지병(심장병, 메모 있음)이 있는 아이 "노을"과 보호자,
# 내일 11시 예약 하나. 그 예약에는 첫 방문·미용 동의·지병이 뜬다(하루 목록의 수는 2 — 지병은 세지 않는다).
# infra/ 에서 실행(bash ../app/tool/prepare_visit_checks_flow.sh). 개발 스택이 떠 있어야 한다(운영자 지정을 backend 컨테이너에서 한다).
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 액세스 토큰·전화번호는 찍지 않는다.
# 개발 DB 에 확인용 매장·유저·고객·방문이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "capp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"확인앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "capp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
OLD_YEAR=$(( $(TZ=Asia/Seoul date +%Y) - 15 ))
family_req="{\"customer\":{\"name\":\"김확인\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":{\"name\":\"노을\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":$OLD_YEAR,\"weight_kg\":3.2,\"no_known_conditions\":false,\"conditions\":[{\"type_code\":\"heart_disease\",\"custom_label\":null,\"note\":\"약 복용 중\"}]}}"
registered=$(call POST "$S/customers" "$owner_token" "$family_req")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); pet=$(echo "$registered" | field "['pets'][0]['pet_id']")
DATE=$(day 1); NEXT=$(day 2)
visit_req="{\"customer_id\":$customer_id,\"pet_ids\":[$pet],\"starts_at\":\"${DATE}T11:00:00+09:00\"}"
visit=$(call POST "$S/visits" "$owner_token" "$visit_req" | field "['visits'][0]['visit_id']")
# 준비가 맞는지 — 그 예약의 확인할 것이 첫 방문·동의·지병이다.
codes=$(call GET "$S/visits/$visit" "$owner_token" | python3 -c "import json,sys; print(','.join(c['code'] for c in json.load(sys.stdin)['checks']))")
[ "$codes" = "first_visit,consent,conditions" ]
echo "--dart-define=SHOP=$shop_id --dart-define=CUSTOMER=$customer_id --dart-define=PET=$pet --dart-define=VISIT=$visit --dart-define=DATE=$DATE --dart-define=NEXT=$NEXT --dart-define=OWNER=capp-owner-$STAMP"
