#!/usr/bin/env bash
# ⑪-C3 시뮬레이터 흐름의 준비물 — 매장·사장, 새 손님용 문진표 링크로 보호자가 미리 낸 답 하나("모카").
# 흐름이 그 답을 등록하고(답이 사라진다) 서류 설정을 바꾼다 — 기기마다 새로 돌린다.
# infra/ 에서 실행(bash ../app/tool/prepare_intake_flow.sh). 개발 스택이 떠 있어야 한다.
# 공개 제출은 접속 주소당 10분에 10번이다 — 한 번에 1번을 쓴다.
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 액세스 토큰·전화번호·링크 주소는 찍지 않는다.
# 개발 DB 에 확인용 매장·유저·답이 남는다. zsh 에서 변수로 받으면 ${=D} 로 펼친다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "iapp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"문진표앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "iapp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
# 새 손님용 링크 → 보호자가 로그인 없이 적어 낸다(토큰은 헤더로만).
token=$(call POST "/v1/shops/$shop_id/intake-forms" "$owner_token" '{"customer_id":null,"pet_id":null}' | python3 -c "import json,sys; print(json.load(sys.stdin)['url'].rsplit('/',1)[1])")
answer="{\"guardian\":{\"name\":\"박문진\",\"phone\":\"$PHONE\"},\"pet\":{\"name\":\"모카\",\"species\":\"dog\",\"breed\":\"푸들\",\"sex\":\"male\",\"neutered\":false,\"birth_year\":2022,\"weight_kg\":4.5,\"no_known_conditions\":true,\"conditions\":[],\"dislikes\":\"드라이기 소리\",\"style\":\"짧게\"},\"extras\":[],\"privacy_agreed\":true,\"done\":true}"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/public/form/intake" -H "X-Form-Token: $token" -H 'Content-Type: application/json' -d "$answer")
[ "$code" = "204" ] || { echo "문진표를 내지 못했다($code)" >&2; exit 1; }
echo "--dart-define=SHOP=$shop_id --dart-define=OWNER=iapp-owner-$STAMP"
