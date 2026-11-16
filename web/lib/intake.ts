import type { OpenIntake } from './form'

/** 자주 쓰는 품종 — 고르면 글자를 치지 않는다. 없으면 `직접 적기`. */
export const BREEDS: Record<'dog' | 'cat', string[]> = {
  dog: ['말티즈', '푸들', '포메라니안', '비숑 프리제', '시츄', '요크셔테리어', '치와와', '말티푸', '믹스'],
  cat: ['코리안 숏헤어', '페르시안', '러시안 블루', '브리티시 숏헤어', '랙돌', '믹스'],
}

export type ConditionDraft = { code: string; customLabel: string; note: string }

/** 화면에 적힌 그대로. 글자 칸은 문자열, 고르는 칸은 고르기 전이 빈 문자열이다. */
export type IntakeDraft = {
  guardianName: string
  guardianPhone: string
  petName: string
  species: '' | 'dog' | 'cat'
  breed: string
  sex: '' | 'female' | 'male'
  neutered: '' | 'yes' | 'no'
  birthKind: '' | 'date' | 'year' | 'unknown'
  birthDate: string // YYYY-MM-DD
  birthYear: string
  weight: string
  weightUnknown: boolean
  noConditions: boolean // 없어요
  conditions: ConditionDraft[]
  dislikes: string
  style: string
  extras: Record<number, string> // 질문 ID → 답
  agreed: boolean
}

export function emptyDraft(): IntakeDraft {
  return {
    guardianName: '', guardianPhone: '', petName: '', species: '', breed: '', sex: '', neutered: '',
    birthKind: '', birthDate: '', birthYear: '', weight: '', weightUnknown: false, noConditions: false,
    conditions: [], dislikes: '', style: '', extras: {}, agreed: false,
  }
}

export type Problem = { field: string; message: string }

/** 한 줄 칸의 글 — 앞뒤 공백을 없애고, 붙여넣은 줄바꿈·탭은 빈칸으로 바꾼다. */
function line(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function weightOf(value: string): number | null {
  const text = value.trim()
  if (!/^\d{1,3}(\.\d)?$/.test(text)) return null
  const kg = Number(text)
  return kg > 0 ? kg : null
}

const OTHER = 'other'

/**
 * 처음 걸리는 칸 하나(화면의 위에서부터). 없으면 null — 있으면 보내지 않고 그 칸을 짚는다.
 * 백엔드의 규칙과 같다: 켜진 칸은 필수, 끈 칸은 보지 않는다, 다시 받기(update)는 전부 선택.
 */
export function problemOf(form: OpenIntake, draft: IntakeDraft): Problem | null {
  const required = form.mode !== 'update'
  const shown = (code: string) => form.fields.includes(code)
  const need = (field: string, message: string): Problem => ({ field, message })

  if (form.guardian_needed) {
    if (line(draft.guardianName) === '') return need('guardianName', '보호자 이름을 적어 주세요')
    if (line(draft.guardianPhone) === '') return need('guardianPhone', '전화번호를 적어 주세요')
  }
  if (required && line(draft.petName) === '') return need('petName', '아이 이름을 적어 주세요')
  if (required && shown('species') && draft.species === '') return need('species', '강아지인지 고양이인지 골라 주세요')
  if (required && shown('breed') && line(draft.breed) === '') return need('breed', '품종을 고르거나 적어 주세요')
  if (required && shown('sex') && draft.sex === '') return need('sex', '성별을 골라 주세요')
  if (required && shown('neutered') && draft.neutered === '') return need('neutered', '중성화 여부를 골라 주세요')
  if (shown('birth')) {
    if (required && draft.birthKind === '') return need('birth', '생일을 고르거나 몰라요를 골라 주세요')
    if (draft.birthKind === 'date' && draft.birthDate === '') return need('birth', '생일을 골라 주세요')
    if (draft.birthKind === 'year' && !/^\d{4}$/.test(draft.birthYear.trim())) return need('birth', '태어난 해를 골라 주세요')
  }
  if (shown('weight') && !draft.weightUnknown) {
    if (draft.weight.trim() === '') {
      if (required) return need('weight', '몸무게를 적거나 모르겠어요를 골라 주세요')
    } else if (weightOf(draft.weight) === null) {
      return need('weight', '몸무게를 숫자로 적어 주세요')
    }
  }
  const picked = draft.conditions.length > 0
  if (required && !draft.noConditions && !picked) return need('conditions', '지병을 고르거나 없어요를 골라 주세요')
  if (picked && draft.conditions.some((c) => c.code === OTHER && line(c.customLabel) === '')) {
    return need('conditions', '기타 지병의 이름을 적어 주세요')
  }
  if (required) {
    for (const question of form.questions) {
      if (question.required && line(draft.extras[question.question_id] ?? '') === '') {
        return need(`extra-${question.question_id}`, '꼭 답해야 하는 질문이 남아 있어요')
      }
    }
  }
  if (!draft.agreed) return need('agreed', '개인정보 수집·이용 안내에 동의해 주세요')
  return null
}

type Json = Record<string, unknown>

/** 보낼 본문. 끈 칸은 싣지 않고, 빈 글은 null 이다. 다시 받기는 적은 것만 싣는다. */
export function bodyOf(form: OpenIntake, draft: IntakeDraft, done: boolean): { guardian: Json | null; pet: Json; extras: Json[]; privacy_agreed: boolean; done: boolean } {
  const update = form.mode === 'update'
  const shown = (code: string) => form.fields.includes(code)
  const text = (value: string) => (line(value) === '' ? null : line(value))
  const pet: Json = {}
  /** 다시 받기는 적은 칸만 싣는다 — 나머지는 "바뀌지 않음"이다. */
  const put = (key: string, value: unknown, written: boolean) => {
    if (!update || written) pet[key] = value
  }

  put('name', text(draft.petName), line(draft.petName) !== '')
  if (shown('species')) put('species', draft.species === '' ? null : draft.species, draft.species !== '')
  if (shown('breed')) put('breed', text(draft.breed), line(draft.breed) !== '')
  if (shown('sex')) put('sex', draft.sex === '' ? null : draft.sex, draft.sex !== '')
  if (shown('neutered')) put('neutered', draft.neutered === '' ? null : draft.neutered === 'yes', draft.neutered !== '')
  if (shown('birth') && (!update || draft.birthKind !== '')) {
    pet.birth_date = draft.birthKind === 'date' ? draft.birthDate : null
    pet.birth_year = draft.birthKind === 'year' ? Number(draft.birthYear) : null
    pet.birth_unknown = draft.birthKind === 'unknown'
  }
  if (shown('weight') && (!update || draft.weightUnknown || draft.weight.trim() !== '')) {
    pet.weight_kg = draft.weightUnknown ? null : weightOf(draft.weight)
    if (!update || draft.weightUnknown) pet.weight_unknown = draft.weightUnknown
  }
  const picked = draft.conditions.length > 0
  if (!update || draft.noConditions || picked) {
    pet.no_known_conditions = !picked
    pet.conditions = draft.conditions.map((c) => ({
      type_code: c.code,
      custom_label: c.code === OTHER ? text(c.customLabel) : null,
      note: text(c.note),
    }))
  }
  if (shown('dislikes')) put('dislikes', text(draft.dislikes), line(draft.dislikes) !== '')
  if (shown('style')) put('style', text(draft.style), line(draft.style) !== '')

  return {
    guardian: form.guardian_needed ? { name: line(draft.guardianName), phone: line(draft.guardianPhone) } : null,
    pet,
    extras: form.questions
      .map((question) => ({ question_id: question.question_id, body: line(draft.extras[question.question_id] ?? '') }))
      .filter((extra) => extra.body !== ''),
    privacy_agreed: draft.agreed,
    done,
  }
}
