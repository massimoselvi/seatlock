import { FALLBACK_ERROR } from './constants'

export function describeError(e: unknown): string {
  return e instanceof Error ? e.message : FALLBACK_ERROR
}
