#!/usr/bin/env bash
# 개발 환경에서 전자 동의서 흐름을 게이트웨이를 거쳐 확인한다(⑪-A) — 노령·지병 아이를 내일 예약하면 동의가 뜬다 →
# 동의서를 보낸다(다시 보내도 같은 링크) → 보호자가 로그인 없이 읽고 서명한다 → 동의가 사라진다 → 지병을 더하면
# 바뀐 토막만 다시 뜬다 → 매장에서 바로 서명받는다(받은 날은 그대로) → 서명 보기 → 링크 끊기 → 알림장 토큰은
# 서류 경로에서 404 → 서류 설정·글 고치기·보낼 것 묶음(⑪-B) → 익명화하면 서명이 없다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_consent_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문이 남는다.
# 단계 이름과 판정만 찍는다 — 토큰·주소·적은 이름·전화번호는 찍지 않는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE_A="010$(printf '%08d' $((STAMP % 100000000)))"
PHONE_B="010$(printf '%08d' $(((STAMP + 1) % 100000000)))"
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# consent — 방문 상세의 동의 항목을 "상태:토막" 으로. 없으면 "없음".
consent() { python3 -c "
import json,sys
found=[c for c in json.load(sys.stdin)['checks'] if c['code']=='consent']
print('없음' if not found else found[0]['detail']['state']+':'+','.join(found[0]['detail'].get('parts',[])))"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# 공개 경로 — 토큰은 헤더로만 보낸다.
pub() { curl -s "$BASE/v1/public/form" -H "X-Form-Token: $1"; }
pub_status() { curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/form" -H "X-Form-Token: $1"; }
pub_sign() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/public/form/consent" -H "X-Form-Token: $1" -H 'Content-Type: application/json' -d "$2"; }
# 600×240 PNG 의 머리만 가진 바이트 — 서버는 그림을 풀지 않는다.
PNG=$(python3 -c "import base64,struct; print(base64.b64encode(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',600,240)+b'\x08\x06\x00\x00\x00'+b'\x00'*30).decode())")
sign_body() { echo "{\"doc_digest\":\"$1\",\"signer_name\":\"확인흐름\",\"signature_png\":\"$PNG\"}"; }

TODAY="$(day 0)"

# 1. 매장·사장
op=$(login "sflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"동의서흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "sflow-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"

pet_body() {
  local none=true; [ "$3" = "[]" ] || none=false
  echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":$2,\"weight_kg\":3.2,\"no_known_conditions\":$none,\"conditions\":$3}"
}
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":$3}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
HEART='{"type_code":"heart_disease","custom_label":null,"note":"약 복용 중"}'
ALLERGY='{"type_code":"allergy","custom_label":null,"note":null}'
OLD_YEAR=$(( $(TZ=Asia/Seoul date +%Y) - 15 ))
read -r old_owner old_pet <<<"$(family 김노령 "$PHONE_A" "$(pet_body 초코 "$OLD_YEAR" "[$HEART]")")"
read -r kong_owner kong <<<"$(family 박콩이 "$PHONE_B" "$(pet_body 콩이 "$OLD_YEAR" "[]")")"
visit_req="{\"customer_id\":$old_owner,\"pet_ids\":[$old_pet],\"starts_at\":\"$(at 1 11)\"}"
visit_id=$(call POST "$S/visits" "$owner" "$visit_req" | field "['visits'][0]['visit_id']")
expect "1 노령·지병 아이의 예약에 동의가 뜬다" "$(call GET "$S/visits/$visit_id" "$owner" | consent)" "missing:"

# 2. 동의서 보내기 — 다시 보내도 같은 링크
send_req="{\"pet_ids\":[$old_pet]}"
sent=$(call POST "$S/consent-forms" "$owner" "$send_req")
form_id=$(echo "$sent" | field "['form_id']"); token=$(echo "$sent" | field "['url'].rsplit('/',1)[1]")
expect "2 다시 보내면 같은 요청이다" "$(call POST "$S/consent-forms" "$owner" "$send_req" | field "['form_id']")" "$form_id"
expect "2 확인할 것에 보낸 날이 실린다" "$(call GET "$S/visits/$visit_id" "$owner" | field "['checks']" | python3 -c "
import ast,sys; c=[x for x in ast.literal_eval(sys.stdin.read()) if x['code']=='consent'][0]; print(c['detail'].get('form_sent_on'))")" "$TODAY"

# 3. 공개 읽기 — 로그인 없이, 토큰은 헤더로
opened=$(pub "$token")
expect "3 열려 있다" "$(echo "$opened" | field "['state']")" "open"
expect "3 토막은 미용 안내·노령·지병이다" "$(echo "$opened" | field "['pets'][0]['parts']" | tr -d " '[]")" "basic,senior,condition"
expect "3 공개 응답에 ID 가 없다" "$(echo "$opened" | python3 -c "import sys; s=sys.stdin.read(); print(any(k in s for k in ('pet_id','customer_id','shop_id','form_id')))")" "False"
expect "3 지병의 메모가 없다" "$(echo "$opened" | python3 -c "import sys; print('복용' in sys.stdin.read())")" "False"
digest=$(echo "$opened" | field "['doc_digest']")

# 4. 서명 → 다시 읽으면 보냈어요 → 두 번째는 닫힘
expect "4 서명하면 204" "$(pub_sign "$token" "$(sign_body "$digest")")" "204"
expect "4 다시 열면 보냈어요" "$(pub "$token" | field "['state']")" "submitted"
expect "4 두 번 내면 410" "$(pub_sign "$token" "$(sign_body "$digest")")" "410"

# 5. 동의가 사라지고 서명으로 받은 것으로 적힌다
expect "5 확인할 것에서 동의가 사라졌다" "$(call GET "$S/visits/$visit_id" "$owner" | consent)" "없음"
pet=$(call GET "$S/pets/$old_pet" "$owner")
expect "5 받은 날이 오늘이다" "$(echo "$pet" | field "['pet']['grooming_consent_on']")" "$TODAY"
expect "5 서명으로 받았다" "$(echo "$pet" | field "['pet']['grooming_consent_via']")" "signature"

# 6. 지병을 더하면 바뀐 토막만 다시
expect "6 지병 더하기" "$(status PUT "$S/pets/$old_pet" "$owner" "$(pet_body 초코 "$OLD_YEAR" "[$HEART,$ALLERGY]")")" "200"
expect "6 받은 날은 그대로다" "$(call GET "$S/pets/$old_pet" "$owner" | field "['pet']['grooming_consent_on']")" "$TODAY"
expect "6 지병 토막만 다시 뜬다" "$(call GET "$S/visits/$visit_id" "$owner" | consent)" "partial:condition"

# 7. 매장에서 바로 서명
doc=$(call GET "$S/consent-document?pet_ids=$old_pet" "$owner")
expect "7 현장 문서는 지병 토막뿐이다" "$(echo "$doc" | field "['pets'][0]['parts']" | tr -d " '[]")" "condition"
expect "7 지난 동의의 날이 실린다" "$(echo "$doc" | field "['previous_consent_on']")" "$TODAY"
here_req="{\"pet_ids\":[$old_pet],\"doc_digest\":\"$(echo "$doc" | field "['doc_digest']")\",\"signer_name\":\"확인흐름\",\"signature_png\":\"$PNG\"}"
expect "7 틀린 지문은 409" "$(status POST "$S/consent-signatures" "$owner" "$(sign_body "$digest" | sed "s/^{/{\"pet_ids\":[$old_pet],/")")" "409"
expect "7 현장 서명 201" "$(status POST "$S/consent-signatures" "$owner" "$here_req")" "201"
expect "7 동의가 사라졌다" "$(call GET "$S/visits/$visit_id" "$owner" | consent)" "없음"
expect "7 더 받을 것이 없으면 409" "$(status GET "$S/consent-document?pet_ids=$old_pet" "$owner")" "409"

# 8. 서명 보기
signs=$(call GET "$S/pets/$old_pet/consent-signatures" "$owner")
expect "8 서명이 둘이다" "$(echo "$signs" | field "['items'].__len__()")" "2"
expect "8 새것이 앞이고 현장 서명이다" "$(echo "$signs" | field "['items'][0]['channel']")" "in_shop"
sig_id=$(echo "$signs" | field "['items'][0]['signature_id']")
expect "8 그때 보인 지병이 둘이다" "$(call GET "$S/consent-signatures/$sig_id" "$owner" | field "['pets'][0]['conditions'].__len__()")" "2"
expect "8 그림은 PNG 다" "$(curl -s -o /dev/null -w '%{content_type}' "$BASE$S/consent-signatures/$sig_id/image" -H "Authorization: Bearer $owner")" "image/png"

# 9. 다른 아이에게 보낸 뒤 끊는다
kong_req="{\"pet_ids\":[$kong]}"
kong_sent=$(call POST "$S/consent-forms" "$owner" "$kong_req")
kong_form=$(echo "$kong_sent" | field "['form_id']"); kong_token=$(echo "$kong_sent" | field "['url'].rsplit('/',1)[1]")
expect "9 보낸 서류에 하나 있다" "$(call GET "$S/forms" "$owner" | field "['items'].__len__()")" "1"
expect "9 끊기 204" "$(status DELETE "$S/forms/$kong_form" "$owner")" "204"
expect "9 끊은 링크는 410" "$(pub_status "$kong_token")" "410"
expect "9 보낸 서류가 비었다" "$(call GET "$S/forms" "$owner" | field "['items'].__len__()")" "0"

# 10. 토큰의 쓰임 — 서류 토큰은 알림장 경로에서, 지어낸 토큰은 서류 경로에서 404
expect "10 서류 토큰은 알림장 경로에서 404" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/report" -H "X-Report-Token: $token")" "404"
expect "10 지어낸 토큰은 404" "$(pub_status "$(printf 'a%.0s' $(seq 43))")" "404"
expect "10 헤더가 없으면 404" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/form")" "404"

# 12. 서류 설정과 보낼 것 묶음(⑪-B) — 설정 없이 기본값으로 돌고, 매장이 글과 기준값을 바꾼다
kinds() { python3 -c "import json,sys; print(','.join(p['kind'] for p in json.load(sys.stdin)['parts']))"; }
expect "12 정한 적 없는 매장의 링크 기간은 14일" "$(call GET "$S/form-settings" "$owner" | field "['link_days']")" "14"
book2_req="{\"customer_id\":$kong_owner,\"pet_ids\":[$kong],\"starts_at\":\"$(at 2 15)\"}"
visit2=$(call POST "$S/visits" "$owner" "$book2_req" | field "['visits'][0]['visit_id']")
bundle=$(call POST "$S/visits/$visit2/send-bundle" "$owner")
expect "12 묶음은 예약 안내와 동의서 링크다" "$(echo "$bundle" | kinds)" "reservation,consent"
expect "12 묶음의 글에 빈 자리가 없다" "$(echo "$bundle" | python3 -c "import json,sys; print(any('{' in p['text'] for p in json.load(sys.stdin)['parts']))")" "False"
same() { python3 -c "import json,sys,hashlib; print(hashlib.sha256(json.dumps(json.load(sys.stdin),sort_keys=True).encode()).hexdigest()[:12])"; }
expect "12 다시 불러도 같은 묶음이다" "$(call POST "$S/visits/$visit2/send-bundle" "$owner" | same)" "$(echo "$bundle" | same)"
token2=$(echo "$bundle" | python3 -c "import json,sys; print(json.load(sys.stdin)['parts'][1]['text'].rsplit('/f/',1)[1].split()[0])")
digest2=$(pub "$token2" | field "['doc_digest']")
text_req='{"body":"나이가 많은 아이는 쉬어 가며 미용해요."}'
expect "12 노령 토막의 글 고치기 200" "$(status PUT "$S/consent-texts/senior" "$owner" "$text_req")" "200"
expect "12 보호자의 화면에 고친 글이 보인다" "$(pub "$token2" | field "['texts']['senior']['body']")" "나이가 많은 아이는 쉬어 가며 미용해요."
expect "12 옛 글을 본 지문은 409" "$(pub_sign "$token2" "$(sign_body "$digest2")")" "409"
expect "12 빈 글은 422" "$(status PUT "$S/consent-texts/senior" "$owner" '{"body":"  "}')" "422"
expect "12 기본 글로 되돌리기 200" "$(status PUT "$S/consent-texts/senior" "$owner" '{"body":null}')" "200"
settings_req='{"link_days":7,"senior_age":20,"consent_days":365,"reservation_text":null,"consent_text":null}'
expect "12 범위 밖의 값은 422" "$(status PUT "$S/form-settings" "$owner" "$(echo "$settings_req" | sed 's/"link_days":7/"link_days":31/')")" "422"
expect "12 노령 나이를 20살로 200" "$(status PUT "$S/form-settings" "$owner" "$settings_req")" "200"
expect "12 15살 아이의 동의가 사라졌다" "$(call GET "$S/visits/$visit2" "$owner" | consent)" "없음"
expect "12 묶음은 예약 안내뿐이다" "$(call POST "$S/visits/$visit2/send-bundle" "$owner" | kinds)" "reservation"

# 11. 익명화하면 서명이 없다 (앞으로의 예약을 먼저 취소한다)
cancel_req="{\"visit_ids\":[$visit_id],\"action\":\"cancel\",\"cancel_reason\":\"shop_reason\"}"
call POST "$S/visits/transitions" "$owner" "$cancel_req" >/dev/null
expect "11 익명화 204" "$(status DELETE "$S/customers/$old_owner" "$owner")" "204"
expect "11 서명은 404" "$(status GET "$S/consent-signatures/$sig_id" "$owner")" "404"
expect "11 낸 링크도 닫혔다" "$(pub_status "$token")" "410"
echo "모두 통과"
