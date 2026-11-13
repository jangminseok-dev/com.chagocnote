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
const USED_TOKENS = [...['ok', 'min', 'vid', 'nf', 'gone', 'rate', 'boom', 'down', 'slow', 'taken'].map(token), ...Object.values(MALFORMED_TOKENS)]

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

/** 같은 출처의 폼 POST. */
function form(fields, headers = {}) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Sec-Fetch-Site': 'same-origin', ...headers },
    body: new URLSearchParams(fields).toString(),
  }
}

/** 검사에서 받은 쿠키 값 전부 — 웹 서버의 기록에 남으면 안 된다. */
const SEEN_COOKIES = new Set()

/** 응답의 Set-Cookie 가운데 그 이름의 줄. 없으면 null. */
function setCookie(res, name) {
  const line = res.headers.getSetCookie().find((value) => value.startsWith(`${name}=`)) ?? null
  if (line !== null && pair(line).length > name.length + 1) SEEN_COOKIES.add(pair(line).slice(name.length + 1))
  return line
}

/** Set-Cookie 한 줄의 "이름=값" — 다음 요청의 cookie 헤더에 넣는다. */
const pair = (line) => line.split(';')[0]

/** 쿠키를 지우는 줄인가. */
const isDeletion = (line) => /Max-Age=0/i.test(line) || /Expires=Thu, 01 Jan 1970/i.test(line)

/** 쿠키 줄의 속성이 다 있는가. */
function hasAttributes(line, attributes) {
  const parts = line.split(';').map((part) => part.trim().toLowerCase())
  for (const attribute of attributes) assert.ok(parts.includes(attribute.toLowerCase()), `쿠키에 ${attribute} 가 없다`)
}

/** 개발용 로그인을 하고 { res, session }(session 은 cookie 헤더에 넣을 "cn_session=…")을 준다. cookie 는 함께 보낼 쿠키다. */
async function loginAs(get, name, { next, cookie } = {}) {
  const res = await get('/login/dev', form({ name, ...(next !== undefined && { next }) }, cookie ? { cookie } : {}))
  const line = setCookie(res, 'cn_session')
  return { res, session: line === null ? null : pair(line) }
}

/** 세션이 없거나 끝났을 때의 이동 — 307 이고 로그인 뒤 here 로 돌아온다. */
function goesToLogin(res, here) {
  assert.equal(res.status, 307)
  assert.equal(res.headers.get('location'), `/login?next=${encodeURIComponent(here)}`)
}

const loginChecks = [
  {
    name: '/login 은 200 이고 헤더 셋이 있고 폼이 /login/dev 로 간다',
    async run({ get, stats }) {
      const res = await get('/login')
      assert.equal(res.status, 200)
      hasHeaderSet(res)
      const html = await res.text()
      assert.match(html, /<form[^>]*action="\/login\/dev"/)
      assert.match(html, /<h1[^>]*>로그인<\/h1>/)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '로그인하면 303 /me 이고 세션 쿠키가 HttpOnly·Secure·SameSite=lax·Path=/·Max-Age=1800 이며 값에 토큰이 보이지 않는다',
    async run({ get, stats }) {
      const res = await get('/login/dev', form({ name: 'ok' }))
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/me')
      hasHeaderSet(res)
      const line = setCookie(res, 'cn_session')
      assert.ok(line, '세션 쿠키가 없다')
      hasAttributes(line, ['HttpOnly', 'Secure', 'SameSite=lax', 'Path=/', 'Max-Age=1800'])
      assert.ok(!line.includes('tok-ok'), '쿠키에 토큰이 그대로 있다')
      const { auth, count, last } = await stats()
      assert.equal(auth, 1)
      assert.equal(count, 1, '로그인이 인증 말고 다른 곳을 불렀다')
      assert.equal(last.session, 'web')
    },
  },
  {
    name: '돌아갈 경로가 내 기록 아래면 그곳으로, 아니면 /me 로 간다',
    async run({ get }) {
      const to = async (next) => (await loginAs(get, 'ok', { next })).res.headers.get('location')
      assert.equal(await to('/me/11'), '/me/11')
      assert.equal(await to('/me/11?pet=7'), '/me/11?pet=7')
      for (const next of ['//evil.example', 'https://evil.example/me', '/\\evil.example', '/r/x', '/login', '/me/11?cursor=a']) {
        assert.equal(await to(next), '/me', `${next} 로 나갔다`)
      }
    },
  },
  {
    name: '이름이 비었거나 51글자면 303 /login?error=1 이고 인증을 부르지 않는다',
    async run({ get, stats }) {
      for (const name of ['', '   ', 'a'.repeat(51)]) {
        const res = await get('/login/dev', form({ name }))
        assert.equal(res.status, 303)
        assert.equal(res.headers.get('location'), '/login?error=1')
        assert.equal(setCookie(res, 'cn_session'), null)
      }
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '인증이 거절하거나 끊기거나 리프레시 토큰을 주면 303 /login?error=1 이고 세션 쿠키가 없다',
    async run({ get }) {
      for (const name of ['bad', 'down', 'refresh']) {
        const { res, session } = await loginAs(get, name)
        assert.equal(res.status, 303, name)
        assert.equal(res.headers.get('location'), '/login?error=1', name)
        assert.equal(session, null, `${name}: 세션 쿠키가 있다`)
      }
    },
  },
  {
    name: '로그인이 실패하면 돌아갈 경로를 이어 붙이고, 실패 화면에 문구와 그 경로가 있다',
    async run({ get }) {
      const { res } = await loginAs(get, 'bad', { next: '/me/11?pet=7' })
      assert.equal(res.headers.get('location'), '/login?error=1&next=%2Fme%2F11%3Fpet%3D7')
      const html = await (await get(res.headers.get('location'))).text()
      assert.match(html, /로그인하지 못했어요\. 다시 시도해 주세요\./)
      assert.match(html, /name="next"[^>]*value="\/me\/11\?pet=7"/)
    },
  },
  {
    name: '/login 의 next 가 밖을 가리키면 숨은 칸은 /me 다',
    async run({ get }) {
      const html = await (await get('/login?next=%2F%2Fevil.example')).text()
      assert.match(html, /name="next"[^>]*value="\/me"/)
      // Next 는 요청 주소를 첫 HTML 의 라우터 상태(스크립트 안의 글자)에 싣는다. 폼과 링크에 없는지만 본다.
      assert.ok(!/(?:value|href|action)="[^"]*evil\.example/.test(html), '폼·링크에 밖의 주소가 있다')
    },
  },
  {
    name: '다른 출처의 로그인·로그아웃은 403 이고 인증을 부르지 않는다',
    async run({ get, stats }) {
      const cross = { 'Sec-Fetch-Site': 'cross-site' }
      assert.equal((await get('/login/dev', form({ name: 'ok' }, cross))).status, 403)
      assert.equal((await get('/logout', form({}, cross))).status, 403)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '로그아웃은 303 /login 이고 세션 쿠키를 지우며 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      const { session } = await loginAs(get, 'ok')
      const before = (await stats()).count
      const res = await get('/logout', form({}, { cookie: session }))
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/login')
      const line = res.headers.getSetCookie().find((value) => value.startsWith('cn_session='))
      assert.ok(line && isDeletion(line), '세션 쿠키를 지우지 않았다')
      assert.equal((await stats()).count, before, '로그아웃이 백엔드를 불렀다')
    },
  },
  {
    name: '로그인·로그아웃을 GET 으로 부르면 405 다',
    async run({ get }) {
      assert.equal((await get('/login/dev')).status, 405)
      assert.equal((await get('/logout')).status, 405)
    },
  },
  {
    name: 'DEV_LOGIN 없이 띄우면 개발용 로그인은 404 이고 로그인 화면에 폼이 없다',
    async run({ backend, stats }) {
      const env = webEnv(backend)
      delete env.DEV_LOGIN
      const port = await freePort()
      const child = startWeb(port, env, ['ignore', 'ignore', 'ignore'])
      try {
        const base = `http://127.0.0.1:${port}`
        await waitUntilUp(base, child)
        const res = await fetch(`${base}/login/dev`, { redirect: 'manual', ...form({ name: 'ok' }) })
        assert.equal(res.status, 404)
        assert.equal(res.headers.getSetCookie().length, 0)
        const html = await (await fetch(`${base}/login`)).text()
        assert.ok(!html.includes('<form'), '로그인 화면에 폼이 있다')
        assert.match(html, /로그인은 준비 중이에요\./)
        assertBackendNotCalled(await stats())
      } finally {
        await stop(child)
      }
    },
  },
  {
    name: '알림장의 첫 HTML 에 잇기 폼이 있고, 닫힌 알림장에는 폼이 없고 내 기록으로 가는 링크가 있다',
    async run({ get }) {
      const open = await (await get(`/r/${token('ok')}`)).text()
      assert.ok(open.includes(`<form action="/r/${token('ok')}/claim" method="post">`), '잇기 폼이 없다')
      assert.match(open, /<button type="submit">로그인하고 지난 기록 보기<\/button>/)
      const closed = await (await get(`/r/${token('gone')}`)).text()
      assert.ok(!closed.includes('<form'), '닫힌 화면에 폼이 있다')
      assert.match(closed, /<a [^>]*href="\/me"[^>]*>로그인하고 지난 기록 보기<\/a>/)
    },
  },
  {
    name: '세션 없이 잇기를 누르면 303 /login 이고 잇기 쿠키가 HttpOnly·Secure·SameSite=lax·Max-Age=600 이며 값에 토큰이 없고 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      const res = await get(`/r/${token('ok')}/claim`, form({}))
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/login')
      hasHeaderSet(res)
      const line = setCookie(res, 'cn_claim')
      assert.ok(line, '잇기 쿠키가 없다')
      hasAttributes(line, ['HttpOnly', 'Secure', 'SameSite=lax', 'Path=/', 'Max-Age=600'])
      assert.ok(!line.includes(token('ok')), '쿠키에 토큰이 그대로 있다')
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '잇기 쿠키를 들고 로그인하면 303 /me 이고 잇기를 한 번 부르며 잇기 쿠키를 지운다',
    async run({ get, stats }) {
      const claim = pair(setCookie(await get(`/r/${token('ok')}/claim`, form({})), 'cn_claim'))
      // 돌아갈 경로가 있어도 잇기 뒤에는 내 기록으로 간다.
      const { res, session } = await loginAs(get, 'ok', { cookie: claim, next: '/me/12' })
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/me')
      assert.ok(session, '세션 쿠키가 없다')
      const cleared = res.headers.getSetCookie().find((value) => value.startsWith('cn_claim='))
      assert.ok(cleared && isDeletion(cleared), '잇기 쿠키를 지우지 않았다')
      const { auth, claims, count, last } = await stats()
      assert.deepEqual([auth, claims, count], [1, 1, 2])
      assert.equal(last.path, '/v1/me/guardian/links')
      assert.equal(last.report_token, true, '알림장 토큰 헤더가 없다')
      assert.equal(last.bearer, true, '액세스 토큰이 없다')
    },
  },
  {
    name: '이미 다른 계정에 이어진 알림장의 잇기 쿠키로 로그인하면 303 /me?notice=taken',
    async run({ get }) {
      const claim = pair(setCookie(await get(`/r/${token('taken')}/claim`, form({})), 'cn_claim'))
      const { res } = await loginAs(get, 'ok', { cookie: claim })
      assert.equal(res.headers.get('location'), '/me?notice=taken')
    },
  },
  ...['gone', 'rate', 'nf'].map((prefix) => ({
    name: `잇지 못하는 알림장(${prefix})의 잇기 쿠키로 로그인하면 말없이 303 /me 이고 잇기 쿠키를 지운다`,
    async run({ get, stats }) {
      const claim = pair(setCookie(await get(`/r/${token(prefix)}/claim`, form({})), 'cn_claim'))
      const { res, session } = await loginAs(get, 'ok', { cookie: claim })
      assert.equal(res.headers.get('location'), '/me')
      assert.ok(session, '세션 쿠키가 없다')
      const cleared = res.headers.getSetCookie().find((value) => value.startsWith('cn_claim='))
      assert.ok(cleared && isDeletion(cleared), '잇기 쿠키를 지우지 않았다')
      assert.equal((await stats()).claims, 1)
    },
  })),
  {
    name: '잇기 쿠키를 들고 로그인이 실패하면 잇기를 부르지 않고 잇기 쿠키를 건드리지 않는다',
    async run({ get, stats }) {
      const claim = pair(setCookie(await get(`/r/${token('ok')}/claim`, form({})), 'cn_claim'))
      for (const name of ['bad', 'down', '']) {
        const { res } = await loginAs(get, name, { cookie: claim })
        assert.equal(res.headers.get('location'), '/login?error=1', name)
        assert.equal(res.headers.getSetCookie().length, 0, `${name}: 쿠키를 건드렸다`)
      }
      assert.equal((await stats()).claims, 0)
    },
  },
  {
    name: '깨진 잇기 쿠키를 들고 로그인하면 잇기를 부르지 않고 돌아갈 경로로 간다',
    async run({ get, stats }) {
      const { res } = await loginAs(get, 'ok', { cookie: 'cn_claim=garbage', next: '/me/12' })
      assert.equal(res.headers.get('location'), '/me/12')
      assert.equal((await stats()).claims, 0)
    },
  },
  {
    name: '로그인한 채 잇기를 누르면 303 /me 이고 잇기를 한 번 부르며 잇기 쿠키를 쓰지 않는다',
    async run({ get, stats }) {
      const { session } = await loginAs(get, 'ok')
      const res = await get(`/r/${token('ok')}/claim`, form({}, { cookie: session }))
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/me')
      assert.equal(res.headers.getSetCookie().length, 0)
      const { claims, last } = await stats()
      assert.equal(claims, 1)
      assert.equal(last.report_token, true)
      const taken = await get(`/r/${token('taken')}/claim`, form({}, { cookie: session }))
      assert.equal(taken.headers.get('location'), '/me?notice=taken')
      for (const prefix of ['gone', 'rate', 'nf']) {
        assert.equal((await get(`/r/${token(prefix)}/claim`, form({}, { cookie: session }))).headers.get('location'), '/me', prefix)
      }
    },
  },
  {
    name: '끝난 세션으로 잇기를 누르면 303 /login 이고 세션 쿠키를 지우고 잇기 쿠키를 쓴다',
    async run({ get }) {
      const { session } = await loginAs(get, 'expired')
      const res = await get(`/r/${token('ok')}/claim`, form({}, { cookie: session }))
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/login')
      const lines = res.headers.getSetCookie()
      const cleared = lines.find((value) => value.startsWith('cn_session='))
      assert.ok(cleared && isDeletion(cleared), '세션 쿠키를 지우지 않았다')
      assert.ok(setCookie(res, 'cn_claim'), '잇기 쿠키가 없다')
    },
  },
  ...Object.entries(MALFORMED_TOKENS).map(([name, value]) => ({
    name: `형식이 틀린 토큰(${name})의 잇기는 404 이고 쿠키를 쓰지 않으며 백엔드를 부르지 않는다`,
    async run({ get, stats }) {
      const res = await get(`/r/${value}/claim`, form({}))
      assert.equal(res.status, 404)
      assert.equal(res.headers.getSetCookie().length, 0)
      assertBackendNotCalled(await stats())
    },
  })),
  {
    name: '다른 출처의 잇기는 403 이고 쿠키를 쓰지 않으며 백엔드를 부르지 않는다',
    async run({ get, stats, reset }) {
      const { session } = await loginAs(get, 'ok')
      await reset()
      for (const cookie of [undefined, session]) {
        const res = await get(`/r/${token('ok')}/claim`, form({}, { 'Sec-Fetch-Site': 'cross-site', ...(cookie && { cookie }) }))
        assert.equal(res.status, 403)
        assert.equal(res.headers.getSetCookie().length, 0)
      }
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '잇기를 GET 으로 부르면 405 이고 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      assert.equal((await get(`/r/${token('ok')}/claim`)).status, 405)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '세션 없는 /me 는 307 /login?next=%2Fme 이고 헤더 셋이 있으며 백엔드를 부르지 않는다',
    async run({ get, stats }) {
      const res = await get('/me')
      goesToLogin(res, '/me')
      hasHeaderSet(res)
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '깨진 세션 쿠키·잇기 쿠키로 만든 세션 쿠키는 로그인으로 간다(500 이 아니다)',
    async run({ get, stats, reset }) {
      const { session } = await loginAs(get, 'ok')
      const claim = pair(setCookie(await get(`/r/${token('ok')}/claim`, form({})), 'cn_claim'))
      await reset()
      const broken = [
        'cn_session=garbage',
        'cn_session=',
        `cn_session=${'A'.repeat(4000)}`,
        session.slice(0, -6), // 잘린 값
        `cn_session=${claim.slice('cn_claim='.length)}`, // 다른 용도로 봉한 값
      ]
      for (const cookie of broken) goesToLogin(await get('/me', { headers: { cookie } }), '/me')
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '로그인한 /me 는 200 이고 헤더 셋이 있으며 매장과 아이들이 첫 HTML 에 있다',
    async run({ get, stats, backend, reset }) {
      const { session } = await loginAs(get, 'ok')
      await reset()
      const res = await get('/me', { headers: { cookie: session } })
      assert.equal(res.status, 200)
      hasHeaderSet(res)
      // React 는 이어 붙인 글자 사이에 <!-- --> 를 넣는다.
      const html = (await res.text()).replaceAll('<!-- -->', '')
      assert.match(html, /<h1[^>]*>내 기록<\/h1>/)
      for (const text of ['Hiss Haus', '2026년 11월 1일부터', '둘째 매장', '아직 받은 알림장이 없어요', '로그아웃']) {
        assert.ok(html.includes(text), `첫 HTML 에 "${text}" 가 없다`)
      }
      assert.match(html, /<a href="\/me\/11\?pet=7">두부<\/a>/)
      assert.match(html, /<a href="\/me\/11\?pet=8">우리 아이<\/a>/)
      assert.match(html, /<form[^>]*action="\/me\/11\/unlink"/)
      assert.ok(!html.includes('아직 이어진 기록이 없어요'), '연결이 있는데 빈 안내가 있다')
      // 연결 목록 한 번 + 연결 둘의 아이들
      const { guardian, count } = await stats()
      assert.deepEqual([guardian, count], [3, 3])
      assert.ok(!html.includes(backend), '첫 HTML 에 백엔드 주소가 있다')
      assert.ok(!html.includes('tok-'), '첫 HTML 에 액세스 토큰이 있다')
    },
  },
  {
    name: '연결이 없는 계정의 /me 는 "아직 이어진 기록이 없어요" 다',
    async run({ get }) {
      const { session } = await loginAs(get, 'empty')
      const html = await (await get('/me', { headers: { cookie: session } })).text()
      assert.ok(html.includes('아직 이어진 기록이 없어요'))
      assert.ok(!html.includes('data-section="shop"'), '매장 구역이 있다')
    },
  },
  {
    name: '/me?notice=taken 에만 안내가 있다',
    async run({ get }) {
      const { session } = await loginAs(get, 'ok')
      const text = '이미 다른 계정에 이어져 있어요'
      assert.ok((await (await get('/me?notice=taken', { headers: { cookie: session } })).text()).includes(text))
      for (const path of ['/me', '/me?notice=%3Cscript%3E', '/me?notice=taken&notice=x']) {
        assert.ok(!(await (await get(path, { headers: { cookie: session } })).text()).includes(text), path)
      }
    },
  },
  {
    name: '끝난 토큰의 /me 는 307 /login?next=%2Fme 다',
    async run({ get }) {
      const { session } = await loginAs(get, 'expired')
      goesToLogin(await get('/me', { headers: { cookie: session } }), '/me')
    },
  },
  {
    name: '정지된 계정의 /me 는 200 "이 계정으로는 볼 수 없어요" 다',
    async run({ get }) {
      const { session } = await loginAs(get, 'susp')
      const res = await get('/me', { headers: { cookie: session } })
      assert.equal(res.status, 200)
      assert.match(await res.text(), /<h1[^>]*>이 계정으로는 볼 수 없어요<\/h1>/)
    },
  },
  {
    name: '백엔드가 매달리면 /me 는 5초 뒤 200 "잠시 후 다시 열어 주세요" 다',
    async run({ get }) {
      const { session } = await loginAs(get, 'slow')
      const { res, body } = await timed(get, '/me', { headers: { cookie: session } })
      assert.equal(res.status, 200)
      assert.match(body, /<h1[^>]*>잠시 후 다시 열어 주세요<\/h1>/)
    },
  },
  {
    name: '연결 끊기는 303 /me 이고 끊기를 한 번 부른다. 없는 연결도 303 /me 다',
    async run({ get, stats, reset }) {
      const { session } = await loginAs(get, 'ok')
      await reset()
      const res = await get('/me/11/unlink', form({}, { cookie: session }))
      assert.equal(res.status, 303)
      assert.equal(res.headers.get('location'), '/me')
      const { count, last } = await stats()
      assert.equal(count, 1)
      assert.deepEqual([last.method, last.path, last.bearer], ['DELETE', '/v1/me/guardian/links/11', true])
      assert.equal((await get('/me/99/unlink', form({}, { cookie: session }))).headers.get('location'), '/me')
    },
  },
  {
    name: '숫자가 아닌 연결의 끊기는 404 이고 백엔드를 부르지 않는다',
    async run({ get, stats, reset }) {
      const { session } = await loginAs(get, 'ok')
      await reset()
      for (const id of ['abc', '0', '-1', '1e3', '11%0a', '9'.repeat(16)]) {
        assert.equal((await get(`/me/${id}/unlink`, form({}, { cookie: session }))).status, 404, id)
      }
      assertBackendNotCalled(await stats())
    },
  },
  {
    name: '세션 없는 끊기는 303 /login, 끝난 세션의 끊기는 세션 쿠키를 지우고 303 /login, 다른 출처는 403 이다',
    async run({ get, stats, reset }) {
      const none = await get('/me/11/unlink', form({}))
      assert.deepEqual([none.status, none.headers.get('location')], [303, '/login'])
      const { session: expired } = await loginAs(get, 'expired')
      const ended = await get('/me/11/unlink', form({}, { cookie: expired }))
      assert.deepEqual([ended.status, ended.headers.get('location')], [303, '/login'])
      const cleared = ended.headers.getSetCookie().find((value) => value.startsWith('cn_session='))
      assert.ok(cleared && isDeletion(cleared), '세션 쿠키를 지우지 않았다')
      const { session } = await loginAs(get, 'ok')
      await reset()
      assert.equal((await get('/me/11/unlink', form({}, { cookie: session, 'Sec-Fetch-Site': 'cross-site' }))).status, 403)
      assert.equal((await get('/me/11/unlink')).status, 405)
      assertBackendNotCalled(await stats())
    },
  },
  // (보호자 검사는 이 위에 더한다)
]

/**
 * 검사 목록. 뒤 작업은 여기에 줄을 더한다.
 * run 은 { web, backend, get, stats, log } 를 받고, 틀리면 던진다.
 *   get(path, init)  웹 서버에 요청한다(리다이렉트를 따라가지 않는다)
 *   reset()          가짜 백엔드의 요청 수를 0 으로(검사 안에서 준비 요청을 빼고 셀 때)
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
  ...loginChecks,
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
      // 가짜 인증이 내주는 액세스 토큰은 tok- 으로 시작한다.
      assert.ok(!text.includes('tok-'), '기록에 액세스 토큰이 있다')
      assert.ok(SEEN_COOKIES.size > 0, '쿠키를 하나도 받지 못했다')
      for (const value of SEEN_COOKIES) assert.ok(!text.includes(value), '기록에 쿠키 값이 있다')
      assert.ok(!text.includes('X-Amz-Signature'), '기록에 서명 주소가 있다')
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
      reset: () => fetch(`${backend}/__reset`, { method: 'POST' }),
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
