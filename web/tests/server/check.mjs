// 서버 응답 검사 — 가짜 백엔드와 `next start` 를 빈 포트에 띄워 상태 코드·헤더·첫 HTML 을 본다.
// 사용: pnpm build && pnpm check:server
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { createServer } from 'node:net'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

// 검사에만 쓰는 값이다. 실제 비밀값이 아니다.
const WEB_SECRET = 'check-server-secret'
const SESSION_SECRET = 'check-server-session-secret-0123456789'

/** 웹 서버의 설정. 가짜 백엔드 하나가 API 와 인증을 함께 맡는다. */
const webEnv = (backend) => ({
  API_BASE_URL: backend,
  REPORT_WEB_SECRET: WEB_SECRET,
  AUTH_BASE_URL: backend,
  WEB_SESSION_SECRET: SESSION_SECRET,
  DEV_LOGIN: '1',
})

/** 앞머리로 시작하는 43글자 토큰. 가짜 백엔드가 앞머리로 응답을 고른다. */
export const token = (prefix) => prefix.padEnd(43, 'A')

const NOT_FOUND_PATHS = ['/', '/nothing', '/r']

/** 형식이 틀린 토큰(R13). 웹이 먼저 걸러 백엔드를 부르지 않는다. */
const MALFORMED_TOKENS = {
  '42글자': token('ok').slice(0, 42),
  '44글자': `${token('ok')}A`,
  '수천 글자': token('ok').padEnd(5000, 'A'),
  '한글': encodeURIComponent('가'.repeat(43)),
  '줄바꿈이 든 값': `ok%0d%0a${'A'.repeat(39)}`,
  '..%2f 가 든 값': `..%2f${'A'.repeat(40)}`,
}

/** 검사에 쓴 토큰 전부 — 웹 서버의 기록에 남으면 안 된다(R18). */
const USED_TOKENS = [...['ok', 'min', 'vid', 'nf', 'gone', 'rate', 'boom', 'down', 'slow'].map(token), ...Object.values(MALFORMED_TOKENS)]

/** 첫 HTML 의 <meta> 값. 없으면 null. */
function meta(html, key) {
  return html.match(new RegExp(`<meta (?:name|property)="${key}" content="([^"]*)"`))?.[1] ?? null
}

function assertBackendNotCalled(stats) {
  assert.equal(stats.count, 0, `백엔드가 불렸다: ${stats.count}번`)
}

/**
 * 백엔드가 매달렸을 때의 요청. 웹은 백엔드를 5초(lib/report.ts) 기다린 뒤 답해야 한다.
 * 6초 안에 답이 끝나지 않으면 실패다 — 페이지가 끝없이 돌면 안 된다.
 */
async function timed(get, path, init) {
  const started = Date.now()
  let res, body
  try {
    res = await get(path, { ...init, signal: AbortSignal.timeout(6000) })
    body = await res.text()
  } catch {
    assert.fail('6초 안에 답이 끝나지 않았다')
  }
  const elapsed = Date.now() - started
  assert.ok(elapsed >= 5000, `5초보다 일찍 답했다: ${elapsed}ms`)
  return { res, body }
}

function hasHeaderSet(res) {
  assert.equal(res.headers.get('x-robots-tag'), 'noindex, nofollow', 'X-Robots-Tag 가 다르다')
  assert.equal(res.headers.get('referrer-policy'), 'no-referrer', 'Referrer-Policy 가 다르다')
  // 없는 경로의 404 는 Next 가 Cache-Control 을 자기 값으로 바꾼다. 두 낱말이 있는지만 본다.
  const cacheControl = res.headers.get('cache-control') ?? ''
  assert.ok(cacheControl.includes('private'), `Cache-Control 에 private 이 없다: ${cacheControl}`)
  assert.ok(cacheControl.includes('no-store'), `Cache-Control 에 no-store 가 없다: ${cacheControl}`)
}

/**
 * 검사 목록. 뒤 작업은 여기에 줄을 더한다.
 * run 은 { web, backend, get, stats, log } 를 받고, 틀리면 던진다.
 *   get(path, init)  웹 서버에 요청한다(리다이렉트를 따라가지 않는다)
 *   stats()          가짜 백엔드가 받은 요청 — { count, reports, viewed, last: { method, path, web_secret, client_ip } | null }
 *                    reports 는 알림장 조회, viewed 는 열람 신호의 수다
 *   log()            지금까지 `next start` 가 표준 출력·오류에 쓴 것
 * 가짜 백엔드의 요청 수는 검사마다 0 에서 시작한다.
 */
const checks = [
  ...NOT_FOUND_PATHS.map((path) => ({
    name: `${path} 는 404 이고 "알림장을 찾을 수 없어요" 를 서버가 그린다`,
    async run({ get }) {
      const res = await get(path)
      assert.equal(res.status, 404)
      assert.match(await res.text(), /<h1[^>]*>알림장을 찾을 수 없어요<\/h1>/)
    },
  })),
  ...NOT_FOUND_PATHS.map((path) => ({
    name: `${path} 의 응답에 헤더 셋이 있다`,
    async run({ get }) {
      hasHeaderSet(await get(path))
    },
  })),
  {
    name: '글꼴 응답에는 no-store 가 없다',
    async run({ web, get }) {
      // 글꼴 주소는 첫 HTML 이 부르는 스타일시트 안에 있다.
      const html = await (await get('/nothing')).text()
      const sheets = new Set(html.match(/\/_next\/static\/[^"]+\.css/g))
      const fonts = new Set()
      for (const sheet of sheets) {
        const css = await (await get(sheet)).text()
        for (const [, url] of css.matchAll(/url\(([^)]+\.woff2)\)/g)) fonts.add(new URL(url, `${web}${sheet}`).pathname)
      }
      assert.equal(fonts.size, 3, `글꼴 주소가 셋이 아니다: ${fonts.size}`)
      const res = await get([...fonts][0])
      assert.equal(res.status, 200)
      assert.equal(res.headers.get('content-type'), 'font/woff2')
      const cacheControl = res.headers.get('cache-control') ?? ''
      assert.ok(!cacheControl.includes('no-store'), `글꼴의 Cache-Control 에 no-store 가 있다: ${cacheControl}`)
    },
  },
  {
    name: '404 HTML 에 외부 도메인 주소가 없다',
    async run({ web, get }) {
      const html = await (await get('/nothing')).text()
      const outside = (html.match(/https?:\/\/[^\s"'<>\\)]+/g) ?? []).filter((url) => !url.startsWith(web))
      assert.deepEqual(outside, [])
    },
  },
  {
    name: 'X-Powered-By 가 없다',
    async run({ get }) {
      assert.equal((await get('/nothing')).headers.get('x-powered-by'), null)
    },
  },
  {
    name: '알림장은 200 이고 첫 HTML 에 제목·케어 메모·미리보기 정보가 있다',
    async run({ get }) {
      const res = await get(`/r/${token('ok')}`)
      assert.equal(res.status, 200)
      const html = await res.text()
      assert.match(html, /<h1[^>]*>두부의 미용 알림장<\/h1>/)
      assert.ok(html.includes('드라이할 때 조금 긴장했지만'), '케어 메모가 없다')
      assert.equal(meta(html, 'og:title'), '두부의 미용 알림장')
      assert.equal(meta(html, 'og:description'), '9월 28일 · Hiss Haus')
      assert.ok(meta(html, 'og:image')?.includes('/media/display/after-1.jpg'), 'og:image 가 대표 주소가 아니다')
      assert.equal(meta(html, 'og:image:width'), '1200')
      assert.equal(meta(html, 'og:image:height'), '1600')
      assert.equal(meta(html, 'og:type'), 'website')
      assert.equal(meta(html, 'og:url'), null, 'og:url 이 있다')
      assert.ok(!html.includes('rel="canonical"'), 'canonical 이 있다')
      assert.match(meta(html, 'robots') ?? '', /noindex/)
    },
  },
  {
    // og:title·og:image 의 </head> 앞 위치는 이 페이지 구조(작은 Suspense 하나)에서는 설정 없이도 항상 참이라 판별력이 없다.
    // 대신 <body> 바로 뒤 이어붙임 표시(<div hidden>...)의 있고 없음이 Next 가 이 로봇을 htmlLimitedBots 로 인식했는지를 드러낸다 —
    // 스트리밍 가능한 클라이언트(로봇이 아니거나 기본 목록에 없는 로봇)에게만 이 표시가 붙는다. kakaotalk-scrap 이 htmlLimitedBots 에서 빠지면 이 줄이 실패한다.
    name: '카카오톡 미리보기 로봇에게는 og 태그가 </head> 앞에 오고 Next 가 막힌 렌더링으로 인식한다',
    async run({ get }) {
      const html = await (await get(`/r/${token('ok')}`, { headers: { 'User-Agent': 'kakaotalk-scrap/1.0' } })).text()
      const headEnd = html.indexOf('</head>')
      assert.ok(headEnd > -1, '</head> 가 없다')
      const titleIndex = html.indexOf('property="og:title"')
      const imageIndex = html.indexOf('property="og:image"')
      assert.ok(titleIndex > -1 && titleIndex < headEnd, 'og:title 이 </head> 앞에 없다')
      assert.ok(imageIndex > -1 && imageIndex < headEnd, 'og:image 가 </head> 앞에 없다')
      assert.ok(
        !html.includes('<div hidden=""><!--$--><!--/$--></div>'),
        'Next 가 이 로봇을 htmlLimitedBots 로 인식하지 않았다(스트리밍용 이어붙임 표시가 있다)',
      )
    },
  },
  {
    name: '알림장의 응답에 헤더 셋이 있고 Cache-Control 은 private, no-store 그대로다',
    async run({ get }) {
      const res = await get(`/r/${token('ok')}`)
      hasHeaderSet(res)
      assert.equal(res.headers.get('cache-control'), 'private, no-store')
    },
  },
  {
    name: '알림장을 열면 백엔드 조회는 한 번이고 열람 신호는 보내지 않는다',
    async run({ get, stats }) {
      await (await get(`/r/${token('ok')}`)).text()
      const { count, reports, viewed } = await stats()
      assert.equal(reports, 1, `조회 호출 수: ${reports}`)
      assert.equal(viewed, 0, `페이지 GET 만으로 열람 신호가 나갔다: ${viewed}`)
      assert.equal(count, 1)
    },
  },
  {
    name: '백엔드는 웹 비밀값과 접속 주소를 받는다',
    async run({ get, stats }) {
      await (await get(`/r/${token('ok')}`)).text()
      const { last } = await stats()
      assert.equal(last.web_secret, WEB_SECRET)
      assert.ok(last.client_ip, '접속 주소가 없다')
    },
  },
  {
    name: 'X-Forwarded-For 의 첫 값이 접속 주소로 넘어간다',
    async run({ get, stats }) {
      await (await get(`/r/${token('ok')}`, { headers: { 'X-Forwarded-For': '203.0.113.9' } })).text()
      assert.equal((await stats()).last.client_ip, '203.0.113.9')
    },
  },
  {
    name: '첫 HTML 에 비밀값과 백엔드 주소가 없다',
    async run({ backend, get }) {
      const html = await (await get(`/r/${token('ok')}`)).text()
      assert.ok(!html.includes(WEB_SECRET), '비밀값이 있다')
      assert.ok(!html.includes(backend), '백엔드 주소가 있다')
    },
  },
  {
    name: '끈 항목이 없는 알림장은 그 구역이 없고 미리보기 그림은 기본 그림이다',
    async run({ web, get }) {
      const res = await get(`/r/${token('min')}`)
      assert.equal(res.status, 200)
      const html = await res.text()
      assert.match(html, /<h1[^>]*>미용 알림장<\/h1>/)
      assert.ok(!html.includes('오늘의 케어'), '오늘의 케어가 있다')
      assert.ok(!html.includes('data-section="shop"'), '매장 구역이 있다')
      assert.equal(meta(html, 'og:title'), '미용 알림장')
      assert.equal(meta(html, 'og:description'), '9월 28일')
      assert.equal(meta(html, 'og:image'), `${web}/og-default.png`)
    },
  },
  {
    name: '기본 미리보기 그림은 PNG 로 받아지고 no-store 가 없다',
    async run({ get }) {
      const res = await get('/og-default.png')
      assert.equal(res.status, 200)
      assert.equal(res.headers.get('content-type'), 'image/png')
      // 토큰과 상관없는 공통 그림이다. 미리보기 로봇이 캐시 금지 그림을 버리지 않게 한다.
      const cacheControl = res.headers.get('cache-control') ?? ''
      assert.ok(!cacheControl.includes('no-store'), `기본 그림의 Cache-Control 에 no-store 가 있다: ${cacheControl}`)
    },
  },
  {
    name: '없는 알림장은 404 다',
    async run({ get }) {
      assert.equal((await get(`/r/${token('nf')}`)).status, 404)
    },
  },
  {
    name: '닫힌 알림장은 200 이고 매장 정보와 미리보기 그림이 없다',
    async run({ get }) {
      const res = await get(`/r/${token('gone')}`)
      assert.equal(res.status, 200)
      hasHeaderSet(res)
      const html = await res.text()
      assert.match(html, /<h1[^>]*>닫힌 알림장이에요<\/h1>/)
      assert.ok(html.includes('매장에 다시 요청해 주세요.'), '설명이 없다')
      assert.ok(!html.includes('Hiss Haus') && !html.includes('tel:'), '매장 정보가 있다')
      assert.equal(meta(html, 'og:image'), null, 'og:image 가 있다')
      assert.match(html, /<title>차곡노트 미용 알림장<\/title>/)
    },
  },
  ...['rate', 'boom', 'down'].map((prefix) => ({
    name: `${prefix} 알림장은 200 이고 "잠시 후 다시 열어 주세요" 다`,
    async run({ get }) {
      const res = await get(`/r/${token(prefix)}`)
      assert.equal(res.status, 200)
      assert.match(await res.text(), /<h1[^>]*>잠시 후 다시 열어 주세요<\/h1>/)
    },
  })),
  {
    name: '백엔드가 응답하지 않으면 5초 남짓 뒤 200 이고 "잠시 후 다시 열어 주세요" 다',
    async run({ get }) {
      const { res, body } = await timed(get, `/r/${token('slow')}`)
      assert.equal(res.status, 200)
      assert.match(body, /<h1[^>]*>잠시 후 다시 열어 주세요<\/h1>/)
    },
  },
  {
    name: '영상만 있는 알림장은 200 이고 미리보기 그림이 영상의 포스터다',
    async run({ web, get }) {
      const res = await get(`/r/${token('vid')}`)
      assert.equal(res.status, 200)
      const html = await res.text()
      const image = meta(html, 'og:image')
      assert.ok(image?.includes('/media/poster/only.jpg'), 'og:image 가 포스터 주소가 아니다')
      assert.notEqual(image, `${web}/og-default.png`, 'og:image 가 기본 그림이다')
      assert.equal(meta(html, 'og:image:width'), '1080')
      assert.equal(meta(html, 'og:image:height'), '1920')
      assert.ok(html.includes('data-play'), '첫 HTML 에 재생 표시가 없다')
    },
  },
  {
    name: '빈 토큰(/r/)은 404 로 끝나고 백엔드를 부르지 않는다',
    async run({ web, get, stats }) {
      let res = await get('/r/')
      if (res.status === 308) res = await get(new URL(res.headers.get('location'), web).pathname)
      assert.equal(res.status, 404)
      assertBackendNotCalled(await stats())
    },
  },
  ...Object.entries(MALFORMED_TOKENS).map(([label, value]) => ({
    name: `${label} 토큰은 404 이고 백엔드를 부르지 않는다`,
    async run({ get, stats }) {
      assert.equal((await get(`/r/${value}`)).status, 404)
      assertBackendNotCalled(await stats())
    },
  })),
  ...[
    ['ok', 204],
    ['gone', 410],
    ['nf', 404],
    ['rate', 429],
    ['boom', 503],
    ['down', 503],
  ].map(([prefix, status]) => ({
    name: `${prefix} 알림장의 열람 신호는 ${status} 이고 본문이 없다`,
    async run({ get, stats }) {
      const res = await get(`/r/${token(prefix)}/viewed`, { method: 'POST', headers: { 'X-Forwarded-For': '203.0.113.9' } })
      assert.equal(res.status, status)
      assert.equal(await res.text(), '')
      hasHeaderSet(res)
      const { viewed, last } = await stats()
      assert.equal(viewed, 1)
      assert.equal(last.web_secret, WEB_SECRET)
      assert.equal(last.client_ip, '203.0.113.9')
    },
  })),
  {
    name: '백엔드가 응답하지 않으면 열람 신호는 5초 남짓 뒤 503 이다',
    async run({ get }) {
      const { res, body } = await timed(get, `/r/${token('slow')}/viewed`, { method: 'POST' })
      assert.equal(res.status, 503)
      assert.equal(body, '')
    },
  },
  {
    name: '형식이 틀린 토큰의 열람 신호는 404 이고 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      assert.equal((await get(`/r/${MALFORMED_TOKENS['44글자']}/viewed`, { method: 'POST' })).status, 404)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '다른 사이트에서 온 열람 신호는 403 이고 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      const res = await get(`/r/${token('ok')}/viewed`, { method: 'POST', headers: { 'Sec-Fetch-Site': 'cross-site' } })
      assert.equal(res.status, 403)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '열람 신호를 GET 으로 부르면 405 이고 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      assert.equal((await get(`/r/${token('ok')}/viewed`)).status, 405)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '같은 출처의 열람 신호는 통과한다',
    async run({ get }) {
      const res = await get(`/r/${token('ok')}/viewed`, { method: 'POST', headers: { 'Sec-Fetch-Site': 'same-origin' } })
      assert.equal(res.status, 204)
    },
  },
  ...['API_BASE_URL', 'REPORT_WEB_SECRET', 'AUTH_BASE_URL', 'WEB_SESSION_SECRET'].map((missing) => ({
    // 프로세스는 끝나지 않는다. 준비에 실패한 채로 모든 요청에 500 을 낸다.
    name: `${missing} 없이 띄우면 모든 요청이 500 이고 오류가 변수 이름을 말한다`,
    async run({ backend }) {
      const env = webEnv(backend)
      delete env[missing]
      const port = await freePort()
      const child = startWeb(port, env, ['ignore', 'pipe', 'pipe'])
      let log = ''
      child.stdout.on('data', (chunk) => (log += chunk))
      child.stderr.on('data', (chunk) => (log += chunk))
      try {
        await waitUntilUp(`http://127.0.0.1:${port}`, child)
        for (const path of ['/nothing', `/r/${token('ok')}`]) {
          const res = await fetch(`http://127.0.0.1:${port}${path}`)
          assert.equal(res.status, 500, `${path} 가 500 이 아니다: ${res.status}`)
          assert.ok(!(await res.text()).includes(missing), `${path} 의 응답에 변수 이름이 있다`)
        }
        assert.match(log, new RegExp(`환경 변수 ${missing} 이 없다`))
        assert.ok(!log.includes(WEB_SECRET) && !log.includes(SESSION_SECRET), '기록에 비밀값이 있다')
      } finally {
        await stop(child)
      }
    },
  })),
  {
    // 맨 끝에 둔다 — 앞의 요청을 다 보낸 뒤의 기록을 본다.
    name: '웹 서버의 기록에 토큰과 비밀값이 없다',
    async run({ log }) {
      const text = log()
      for (const value of [...USED_TOKENS, ...USED_TOKENS.map(decodeURIComponent)]) {
        assert.ok(!text.includes(value), '기록에 검사에 쓴 토큰이 있다')
      }
      assert.ok(!text.includes(WEB_SECRET) && !text.includes(SESSION_SECRET), '기록에 비밀값이 있다')
    },
  },
]

/** `next start` 를 띄운다. 설정은 env 에 준 것만 있다(셸의 값은 넘기지 않는다). */
function startWeb(port, env, stdio) {
  const { API_BASE_URL, REPORT_WEB_SECRET, AUTH_BASE_URL, WEB_SESSION_SECRET, DEV_LOGIN, ...rest } = process.env
  return spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '-p', String(port), '-H', '127.0.0.1'], {
    cwd: root,
    stdio,
    env: { ...rest, ...env },
  })
}

function freePort() {
  return new Promise((done, fail) => {
    const server = createServer()
    server.on('error', fail)
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close(() => done(port))
    })
  })
}

async function waitUntilUp(url, child) {
  for (let i = 0; i < 100; i += 1) {
    if (child.exitCode !== null) throw new Error(`서버가 뜨지 못했다: ${url}`)
    try {
      await fetch(url)
      return
    } catch {
      await new Promise((done) => setTimeout(done, 100))
    }
  }
  throw new Error(`서버가 10초 안에 뜨지 않았다: ${url}`)
}

function stop(child) {
  if (child.exitCode !== null) return Promise.resolve()
  return new Promise((done) => {
    child.on('exit', done)
    child.kill()
  })
}

async function main() {
  if (!existsSync(resolve(root, '.next/BUILD_ID'))) {
    console.error('빌드가 없다. 먼저 `pnpm build` 를 돌린다.')
    return 1
  }

  const backendPort = await freePort()
  const webPort = await freePort()
  const backend = `http://127.0.0.1:${backendPort}`
  const web = `http://127.0.0.1:${webPort}`

  const children = [
    spawn(process.execPath, ['tests/server/fake-backend.mjs', String(backendPort)], { cwd: root, stdio: 'inherit' }),
startWeb(webPort, webEnv(backend), ['ignore', 'pipe', 'pipe']),
  ]
  let webLog = ''
  children[1].stdout.on('data', (chunk) => (webLog += chunk))
  children[1].stderr.on('data', (chunk) => {
    webLog += chunk
    process.stderr.write(chunk)
  })

  let failed = 0
  try {
    await waitUntilUp(`${backend}/__stats`, children[0])
    await waitUntilUp(web, children[1])

    const context = {
      web,
      backend,
      get: (path, init) => fetch(`${web}${path}`, { redirect: 'manual', ...init }),
      stats: async () => (await fetch(`${backend}/__stats`)).json(),
      log: () => webLog,
    }
    for (const { name, run } of checks) {
      await fetch(`${backend}/__reset`, { method: 'POST' })
      try {
        await run(context)
        console.log(`ok   ${name}`)
      } catch (error) {
        failed += 1
        console.log(`FAIL ${name}\n     ${String(error.message).split('\n')[0]}`)
      }
    }
  } finally {
    await Promise.all(children.map(stop))
  }

  console.log(`\n검사 ${checks.length}줄, 실패 ${failed}줄`)
  return failed === 0 ? 0 : 1
}

process.exitCode = await main()
