import type { RegistrationStatus } from './types'

export const TOKEN_KEY = 'seatlock.token'

export const FALLBACK_ERROR = 'Something went wrong'

export const MY_STATUS_LABEL: Record<Exclude<RegistrationStatus, 'cancelled'>, string> = {
  confirmed: 'You have a seat',
  waitlisted: 'You are on the waitlist',
}
