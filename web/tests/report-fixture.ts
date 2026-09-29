// 테스트용 알림장. 주소는 가짜다 — 아무것도 가져오지 않는다.
import type { Media, Report } from '../lib/report'

export function makeMedia(overrides: Partial<Media> = {}): Media {
  return {
    kind: 'photo',
    phase: 'after',
    width: 1200,
    height: 1600,
    duration_seconds: null,
    display_url: 'https://media.test/display.jpg',
    thumb_url: 'https://media.test/thumb.jpg',
    download_url: 'https://media.test/download.jpg',
    ...overrides,
  }
}

export function makeVideo(overrides: Partial<Media> = {}): Media {
  return makeMedia({
    kind: 'video',
    width: 1080,
    height: 1920,
    duration_seconds: 18,
    display_url: 'https://media.test/video.mp4',
    thumb_url: 'https://media.test/poster.jpg',
    download_url: 'https://media.test/video-download.mp4',
    ...overrides,
  })
}

/** 매장이 항목을 모두 끈 알림장 — 칸이 여섯뿐이다. 미디어는 후 사진 2·후 영상 1·전 사진 2. */
export function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    pet_name: '두부',
    visit_date: '2026-09-28',
    care_note: '오늘 두부가 드라이할 때 조금 긴장했지만 끝까지 잘 참아 줬어요.',
    media: [
      makeMedia(),
      makeMedia(),
      makeVideo(),
      makeMedia({ phase: 'before' }),
      makeMedia({ phase: 'before' }),
    ],
    cover: { url: 'https://media.test/cover.jpg', width: 1200, height: 1600 },
    expires_at: '2026-10-28T23:59:59+09:00',
    ...overrides,
  }
}

/** 매장이 항목을 모두 켠 알림장. */
export function makeFullReport(overrides: Partial<Report> = {}): Report {
  return makeReport({
    menus: [
      { name: '전체 미용', amount: 55000 },
      { name: '스파', amount: 15000 },
    ],
    total_amount: 70000,
    weight_kg: 4.2,
    shop: { name: 'Hiss Haus', phone: '02-123-4567', address: '서울 마포구 ○○로 12, 1층' },
    ...overrides,
  })
}
