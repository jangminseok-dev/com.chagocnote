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

/** 앞머리로 시작하는 43글자 토큰. 가짜 백엔드가 앞머리로 응답을 고른다. */
export const token = (prefix) => prefix.padEnd(43, 'A')

const NOT_FOUND_PATHS = ['/', '/nothing', '/r']

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
 * run 은 { web, backend, get, stats } 를 받고, 틀리면 던진다.
 *   get(path, init)  웹 서버에 요청한다(리다이렉트를 따라가지 않는다)
 *   stats()          가짜 백엔드가 받은 요청 — { count, last: { method, path, web_secret, client_ip } | null }
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
  ...['API_BASE_URL', 'REPORT_WEB_SECRET'].map((missing) => ({
    // 프로세스는 끝나지 않는다. 준비에 실패한 채로 모든 요청에 500 을 낸다.
    name: `${missing} 없이 띄우면 모든 요청이 500 이고 오류가 변수 이름을 말한다`,
    async run({ backend }) {
      const env = { API_BASE_URL: backend, REPORT_WEB_SECRET: WEB_SECRET }
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
        assert.ok(!log.includes(WEB_SECRET), '기록에 비밀값이 있다')
      } finally {
        await stop(child)
      }
    },
  })),
]

/** `next start` 를 띄운다. 설정 둘은 env 에 준 것만 있다(셸의 값은 넘기지 않는다). */
function startWeb(port, env, stdio) {
  const { API_BASE_URL, REPORT_WEB_SECRET, ...rest } = process.env
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
    startWeb(webPort, { API_BASE_URL: backend, REPORT_WEB_SECRET: WEB_SECRET }, ['ignore', 'ignore', 'inherit']),
  ]

  let failed = 0
  try {
    await waitUntilUp(`${backend}/__stats`, children[0])
    await waitUntilUp(web, children[1])

    const context = {
      web,
      backend,
      get: (path, init) => fetch(`${web}${path}`, { redirect: 'manual', ...init }),
      stats: async () => (await fetch(`${backend}/__stats`)).json(),
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
