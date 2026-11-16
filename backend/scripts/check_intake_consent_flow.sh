#!/usr/bin/env bash
# 개발 환경에서 문진표 끝의 동의서(⑪-C1b)를 게이트웨이를 거쳐 확인한다 — 새 손님용 링크를 연다(동의서 구역의 글·기준) →
# 노령 아이를 서명 없이 내면 422 → 연 뒤 매장이 글을 고치면 409 → 다시 열어 서명과 함께 내면 맡아 둔다 →
# 받은 문진표 한 장에 서명 요약 → 지병을 더해 등록하면 서명이 그 아이의 동의가 되고 지병 토막만 남는다 →
# 서명 목록의 받은 길 → `모든 아이에게` 를 켜면 노령도 지병도 아닌 아이도 서명한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_intake_consent_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정·횟수 제한 키 지우기를 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객이 남는다.
# 단계 이름과 판정만 찍는다 — 토큰·주소·적은 이름·전화번호·서명 그림·문진표의 글은 찍지 않는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
SENIOR=$(( $(TZ=Asia/Seoul date +%Y) - 12 ))
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
pub() { curl -s "$BASE/v1/public/form" -H "X-Form-Token: $1"; }
pub_send() { curl -s -X POST "$BASE/v1/public/form/intake" -H "X-Form-Token: $1" -H 'Content-Type: application/json' -d "$2"; }
pub_code() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/public/form/intake" -H "X-Form-Token: $1" -H 'Content-Type: application/json' -d "$2"; }
token_of() { python3 -c "import json,sys; print(json.load(sys.stdin)['url'].rsplit('/',1)[1])"; }
# 600×240 PNG 머리 — 서버는 머리·폭·높이·크기만 본다.
PNG=$(python3 -c "import base64,struct; print(base64.b64encode(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',600,240)+b'\x08\x06\x00\x00\x00'+b'\x00'*30).decode())")

# 공개 제출은 접속 주소당 10분에 10번이다 — 앞서 돌린 흐름의 수를 지운다(개발 Redis 의 이 이름 공간만).
docker compose exec -T redis sh -c 'redis-cli --scan --pattern "customer:form-*" | xargs -r redis-cli del' >/dev/null

# 1. 매장·사장
op=$(login "icflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"문진표동의흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "icflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner" "{\"code\":\"$owner_code\"}" >/dev/null
S="/v1/shops/$shop_id"

# answer <태어난 해> <동의 JSON 또는 null>
answer() {
  echo "{\"guardian\":{\"name\":\"확인흐름\",\"phone\":\"$PHONE\"},\"pet\":{\"name\":\"모카\",\"species\":\"dog\",\"breed\":\"푸들\",\"sex\":\"male\",\"neutered\":false,\"birth_year\":$1,\"weight_kg\":4.5,\"no_known_conditions\":true,\"conditions\":[]},\"extras\":[],\"privacy_agreed\":true,\"done\":true,\"consent\":$2}"
}
consent() { echo "{\"digest\":\"$1\",\"parts\":$2,\"signer_name\":\"확인흐름\",\"signature_png\":\"$PNG\"}"; }

# 2. 새 손님용 링크를 연다 — 끝의 동의서 구역의 글과 기준이 함께 온다
token=$(call POST "$S/intake-forms" "$owner" '{"customer_id":null,"pet_id":null}' | token_of)
opened=$(pub "$token")
expect "2 동의서 구역이 있다" "$(echo "$opened" | field "['consent']['all'].__str__()+':'+str(d['consent']['senior_age'])")" "False:10"
expect "2 토막 셋의 글" "$(echo "$opened" | field "['consent']['texts'].__len__()")" "3"
old_digest=$(echo "$opened" | field "['consent']['digest']")

# 3. 노령 아이를 서명 없이 내면 받지 않는다
expect "3 서명 없이 422" "$(pub_send "$token" "$(answer $SENIOR null)" | field "['code']")" "CONSENT_REQUIRED"

# 4. 연 뒤 매장이 노령 안내의 글을 고쳤다 — 옛 지문으로는 409, 다시 열면 새 글
expect "4 글 고치기 200" "$(status PUT "$S/consent-texts/senior" "$owner" '{"body":"나이 많은 아이는 쉬어 가며 미용해요."}')" "200"
expect "4 옛 지문은 409" "$(pub_send "$token" "$(answer $SENIOR "$(consent "$old_digest" '["basic","senior"]')")" | field "['code']")" "CONSENT_DOCUMENT_CHANGED"
fresh=$(pub "$token")
expect "4 다시 열면 고친 글" "$(echo "$fresh" | field "['consent']['texts']['senior']['body']")" "나이 많은 아이는 쉬어 가며 미용해요."

# 5. 서명과 함께 내면 맡아 둔다 — 고객 표는 그대로다
expect "5 서명과 함께 204" "$(pub_code "$token" "$(answer $SENIOR "$(consent "$(echo "$fresh" | field "['consent']['digest']")" '["basic","senior"]')")")" "204"
answer_id=$(call GET "$S/intake-answers" "$owner" | field "['items'][0]['answer_id']")
expect "5 한 장에 서명 요약" "$(call GET "$S/intake-answers/$answer_id" "$owner" | field "['consent']['parts']")" "['basic', 'senior']"
expect "5 고객은 아직 없다" "$(call GET "$S/customers" "$owner" | field "['items'].__len__()")" "0"

# 6. 지병을 더해 등록하면 서명이 그 아이의 동의가 되고, 서명이 보지 않은 지병 토막만 남는다
pet_req="{\"name\":\"모카\",\"species\":\"dog\",\"breed\":\"푸들\",\"sex\":\"male\",\"neutered\":false,\"birth_year\":$SENIOR,\"weight_kg\":4.5,\"no_known_conditions\":false,\"conditions\":[{\"type_code\":\"heart_disease\",\"custom_label\":null,\"note\":null}]}"
registered=$(call POST "$S/customers" "$owner" "{\"customer\":{\"name\":\"확인흐름\",\"phone\":\"$PHONE\",\"marketing_consent\":false},\"pet\":$pet_req,\"intake_answer_id\":$answer_id}")
pet_id=$(echo "$registered" | field "['pets'][0]['pet_id']")
today=$(TZ=Asia/Seoul date +%F)
expect "6 받은 날은 서명한 날" "$(call GET "$S/pets/$pet_id" "$owner" | field "['pet']['grooming_consent_on']")" "$today"
expect "6 지병 토막만 남는다" "$(curl -s "$BASE$S/consent-document?pet_ids=$pet_id" -H "Authorization: Bearer $owner" | field "['pets'][0]['parts']")" "['condition']"
expect "6 서명의 받은 길은 문진표" "$(call GET "$S/pets/$pet_id/consent-signatures" "$owner" | field "['items'][0]['channel']")" "intake"
expect "6 받은 문진표가 비었다" "$(call GET "$S/intake-answers" "$owner" | field "['items'].__len__()")" "0"

# 7. 모든 아이에게를 켜면 노령도 지병도 아닌 아이도 서명한다
settings='{"link_days":14,"senior_age":10,"consent_days":365,"reservation_text":null,"consent_text":null,"intake_consent_all":true}'
expect "7 모든 아이에게 켜기 200" "$(status PUT "$S/form-settings" "$owner" "$settings")" "200"
young=$(call POST "$S/intake-forms" "$owner" '{"customer_id":null,"pet_id":null}' | token_of)
young_open=$(pub "$young")
expect "7 열면 모든 아이에게" "$(echo "$young_open" | field "['consent']['all']")" "True"
expect "7 어린 아이도 서명 없이 422" "$(pub_send "$young" "$(answer 2024 null | sed "s/$PHONE/01000000001/")" | field "['code']")" "CONSENT_REQUIRED"
expect "7 미용 안내에 서명하면 204" "$(pub_code "$young" "$(answer 2024 "$(consent "$(echo "$young_open" | field "['consent']['digest']")" '["basic"]')" | sed "s/$PHONE/01000000001/")")" "204"
echo "모두 통과"
