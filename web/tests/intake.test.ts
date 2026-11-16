import { expect, test } from 'vitest'
import { bodyOf, consentPartsOf, emptyDraft, problemOf, type IntakeDraft } from '../lib/intake'
import type { OpenIntake } from '../lib/form'

const FORM: OpenIntake = {
  kind: 'intake',
  state: 'open',
  shop: { name: 'Hiss Haus' },
  mode: 'new',
  pet_name: null,
  fields: ['species', 'breed', 'sex', 'neutered', 'birth', 'weight', 'dislikes', 'style'],
  questions: [
    { question_id: 7, label: '산책은 얼마나 하나요?', required: true },
    { question_id: 8, label: '간식은요?', required: false },
  ],
  condition_types: [
    { code: 'heart_disease', label: '심장 질환' },
    { code: 'other', label: '기타' },
  ],
  answered: 0,
  guardian_needed: true,
  keep_days: 30,
  consent: {
    all: false,
    senior_age: 10,
    texts: { basic: { body: '미용 중 생길 수 있는 일' }, senior: { body: '나이가 많은 아이는 쉬어 가며' }, condition: { body: '지병이 나빠질 수 있어요' } },
    digest: 'c'.repeat(64),
  },
}

const FULL: IntakeDraft = {
  ...emptyDraft(),
  guardianName: ' 김민지 ',
  guardianPhone: '010-1234-5678',
  petName: '콩이',
  species: 'dog',
  breed: '말티즈',
  sex: 'female',
  neutered: 'yes',
  birthKind: 'year',
  birthYear: '2021',
  weight: '3.2',
  noConditions: true,
  dislikes: '발 만지기',
  style: '',
  extras: { 7: '하루 한 번' },
  agreed: true,
}

test('다 적은 답에는 걸리는 것이 없다', () => {
  expect(problemOf(FORM, FULL)).toBeNull()
})

test.each<[Partial<IntakeDraft>, string]>([
  [{ guardianName: '  ' }, 'guardianName'],
  [{ guardianPhone: '' }, 'guardianPhone'],
  [{ petName: '' }, 'petName'],
  [{ species: '' }, 'species'],
  [{ breed: ' ' }, 'breed'],
  [{ sex: '' }, 'sex'],
  [{ neutered: '' }, 'neutered'],
  [{ birthKind: '' }, 'birth'],
  [{ birthKind: 'date', birthDate: '' }, 'birth'],
  [{ birthKind: 'year', birthYear: '' }, 'birth'],
  [{ weight: '' }, 'weight'],
  [{ weight: '0' }, 'weight'],
  [{ weight: 'abc' }, 'weight'],
  [{ noConditions: false }, 'conditions'],
  [{ noConditions: false, conditions: [{ code: 'other', customLabel: ' ', note: '' }] }, 'conditions'],
  [{ extras: {} }, 'extra-7'],
  [{ extras: { 7: '  ' } }, 'extra-7'],
  [{ agreed: false }, 'agreed'],
])('켜진 칸이 비면 그 칸을 짚는다 %#', (change, field) => {
  const problem = problemOf(FORM, { ...FULL, ...change })
  expect(problem?.field).toBe(field)
  expect(problem?.message).toMatch(/요$/)
})

test('화면의 위에서부터 처음 걸리는 칸 하나만 짚는다', () => {
  expect(problemOf(FORM, { ...FULL, guardianName: '', petName: '', agreed: false })?.field).toBe('guardianName')
})

test('몰라요와 모르겠어요는 값 없이도 된다', () => {
  expect(problemOf(FORM, { ...FULL, birthKind: 'unknown', birthYear: '', weight: '', weightUnknown: true })).toBeNull()
})

test('매장이 끈 칸과 묻지 않는 보호자 칸은 비어 있어도 된다', () => {
  const form = { ...FORM, fields: ['species'], questions: [], guardian_needed: false }
  const bare = { ...emptyDraft(), petName: '콩이', species: 'dog' as const, noConditions: true, agreed: true }
  expect(problemOf(form, bare)).toBeNull()
})

test('다시 받기는 전부 선택이고 동의만 필수다', () => {
  const form: OpenIntake = { ...FORM, mode: 'update', pet_name: '콩이', guardian_needed: false }
  expect(problemOf(form, { ...emptyDraft(), agreed: true })).toBeNull()
  expect(problemOf(form, emptyDraft())?.field).toBe('agreed')
  expect(problemOf(form, { ...emptyDraft(), agreed: true, weight: 'abc' })?.field).toBe('weight')
})

test('보낼 본문 — 빈 글은 null, 숫자는 숫자로, 끈 칸은 싣지 않는다', () => {
  expect(bodyOf(FORM, FULL, true)).toEqual({
    guardian: { name: '김민지', phone: '010-1234-5678' },
    pet: {
      name: '콩이',
      species: 'dog',
      breed: '말티즈',
      sex: 'female',
      neutered: true,
      birth_date: null,
      birth_year: 2021,
      birth_unknown: false,
      weight_kg: 3.2,
      weight_unknown: false,
      no_known_conditions: true,
      conditions: [],
      dislikes: '발 만지기',
      style: null,
    },
    extras: [{ question_id: 7, body: '하루 한 번' }],
    privacy_agreed: true,
    done: true,
  })
  const hidden = bodyOf({ ...FORM, fields: ['species'], guardian_needed: false }, FULL, false)
  expect(hidden.guardian).toBeNull()
  expect(Object.keys(hidden.pet).sort()).toEqual(['conditions', 'name', 'no_known_conditions', 'species'])
  expect(hidden.done).toBe(false)
})

test('지병을 고르면 한 줄씩 함께 가고 기타는 적은 이름이 간다', () => {
  const body = bodyOf(FORM, {
    ...FULL,
    noConditions: false,
    conditions: [
      { code: 'heart_disease', customLabel: '', note: ' 약 복용 중 ' },
      { code: 'other', customLabel: '슬개골', note: '' },
    ],
  }, true)
  expect(body.pet.no_known_conditions).toBe(false)
  expect(body.pet.conditions).toEqual([
    { type_code: 'heart_disease', custom_label: null, note: '약 복용 중' },
    { type_code: 'other', custom_label: '슬개골', note: null },
  ])
})

test('다시 받기는 적은 것만 싣고 지병을 건드리지 않았으면 답하지 않은 것으로 보낸다', () => {
  const form: OpenIntake = { ...FORM, mode: 'update', pet_name: '콩이', guardian_needed: false, questions: [] }
  const body = bodyOf(form, { ...emptyDraft(), weight: '5.1', agreed: true }, true)
  expect(body.pet).toEqual({ weight_kg: 5.1 })
  expect(body.guardian).toBeNull()
  const cleared = bodyOf(form, { ...emptyDraft(), noConditions: true, agreed: true }, true)
  expect(cleared.pet).toEqual({ no_known_conditions: true, conditions: [] })
})

test('한 줄 칸에 붙여넣은 줄바꿈은 빈칸으로 바뀐다', () => {
  const body = bodyOf(FORM, { ...FULL, breed: '말티즈\n믹스', dislikes: '발\n만지기' }, true)
  expect(body.pet.breed).toBe('말티즈 믹스')
  expect(body.pet.dislikes).toBe('발 만지기')
})

// --- 최종 검토: 서버가 422 로 막는 입력을 브라우저가 먼저 짚는다 ---------------------------------------------------

test.each([
  ['1234'],
  ['010-123-45'],
  ['02-12'],
  ['전화 없음'],
])('전화번호의 모양이 아니면(%s) 그 칸을 짚는다', (phone) => {
  const problem = problemOf(FORM, { ...FULL, guardianPhone: phone })
  expect(problem).toEqual({ field: 'guardianPhone', message: '전화번호를 다시 확인해 주세요' })
})

test.each([
  ['010-1234-5678', '010-1234-5678'],
  ['01012345678', '01012345678'],
  ['02-123-4567', '02-123-4567'],
  ['+82 10-1234-5678', '01012345678'], // 자동 채움이 넣는 나라 번호는 0 으로 바꿔 보낸다
  ['82-10-1234-5678', '01012345678'],
])('받는 전화번호 %s', (phone, sent) => {
  expect(problemOf(FORM, { ...FULL, guardianPhone: phone })).toBeNull()
  expect(bodyOf(FORM, { ...FULL, guardianPhone: phone }, true).guardian).toEqual({ name: '김민지', phone: sent })
})

test('생일은 1990년부터 오늘까지다 — 앞날과 치다 만 연도를 짚는다', () => {
  const today = new Date(2026, 10, 16)
  // 노령이면 끝의 동의서가 붙는다(⑪-C1b) — 서명해 둔 답으로 생일의 범위만 본다.
  const signed: IntakeDraft = { ...FULL, signerName: '김민지', signature: 'UE5H', consentAgreed: true }
  const withDate = (birthDate: string) => problemOf(FORM, { ...signed, birthKind: 'date', birthYear: '', birthDate }, today)
  expect(withDate('2026-11-16')).toBeNull()
  expect(withDate('1990-01-01')).toBeNull()
  expect(withDate('2026-11-17')).toEqual({ field: 'birth', message: '생일을 다시 확인해 주세요' })
  expect(withDate('0020-03-04')?.field).toBe('birth')
  expect(withDate('1989-12-31')?.field).toBe('birth')
  expect(problemOf(FORM, { ...FULL, birthYear: '2027' }, today)?.field).toBe('birth')
  expect(problemOf(FORM, { ...FULL, birthYear: '1989' }, today)?.field).toBe('birth')
})

test('몸무게는 소수 첫째 자리까지라고 말한다', () => {
  expect(problemOf(FORM, { ...FULL, weight: '5.12' })?.message).toBe('몸무게를 숫자로, 소수 첫째 자리까지 적어 주세요')
})

test('붙여넣은 글의 제어 문자는 걷어 낸다 — 서버가 받지 않는다', () => {
  const body = bodyOf(FORM, { ...FULL, petName: '콩\u0000이\u001b', dislikes: '발\u007f 만지기' }, true)
  expect(body.pet.name).toBe('콩이')
  expect(body.pet.dislikes).toBe('발 만지기')
})

// ── 문진표 끝의 동의서(⑪-C1b) — 백엔드 `intake_consent.consent_parts` 와 같은 경계 ─────────────────────────

const TODAY = new Date(2026, 10, 16)
const BLANK: IntakeDraft = { ...FULL, birthKind: 'unknown', birthYear: '', noConditions: true, conditions: [] }
const parts = (change: Partial<IntakeDraft>, form: OpenIntake = FORM) => consentPartsOf(form, { ...BLANK, ...change }, TODAY)

test('노령이거나 지병을 골랐을 때만 동의서 토막이 붙는다', () => {
  expect(parts({})).toEqual([])
  expect(parts({ birthKind: 'year', birthYear: '2016' })).toEqual(['basic', 'senior'])
  expect(parts({ birthKind: 'year', birthYear: '2017' })).toEqual([])
  expect(parts({ birthKind: 'date', birthDate: '2016-11-16' })).toEqual(['basic', 'senior'])     // 생일 당일 10살
  expect(parts({ birthKind: 'date', birthDate: '2016-11-17' })).toEqual([])                      // 하루 모자란 9살
  expect(parts({ noConditions: false, conditions: [{ code: 'heart_disease', customLabel: '', note: '' }] })).toEqual(['basic', 'condition'])
  expect(parts({ birthKind: 'year', birthYear: '2010', noConditions: false, conditions: [{ code: 'other', customLabel: '눈물', note: '' }] }))
    .toEqual(['basic', 'senior', 'condition'])
})

test('매장의 노령 나이를 따르고, 모든 아이에게를 켜면 미용 안내만이라도 붙고, 나이 칸을 껐으면 노령이 아니다', () => {
  const eight = { birthKind: 'year' as const, birthYear: '2018' }
  expect(parts(eight)).toEqual([])
  expect(parts(eight, { ...FORM, consent: { ...FORM.consent, senior_age: 8 } })).toEqual(['basic', 'senior'])
  expect(parts({}, { ...FORM, consent: { ...FORM.consent, all: true } })).toEqual(['basic'])
  expect(parts({ birthKind: 'year', birthYear: '2010' }, { ...FORM, fields: FORM.fields.filter((f) => f !== 'birth') })).toEqual([])
})

test('동의서가 붙으면 이름·서명·동의 체크를 차례로 묻는다 — 개인정보 동의보다 먼저(화면의 위)', () => {
  const senior: IntakeDraft = { ...FULL, birthYear: '2014', agreed: false }
  expect(problemOf(FORM, senior, TODAY)?.field).toBe('signerName')
  expect(problemOf(FORM, { ...senior, signerName: '김민지' }, TODAY)?.field).toBe('signature')
  expect(problemOf(FORM, { ...senior, signerName: '김민지', signature: 'UE5H' }, TODAY)?.field).toBe('consentAgreed')
  expect(problemOf(FORM, { ...senior, signerName: '김민지', signature: 'UE5H', consentAgreed: true }, TODAY)?.field).toBe('agreed')
  expect(problemOf(FORM, { ...FULL, agreed: true }, TODAY)).toBeNull()       // 2021년생 — 동의서가 없다
})

test('보낼 본문 — 동의서가 붙었을 때만 지문·읽은 토막·이름·서명을 싣는다', () => {
  const signed: IntakeDraft = { ...FULL, birthYear: '2014', signerName: ' 김민지 ', signature: 'UE5H', consentAgreed: true }
  expect(bodyOf(FORM, signed, true, TODAY).consent).toEqual({
    digest: 'c'.repeat(64), parts: ['basic', 'senior'], signer_name: '김민지', signature_png: 'UE5H',
  })
  expect('consent' in bodyOf(FORM, FULL, true, TODAY)).toBe(false)
})

