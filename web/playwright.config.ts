import { defineConfig, devices } from '@playwright/test'

// compose 의 web(next dev)과 개발 스택에 붙는다. 먼저 pnpm e2e:prepare 로 링크를 만든다.
export default defineConfig({
  testDir: 'tests/e2e',
  // test-results 에는 준비 스크립트의 링크 파일이 있다. Playwright 는 outputDir 를 비우므로 한 칸 아래로 둔다.
  outputDir: 'test-results/playwright',
  // 첫 테스트가 "아직 아무도 열지 않은 링크"를 보므로 적힌 순서대로 하나씩 돈다.
  workers: 1,
  use: {
    ...devices['Pixel 7'],
    baseURL: 'http://127.0.0.1:3010',
    trace: 'retain-on-failure',
  },
})
