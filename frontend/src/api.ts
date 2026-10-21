export interface Workshop {
  id: number
  title: string
  description: string
  starts_at: string
  capacity: number
  seats_taken: number
  seats_left: number
}

export type RegistrationStatus = 'confirmed' | 'waitlisted' | 'cancelled'

export interface Registration {
  id: number
  workshop: number
  workshop_title: string
  status: RegistrationStatus
  created_at: string
}

export interface User {
  id: number
  username: string
  email: string
  is_staff: boolean
}

export interface OrganizerWorkshop extends Workshop {
  waitlist_size: number
}

export interface OrganizerRegistration {
  id: number
  username: string
  email: string
  status: RegistrationStatus
  created_at: string
}

interface Page<T> {
  results: T[]
}

const TOKEN_KEY = 'seatlock.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be blocked; the session then lasts until reload.
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

// DRF returns {field: ["msg"]} or {detail: "msg"}; flatten it into one readable line.
function messageFrom(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const parts = Object.values(body as Record<string, unknown>).flatMap((v) =>
      Array.isArray(v) ? v.map(String) : [String(v)],
    )
    if (parts.length) return parts.join(' ')
  }
  return `API error ${status}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Token ${token}`)

  const response = await fetch(`/api${path}`, { ...init, headers })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, messageFrom(body, response.status))
  return body as T
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: 'POST', body: data ? JSON.stringify(data) : undefined })

export const fetchWorkshops = async () => (await request<Page<Workshop>>('/workshops/')).results
export const fetchMyRegistrations = async () =>
  (await request<Page<Registration>>('/registrations/')).results

export const register = (workshopId: number) =>
  post<Registration>(`/workshops/${workshopId}/register/`)
export const cancel = (registrationId: number) =>
  post<Registration>(`/registrations/${registrationId}/cancel/`)

export const signup = (data: { username: string; email: string; password: string }) =>
  post<{ token: string; user: User }>('/auth/signup/', data)
export const login = (data: { username: string; password: string }) =>
  post<{ token: string }>('/auth/login/', data)
export const logout = () => post<void>('/auth/logout/')
export const fetchMe = () => request<User>('/auth/me/')

export const fetchOrganizerWorkshops = async () =>
  (await request<Page<OrganizerWorkshop>>('/organizer/workshops/')).results
export const fetchOrganizerRegistrations = (workshopId: number) =>
  request<OrganizerRegistration[]>(`/organizer/workshops/${workshopId}/registrations/`)
