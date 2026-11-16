#!/usr/bin/env bash
# 개발 환경에서 첫 방문 문진표 흐름을 게이트웨이를 거쳐 확인한다(⑪-C) — 설정 없이 새 손님용 링크를 보낸다 →
# 보호자가 로그인 없이 열고 아이 둘을 적어 낸다 → 받은 문진표에 둘이 있다 → 한 번에 등록한다(답이 사라진다) →
# 같은 답으로 두 번 등록되지 않는다 → 등록된 고객의 새 아이 → 이미 있는 아이의 정보를 다시 받기(지금 값은 싣지 않는다) →
# 매장이 칸을 끄고 질문을 더한다 → 보낸 서류와 끊기 → 익명화하면 답이 없다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_intake_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객이 남는다.
# 단계 이름과 판정만 찍는다 — 토큰·주소·적은 이름·전화번호·문진표의 글은 찍지 않는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# 공개 경로 — 토큰은 헤더로만 보낸다.
pub() { curl -s "$BASE/v1/public/form" -H "X-Form-Token: $1"; }
pub_send() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/public/form/intake" -H "X-Form-Token: $1" -H 'Content-Type: application/json' -d "$2"; }
token_of() { python3 -c "import json,sys; print(json.load(sys.stdin)['url'].rsplit('/',1)[1])"; }
count() { python3 -c "import json,sys; print(len(json.load(sys.stdin)['items']))"; }

# 1. 매장·사장
op=$(login "iflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"문진표흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "iflow-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"

# 보호자가 내는 답. answer <아이 이름> <보호자 JSON 또는 null> <done>
answer() {
  echo "{\"guardian\":$2,\"pet\":{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"푸들\",\"sex\":\"male\",\"neutered\":false,\"birth_year\":2022,\"weight_kg\":4.5,\"no_known_conditions\":true,\"conditions\":[],\"dislikes\":\"드라이기 소리\",\"style\":\"짧게\"},\"extras\":[],\"privacy_agreed\":true,\"done\":$3}"
}
GUARDIAN="{\"name\":\"확인흐름\",\"phone\":\"$PHONE\"}"

# 2. 설정을 한 번도 열지 않고 새 손님용 링크를 보낸다
sent=$(call POST "$S/intake-forms" "$owner" '{"customer_id":null,"pet_id":null}')
token=$(echo "$sent" | token_of)
expect "2 링크의 토큰은 43글자다" "${#token}" "43"
opened=$(pub "$token")
expect "2 로그인 없이 열린다" "$(echo "$opened" | field "['kind']+':'+d['state']+':'+d['mode']")" "intake:open:new"
expect "2 켜진 칸이 여덟이다" "$(echo "$opened" | field "['fields'].__len__()")" "8"
expect "2 고객·반려동물의 값은 싣지 않는다" "$(echo "$opened" | python3 -c "import json,sys; print(sorted(json.load(sys.stdin)))")" "['answered', 'condition_types', 'fields', 'guardian_needed', 'kind', 'mode', 'pet_name', 'questions', 'shop', 'state']"

# 3. 아이 둘을 적어 낸다 — 둘째는 보호자 칸을 묻지 않고, 다 적었어요로 닫는다
expect "3 첫 아이에게는 보호자 칸을 묻는다" "$(echo "$opened" | field "['guardian_needed']")" "True"
expect "3 첫 아이 204" "$(pub_send "$token" "$(answer 모카 "$GUARDIAN" false)")" "204"
expect "3 틀린 답은 422" "$(pub_send "$token" "$(answer 모카 null false | sed 's/"species":"dog"/"species":"bird"/')")" "422"
expect "3 둘째 아이부터는 묻지 않는다" "$(pub "$token" | field "['guardian_needed']")" "False"
expect "3 둘째 아이 204" "$(pub_send "$token" "$(answer 라떼 null true)")" "204"
expect "3 다 적으면 닫힌다" "$(pub "$token" | field "['state']")" "submitted"
expect "3 닫힌 링크로는 낼 수 없다" "$(pub_send "$token" "$(answer 셋째 null false)")" "410"

# 4. 받은 문진표 — 고객 표는 그대로다
answers=$(call GET "$S/intake-answers" "$owner")
expect "4 받은 문진표가 둘이다" "$(echo "$answers" | count)" "2"
expect "4 고객은 아직 없다" "$(call GET "$S/customers" "$owner" | count)" "0"
first=$(echo "$answers" | field "['items'][1]['answer_id']"); second=$(echo "$answers" | field "['items'][0]['answer_id']")
detail=$(call GET "$S/intake-answers/$first" "$owner")
expect "4 빈 필수 칸이 없다" "$(echo "$detail" | field "['missing']")" "[]"
expect "4 메모 초안이 두 줄이다" "$(echo "$detail" | field "['memo_draft'].count(chr(10))")" "1"

# 5. 한 번에 등록 — 답이 사라지고, 같은 답으로 두 번 등록되지 않는다
pet_of() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"푸들\",\"sex\":\"male\",\"neutered\":false,\"birth_year\":2022,\"weight_kg\":4.5,\"no_known_conditions\":true,\"conditions\":[]}"; }
register_req="{\"customer\":{\"name\":\"확인흐름\",\"phone\":\"$PHONE\",\"marketing_consent\":false},\"pet\":$(pet_of 모카),\"intake_answer_id\":$first}"
registered=$(call POST "$S/customers" "$owner" "$register_req")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); pet_id=$(echo "$registered" | field "['pets'][0]['pet_id']")
expect "5 답이 하나 남았다" "$(call GET "$S/intake-answers" "$owner" | count)" "1"
expect "5 같은 답으로 다시 등록하면 404" "$(status POST "$S/customers" "$owner" "$(echo "$register_req" | sed "s/$PHONE/01000000000/")")" "404"
# 둘째 답은 번호가 같은 고객(방금 등록한)에 미리 이어져 있지 않다 — 낼 때는 고객이 없었다. 그 고객의 새 아이로 더한다.
add_req="$(pet_of 라떼 | sed "s/}$/,\"intake_answer_id\":$second}/")"
expect "5 둘째를 그 고객의 새 아이로 201" "$(status POST "$S/customers/$customer_id/pets" "$owner" "$add_req")" "201"
expect "5 받은 문진표가 비었다" "$(call GET "$S/intake-answers" "$owner" | count)" "0"

# 6. 등록된 고객의 새 아이 — 보호자를 묻지 않고, 그 고객에 이어져 있다
add_sent=$(call POST "$S/intake-forms" "$owner" "{\"customer_id\":$customer_id,\"pet_id\":null}")
add_token=$(echo "$add_sent" | token_of)
expect "6 다시 보내면 같은 링크다" "$(call POST "$S/intake-forms" "$owner" "{\"customer_id\":$customer_id,\"pet_id\":null}" | field "['form_id']")" "$(echo "$add_sent" | field "['form_id']")"
expect "6 새 아이용이다" "$(pub "$add_token" | field "['mode']")" "add_pet"
expect "6 보호자 없이 204" "$(pub_send "$add_token" "$(answer 두부 null false)")" "204"
expect "6 그 고객에 이어져 있다" "$(call GET "$S/intake-answers" "$owner" | field "['items'][0]['matched_customer']['customer_id']")" "$customer_id"

# 7. 이미 있는 아이의 정보를 다시 받기 — 아이 이름만 보이고, 바뀐 것만 적고, 한 번 내면 닫힌다
upd_token=$(call POST "$S/intake-forms" "$owner" "{\"customer_id\":null,\"pet_id\":$pet_id}" | token_of)
upd=$(pub "$upd_token")
expect "7 다시 받기에는 아이 이름만 있다" "$(echo "$upd" | field "['mode']+':'+d['pet_name']")" "update:모카"
expect "7 몸무게만 적어 204" "$(pub_send "$upd_token" '{"guardian":null,"pet":{"weight_kg":5.1},"extras":[],"privacy_agreed":true}')" "204"
expect "7 한 번 내면 닫힌다" "$(pub "$upd_token" | field "['state']")" "submitted"
expect "7 저절로 반영하지 않는다" "$(call GET "$S/pets/$pet_id" "$owner" | field "['pet']['weight_kg']")" "4.5"

# 8. 매장이 칸을 끄고 질문을 더한다 — 열려 있던 링크도 다음에 열 때 새 구성이다
settings_req='{"link_days":14,"senior_age":10,"consent_days":365,"reservation_text":null,"consent_text":null,"intake_keep_days":30,"intake_hidden":["weight","style"]}'
expect "8 칸 끄기 200" "$(status PUT "$S/form-settings" "$owner" "$settings_req")" "200"
question=$(call PUT "$S/intake-questions" "$owner" '{"items":[{"question_id":null,"label":"산책은 얼마나 하나요?","required":true}]}' | field "['items'][0]['question_id']")
again=$(pub "$add_token")
expect "8 켜진 칸이 여섯이다" "$(echo "$again" | field "['fields'].__len__()")" "6"
expect "8 질문이 하나 보인다" "$(echo "$again" | field "['questions'].__len__()")" "1"
expect "8 필수 질문의 답이 없으면 422" "$(pub_send "$add_token" "$(answer 보리 null false)")" "422"
with_answer="$(answer 보리 null false | sed "s/\"extras\":\[\]/\"extras\":[{\"question_id\":$question,\"body\":\"하루 한 번\"}]/")"
expect "8 답을 적으면 204" "$(pub_send "$add_token" "$with_answer")" "204"
expect "8 끌 수 없는 칸은 422" "$(status PUT "$S/form-settings" "$owner" "$(echo "$settings_req" | sed 's/"weight","style"/"pet_name"/')")" "422"

# 9. 보낸 서류와 끊기
expect "9 보낸 서류에 살아 있는 문진표가 하나다" "$(call GET "$S/forms" "$owner" | python3 -c "import json,sys; print(sum(1 for i in json.load(sys.stdin)['items'] if i['kind']=='intake'))")" "1"
expect "9 끊기 204" "$(status DELETE "$S/forms/$(echo "$add_sent" | field "['form_id']")" "$owner")" "204"
expect "9 끊은 링크는 410" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/form" -H "X-Form-Token: $add_token")" "410"
expect "9 문진표 토큰은 알림장 경로에서 404" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/report" -H "X-Report-Token: $upd_token")" "404"

# 10. 익명화하면 그 고객에 이어 둔 답이 없다
expect "10 익명화 전에는 답이 셋이다" "$(call GET "$S/intake-answers" "$owner" | count)" "3"
expect "10 익명화 204" "$(status DELETE "$S/customers/$customer_id" "$owner")" "204"
expect "10 답이 남지 않았다" "$(call GET "$S/intake-answers" "$owner" | count)" "0"
echo "모두 통과"
