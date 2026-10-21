import { describe, expect, it } from 'vitest'
import { FALLBACK_ERROR } from './constants'
import { describeError } from './utils'

describe('describeError', () => {
  it('returns the message of an Error', () => {
    expect(describeError(new Error('Seat taken'))).toBe('Seat taken')
  })

  it('falls back for anything that is not an Error', () => {
    expect(describeError('boom')).toBe(FALLBACK_ERROR)
    expect(describeError(null)).toBe(FALLBACK_ERROR)
  })
})
