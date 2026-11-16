// 가짜 백엔드 — 토큰(43글자)의 앞머리로 응답을 고르고, 받은 요청을 센다.
// 사용: node tests/server/fake-backend.mjs <포트>
//
//   ok    200 알림장 전체(모든 항목 켬)      gone  410
//   min   200 끈 항목의 칸이 없는 알림장      rate  429
//   vid   200 영상 하나뿐인 알림장            boom  500
//   nf    404 (그 밖의 앞머리도 404)          down  소켓을 끊는다
//                                              slow  응답하지 않고 연결을 붙들고 있는다
// POST /v1/public/report/viewed 도 같은 규칙이고 200 자리에 204 다.
//
// 서류(동의서) — X-Form-Token 의 앞머리로 고른다.
//   GET /v1/public/form            ok 열림(아이 둘·토막 셋)  part 바뀐 부분만  sent 보냈어요  gone 410  rate 429  boom 500
//                                  slow 매달린다  down 소켓을 끊는다  그 밖 404
//   GET /v1/public/form (문진표)   iok 새 손님  iupd 다시 받기(두부)  isent 보냈어요  ibad 열림(제출은 422)
//   POST /v1/public/form/intake    iok 204  ichg 409(동의서 글이 바뀜)  ibad 422  gone 410  rate 429  boom 500  그 밖 404
//   POST /v1/public/form/consent   ok 204  chg 409  gone 410  big 413  bad 422  rate 429  boom 500  그 밖 404
//
// 이 서버는 인증 프로세스도 맡는다(검사는 AUTH_BASE_URL 을 같은 주소로 둔다).
// POST /v1/auth/social — 본문의 token(로그인 이름)의 앞머리로 고른다. session 이 "web" 이 아니면 422.
//   down 소켓을 끊는다   bad 401   refresh 200 인데 리프레시 토큰을 준다   그 밖 200, access_token 은 "tok-<이름>"
// /v1/me/guardian/… — Authorization 의 토큰(tok-<이름>)의 앞머리로 고른다.
//   tok-expired 401   tok-susp 403   tok-slow 매달린다   tok-empty 연결이 없다   그 밖 아래의 표준 자료
//   tok-stale 표준 자료에 연결 13 이 하나 더 있는데 그 연결의 아이들·알림장은 404 다(목록을 읽은 직후 끊긴 연결)
// POST /v1/me/guardian/links(잇기)는 X-Report-Token 의 앞머리 — ok 201, gone 410, taken 409, rate 429, 그 밖 404.
import http from 'node:http'

const port = Number(process.argv[2])
// 미디어 주소는 백엔드 주소(API_BASE_URL = 127.0.0.1)와 글자가 다르게 localhost 로 둔다.
// 실제 서명 주소도 저장소의 주소라 백엔드 주소와 다르다. 첫 HTML 에 백엔드 주소가 없는지 볼 수 있다.
const media = `http://localhost:${port}/media`

let count = 0
let reports = 0 // GET /v1/public/report
let viewed = 0 // POST /v1/public/report/viewed
let auth = 0 // POST /v1/auth/social
let claims = 0 // POST /v1/me/guardian/links
let guardian = 0 // 그 밖의 /v1/me/guardian/…
let forms = 0 // GET /v1/public/form
let consents = 0 // POST /v1/public/form/consent
let intakes = 0 // POST /v1/public/form/intake
let last = null

const photo = (name, phase) => ({
  kind: 'photo',
  phase,
  width: 1200,
  height: 1600,
  duration_seconds: null,
  display_url: `${media}/display/${name}.jpg?X-Amz-Signature=display-${name}`,
  thumb_url: `${media}/thumb/${name}.jpg?X-Amz-Signature=thumb-${name}`,
  download_url: `${media}/original/${name}.jpg?X-Amz-Signature=download-${name}`,
})

const video = (name, phase) => ({
  kind: 'video',
  phase,
  width: 1080,
  height: 1920,
  duration_seconds: 18,
  display_url: `${media}/original/${name}.mp4?X-Amz-Signature=display-${name}`,
  thumb_url: `${media}/poster/${name}.jpg?X-Amz-Signature=thumb-${name}`,
  download_url: `${media}/original/${name}.mp4?X-Amz-Signature=download-${name}`,
})

const FULL = {
  pet_name: '두부',
  visit_date: '2026-09-28',
  care_note: '오늘 두부가 드라이할 때 조금 긴장했지만 끝까지 잘 참아 줬어요.',
  media: [photo('after-1', 'after'), photo('after-2', 'after'), video('after-3', 'after'), photo('before-1', 'before')],
  cover: { url: `${media}/display/after-1.jpg?X-Amz-Signature=cover`, width: 1200, height: 1600 },
  menus: [
    { name: '전체 미용', amount: 55000 },
    { name: '스파', amount: 15000 },
  ],
  total_amount: 70000,
  weight_kg: 4.2,
  shop: { name: 'Hiss Haus', phone: '02-123-4567', address: '서울 마포구 ○○로 12, 1층' },
  expires_at: '2026-10-28T23:59:59+09:00',
}

const MINIMAL = {
  pet_name: null,
  visit_date: '2026-09-28',
  care_note: null,
  media: [],
  cover: null,
  expires_at: null,
}

// 사진이 없다. 백엔드는 대표(cover)로 영상의 포스터를 준다(결정 기록 008).
const only = video('only', 'after')
const VIDEO_ONLY = { ...MINIMAL, pet_name: '두부', media: [only], cover: { url: only.thumb_url, width: 1080, height: 1920 } }

const REPORTS = { ok: FULL, min: MINIMAL, vid: VIDEO_ONLY }
const ERRORS = {
  gone: [410, 'REPORT_CLOSED'],
  rate: [429, 'TOO_MANY_ATTEMPTS'],
  boom: [500, 'INTERNAL_ERROR'],
}

// 로그인한 보호자의 표준 자료 — 연결 둘(11 은 아이 둘·알림장 셋, 12 는 비어 있다).
const LINKS = [
  { link_id: 11, shop_name: 'Hiss Haus', linked_at: '2026-11-01T10:00:00+09:00' },
  { link_id: 12, shop_name: '둘째 매장', linked_at: '2026-11-05T15:30:00+09:00' },
]
const PETS = { 11: [{ pet_id: 7, name: '두부' }, { pet_id: 8, name: null }], 12: [] }
const item = (report_id, extra) => ({ report_id, visit_date: '2026-09-28', pet_id: null, pet_name: null, cover: null, media_count: 0, ...extra })
const ITEM_501 = item(501, { pet_id: 7, pet_name: '두부', cover: FULL.cover, media_count: 4 })
const ITEM_502 = item(502, { visit_date: '2026-08-15' }) // 보호자만의 방문 — 이름·대표·사진이 없다
const ITEM_503 = item(503, { visit_date: '2026-07-01', pet_id: 8 })

/** 본문을 다 읽어 JSON 으로. 깨졌으면 {} */
function readJson(req) {
  return new Promise((done) => {
    let text = ''
    req.on('data', (chunk) => (text += chunk))
    req.on('end', () => {
      try {
        done(JSON.parse(text))
      } catch {
        done({})
      }
    })
  })
}

async function login(req, send) {
  const body = await readJson(req)
  last.session = body.session ?? null
  const name = String(body.token ?? '')
  if (body.session !== 'web') return send(422, { code: 'VALIDATION_ERROR', message: '가짜 백엔드의 오류' })
  if (name.startsWith('down')) return req.socket.destroy()
  if (name.startsWith('bad')) return send(401, { code: 'INVALID_SOCIAL_TOKEN', message: '가짜 백엔드의 오류' })
  return send(200, {
    access_token: `tok-${name}`,
    refresh_token: name.startsWith('refresh') ? 'refresh-token' : null,
    token_type: 'Bearer',
    expires_in: 1800,
    user_id: 1,
    is_new_user: false,
  })
}

function guardianApi(req, url, send) {
  const bearer = String(req.headers.authorization ?? '').replace(/^Bearer /, '')
  const error = (status, code) => send(status, { code, message: '가짜 백엔드의 오류' })
  if (!bearer.startsWith('tok-') || bearer.startsWith('tok-expired')) return error(401, 'UNAUTHENTICATED')
  if (bearer.startsWith('tok-susp')) return error(403, 'ACCOUNT_SUSPENDED')
  if (bearer.startsWith('tok-slow')) return
  const empty = bearer.startsWith('tok-empty')
  const path = url.pathname.slice('/v1/me/guardian'.length)

  if (req.method === 'POST' && path === '/links') {
    const token = String(req.headers['x-report-token'] ?? '')
    if (token.startsWith('ok')) return send(201, { link_id: 11 })
    if (token.startsWith('gone')) return error(410, 'REPORT_CLOSED')
    if (token.startsWith('taken')) return error(409, 'GUARDIAN_ALREADY_LINKED')
    if (token.startsWith('rate')) return error(429, 'GUARDIAN_RATE_LIMITED')
    return error(404, 'REPORT_NOT_FOUND')
  }
  const stale = bearer.startsWith('tok-stale') ? [{ link_id: 13, shop_name: '방금 끊긴 매장', linked_at: '2026-11-07T09:00:00+09:00' }] : []
  if (req.method === 'GET' && path === '/links') return send(200, { items: empty ? [] : [...LINKS, ...stale] })

  const [, id, rest] = path.match(/^\/links\/(\d+)(\/.*)?$/) ?? []
  const linkId = Number(id)
  if (empty || !(linkId in PETS)) return error(404, 'GUARDIAN_LINK_NOT_FOUND')
  if (req.method === 'DELETE' && rest === undefined) return linkId === 11 ? send(204) : error(404, 'GUARDIAN_LINK_NOT_FOUND')
  if (req.method !== 'GET') return error(404, 'NOT_FOUND')
  if (rest === '/pets') return send(200, { items: PETS[linkId] })
  if (rest === '/reports') {
    if (linkId !== 11) return send(200, { items: [], next_cursor: null })
    if (url.searchParams.get('pet_id') === '7') return send(200, { items: [ITEM_501], next_cursor: null })
    if (url.searchParams.get('cursor') === 'c2') return send(200, { items: [ITEM_503], next_cursor: null })
    return send(200, { items: [ITEM_501, ITEM_502], next_cursor: 'c2' })
  }
  if (rest === '/reports/501' && linkId === 11) return send(200, { ...FULL, expires_at: null })
  return error(404, 'REPORT_NOT_FOUND')
}

// 열려 있는 동의서 — 가족 둘, 토막 셋. 지병의 메모·ID 는 백엔드가 주지 않는다.
const OPEN_FORM = {
  kind: 'consent',
  state: 'open',
  shop: { name: 'Hiss Haus' },
  previous_consent_on: null,
  pets: [
    { name: '두부', conditions: [], parts: ['basic', 'senior'] },
    { name: '모카', conditions: ['심장 질환', '피부'], parts: ['basic', 'condition'] },
  ],
  texts: {
    basic: { body: '미용하는 동안 작은 상처가 생길 수 있어요.\n많이 힘들어하면 미용을 멈출게요.' },
    senior: { body: '나이가 많은 아이는 미용이 부담이 될 수 있어요.' },
    condition: { body: '알려 주신 지병 때문에 상태가 나빠질 수 있어요.' },
  },
  doc_digest: 'd'.repeat(64),
}
const PARTIAL_FORM = {
  ...OPEN_FORM,
  previous_consent_on: '2026-03-02',
  pets: [{ name: '모카', conditions: ['심장 질환', '피부'], parts: ['condition'] }],
  texts: { condition: OPEN_FORM.texts.condition },
}
const SUBMITTED_FORM = { kind: 'consent', state: 'submitted', shop: { name: 'Hiss Haus' }, submitted_on: '2026-11-16' }
// 열려 있는 문진표 — 새 손님용. 지금 값(품종·몸무게·지병)과 ID 는 백엔드가 주지 않는다(질문 ID 만).
const OPEN_INTAKE = {
  kind: 'intake',
  state: 'open',
  shop: { name: 'Hiss Haus' },
  mode: 'new',
  pet_name: null,
  fields: ['species', 'breed', 'sex', 'neutered', 'birth', 'weight', 'dislikes', 'style'],
  questions: [{ question_id: 7, label: '산책은 얼마나 하나요?', required: false }],
  condition_types: [
    { code: 'heart_disease', label: '심장 질환' },
    { code: 'other', label: '기타' },
  ],
  answered: 0,
  guardian_needed: true,
  keep_days: 30,
  // 끝의 동의서 구역(⑪-C1b) — 글과 기준뿐이다. 아이의 지금 사실은 없다.
  consent: { all: false, senior_age: 10, texts: { basic: { body: '미용 안내의 글' }, senior: { body: '노령 안내의 글' }, condition: { body: '지병 안내의 글' } }, digest: 'c'.repeat(64) },
}
const UPDATE_INTAKE = { ...OPEN_INTAKE, mode: 'update', pet_name: '두부', guardian_needed: false, questions: [] }
const SUBMITTED_INTAKE = { kind: 'intake', state: 'submitted', shop: { name: 'Hiss Haus' }, submitted_on: '2026-11-16' }
const FORMS = {
  ok: OPEN_FORM, part: PARTIAL_FORM, sent: SUBMITTED_FORM, chg: OPEN_FORM, big: OPEN_FORM, bad: OPEN_FORM,
  iok: OPEN_INTAKE, iupd: UPDATE_INTAKE, isent: SUBMITTED_INTAKE, ibad: OPEN_INTAKE, ichg: OPEN_INTAKE,
}
const INTAKE_STATUS = { iok: [204], ibad: [422, 'VALIDATION_ERROR'], ichg: [409, 'CONSENT_DOCUMENT_CHANGED'] }
const FORM_ERRORS = { gone: [410, 'FORM_CLOSED'], rate: [429, 'TOO_MANY_ATTEMPTS'], boom: [500, 'INTERNAL_ERROR'] }
const CONSENT_STATUS = { ok: [204], chg: [409, 'CONSENT_DOCUMENT_CHANGED'], big: [413, 'PAYLOAD_TOO_LARGE'], bad: [422, 'VALIDATION_ERROR'] }
const formPrefixOf = (token) =>
  ['iok', 'iupd', 'isent', 'ibad', 'ichg', 'ok', 'part', 'sent', 'chg', 'big', 'bad', 'gone', 'rate', 'boom', 'down', 'slow'].find((prefix) => token.startsWith(prefix))

async function formApi(req, url, send) {
  const prefix = formPrefixOf(String(req.headers['x-form-token'] ?? ''))
  const error = (status, code) => send(status, { code, message: '가짜 백엔드의 오류' })
  if (prefix === 'down') return req.socket.destroy()
  if (prefix === 'slow') return
  if (prefix in FORM_ERRORS) return error(...FORM_ERRORS[prefix])
  if (req.method === 'GET' && url.pathname === '/v1/public/form' && prefix in FORMS) return send(200, FORMS[prefix])
  if (req.method === 'POST' && url.pathname === '/v1/public/form/consent' && prefix in CONSENT_STATUS) {
    // 본문의 값은 적지 않는다. 칸의 이름만 남긴다 — 웹이 무엇을 넘겼는지 본다.
    last.body_keys = Object.keys(await readJson(req)).sort()
    const [status, code] = CONSENT_STATUS[prefix]
    return status === 204 ? send(204) : error(status, code)
  }
  if (req.method === 'POST' && url.pathname === '/v1/public/form/intake' && prefix in INTAKE_STATUS) {
    // 본문의 값은 적지 않는다. 칸의 이름만 남긴다 — 웹이 무엇을 넘겼는지 본다.
    const body = await readJson(req)
    last.body_keys = Object.keys(body).sort()
    last.pet_keys = Object.keys(body.pet ?? {}).sort()
    const [status, code] = INTAKE_STATUS[prefix]
    return status === 204 ? send(204) : error(status, code)
  }
  return error(404, 'FORM_NOT_FOUND')
}

const prefixOf = (token) => ['ok', 'min', 'vid', 'gone', 'rate', 'boom', 'down', 'slow'].find((prefix) => token.startsWith(prefix))

http
  .createServer((req, res) => {
    const send = (status, body) => {
      res.writeHead(status, { 'content-type': 'application/json' })
      res.end(body === undefined ? '' : JSON.stringify(body))
    }
    if (req.url === '/__stats') return send(200, { count, reports, viewed, auth, claims, guardian, forms, consents, intakes, last })
    if (req.url === '/__reset') {
      count = reports = viewed = auth = claims = guardian = forms = consents = intakes = 0
      last = null
      return send(200, {})
    }

    count += 1
    if (req.method === 'GET' && req.url === '/v1/public/report') reports += 1
    if (req.method === 'POST' && req.url === '/v1/public/report/viewed') viewed += 1
    // 토큰은 적지 않는다. 웹이 붙인 두 헤더와, 토큰 헤더가 있었는지만 남긴다.
    last = {
      method: req.method,
      path: req.url,
      web_secret: req.headers['x-report-web-secret'] ?? null,
      client_ip: req.headers['x-report-client-ip'] ?? null,
      bearer: req.headers.authorization !== undefined,
      report_token: req.headers['x-report-token'] !== undefined,
      form_token: req.headers['x-form-token'] !== undefined,
      body_keys: null, // 서명 본문의 칸 이름
      session: null, // 로그인 본문의 session
    }

    const url = new URL(req.url, 'http://fake')
    if (req.method === 'POST' && url.pathname === '/v1/auth/social') {
      auth += 1
      return login(req, send)
    }
    if (url.pathname.startsWith('/v1/me/guardian/')) {
      if (req.method === 'POST' && url.pathname === '/v1/me/guardian/links') claims += 1
      else guardian += 1
      return guardianApi(req, url, send)
    }

    if (['/v1/public/form', '/v1/public/form/consent', '/v1/public/form/intake'].includes(url.pathname)) {
      if (req.method === 'GET') forms += 1
      else if (url.pathname.endsWith('/intake')) intakes += 1
      else consents += 1
      return formApi(req, url, send)
    }

    const prefix = prefixOf(String(req.headers['x-report-token'] ?? ''))
    if (prefix === 'down') return req.socket.destroy()
    if (prefix === 'slow') return
    if (prefix in ERRORS) {
      const [status, code] = ERRORS[prefix]
      return send(status, { code, message: '가짜 백엔드의 오류' })
    }
    if (prefix in REPORTS) {
      if (req.method === 'POST' && req.url === '/v1/public/report/viewed') return send(204)
      if (req.method === 'GET' && req.url === '/v1/public/report') return send(200, REPORTS[prefix])
    }
    return send(404, { code: 'REPORT_NOT_FOUND', message: '가짜 백엔드의 오류' })
  })
  .listen(port, '127.0.0.1')
