// 가짜 백엔드 — 토큰(43글자)의 앞머리로 응답을 고르고, 받은 요청을 센다.
// 사용: node tests/server/fake-backend.mjs <포트>
//
//   ok    200 알림장 전체(모든 항목 켬)      gone  410
//   min   200 끈 항목의 칸이 없는 알림장      rate  429
//   vid   200 영상 하나뿐인 알림장            boom  500
//   nf    404 (그 밖의 앞머리도 404)          down  소켓을 끊는다
//                                              slow  응답하지 않고 연결을 붙들고 있는다
// POST /v1/public/report/viewed 도 같은 규칙이고 200 자리에 204 다.
import http from 'node:http'

const port = Number(process.argv[2])
// 미디어 주소는 백엔드 주소(API_BASE_URL = 127.0.0.1)와 글자가 다르게 localhost 로 둔다.
// 실제 서명 주소도 저장소의 주소라 백엔드 주소와 다르다. 첫 HTML 에 백엔드 주소가 없는지 볼 수 있다.
const media = `http://localhost:${port}/media`

let count = 0
let reports = 0 // GET /v1/public/report
let viewed = 0 // POST /v1/public/report/viewed
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

const prefixOf = (token) => ['ok', 'min', 'vid', 'gone', 'rate', 'boom', 'down', 'slow'].find((prefix) => token.startsWith(prefix))

http
  .createServer((req, res) => {
    const send = (status, body) => {
      res.writeHead(status, { 'content-type': 'application/json' })
      res.end(body === undefined ? '' : JSON.stringify(body))
    }
    if (req.url === '/__stats') return send(200, { count, reports, viewed, last })
    if (req.url === '/__reset') {
      count = reports = viewed = 0
      last = null
      return send(200, {})
    }

    count += 1
    if (req.method === 'GET' && req.url === '/v1/public/report') reports += 1
    if (req.method === 'POST' && req.url === '/v1/public/report/viewed') viewed += 1
    // 토큰은 적지 않는다. 웹이 붙인 두 헤더만 남긴다.
    last = {
      method: req.method,
      path: req.url,
      web_secret: req.headers['x-report-web-secret'] ?? null,
      client_ip: req.headers['x-report-client-ip'] ?? null,
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
