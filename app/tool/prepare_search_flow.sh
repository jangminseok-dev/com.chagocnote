#!/usr/bin/env bash
# ⑨-1b 시뮬레이터 흐름의 준비물 — 매장·사장, 보호자(메모 있음)와 아이 둘("콩이" — 특이사항·지병(심장 질환), "두부" — 특이사항),
# 콩이의 어제 완료 방문과 기록(케어 노트·내부 메모). 색인기가 글을 검색에 넣을 때까지 기다린다(글자로도 뜻으로도 찾아질 때까지).
# infra/ 에서 실행(bash ../app/tool/prepare_search_flow.sh). 개발 스택과 임베딩 프로세스(embed)가 떠 있어야 한다.
# 마지막 줄에 flutter drive 의 --dart-define 들을 찍는다. 액세스 토큰·전화번호·검색 응답은 찍지 않는다.
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
search() { curl -s -G "$BASE$S/search" -H "Authorization: Bearer $owner_token" --data-urlencode "q=$1"; }

op=$(login "sapp-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose exec -T backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"검색앱-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "sapp-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"

pet_body() {   # <이름> <특이사항> <지병 JSON 배열>
  local none=true; [ "$3" = "[]" ] || none=false
  echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":$none,\"conditions\":$3,\"memo\":\"$2\"}"
}
HEART='{"type_code":"heart_disease","custom_label":null,"note":"약 복용 중"}'
family_req="{\"customer\":{\"name\":\"김검색\",\"phone\":\"$PHONE\",\"marketing_consent\":false,\"memo\":\"미용이 끝나면 전화를 달라고 하심\"},\"pet\":$(pet_body 콩이 "드라이기 소리를 무서워해요" "[$HEART]")}"
registered=$(call POST "$S/customers" "$owner_token" "$family_req")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
dubu=$(call POST "$S/customers/$customer_id/pets" "$owner_token" "$(pet_body 두부 "빗질을 좋아해요" "[]")" | field "['pet']['pet_id']")

visit_req="{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(day -1)T11:00:00+09:00\"}"
visit=$(call POST "$S/visits" "$owner_token" "$visit_req" | field "['visits'][0]['visit_id']")
start_req="{\"visit_ids\":[$visit],\"action\":\"start\"}"; done_req="{\"visit_ids\":[$visit],\"action\":\"complete\"}"
call POST "$S/visits/transitions" "$owner_token" "$start_req" >/dev/null
record_req='{"care_note":"귀 청소할 때 예민하게 반응했어요. 귀 안쪽을 만지면 고개를 심하게 털어요.","internal_note":"입 주변을 만지면 무는 시늉을 함"}'
call PUT "$S/visits/$visit/record" "$owner_token" "$record_req" >/dev/null
call POST "$S/visits/transitions" "$owner_token" "$done_req" >/dev/null

# 색인기를 기다린다(30초까지) — 케어 노트가 글자로, 콩이의 특이사항이 뜻으로 찾아질 때까지.
ready=""
for _ in $(seq 1 60); do
  by_letter=$(search "귀 청소할 때" | python3 -c "import json,sys; print(sum(1 for i in json.load(sys.stdin)['items'] if i['visit_id'] == $visit))")
  by_meaning=$(search "드라이어 바람에 겁먹는 강아지" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['semantic'] and any(i['kind'] == 'pet_memo' and i['open_pet_id'] == $kong for i in d['items'])))")
  if [ "$by_letter" = "1" ] && [ "$by_meaning" = "1" ]; then ready=1; break; fi
  sleep 0.5
done
[ -n "$ready" ] || { echo "색인이 끝나지 않았습니다 — backend 와 embed 가 떠 있는지 확인해 주세요." >&2; exit 1; }
echo "--dart-define=SHOP=$shop_id --dart-define=PET=$kong --dart-define=PET2=$dubu --dart-define=VISIT=$visit --dart-define=OWNER=sapp-owner-$STAMP"
