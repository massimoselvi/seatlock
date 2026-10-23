// @env browser
import type { OrganizerRegistration, OrganizerWorkshop, Registration, User, Workshop } from './types'
import { TOKEN_KEY } from './constants'

interface Page<T> {
  results: T[]
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  }
  catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token)
      localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  }
  catch {
    // Storage can be blocked; the session then lasts until reload.
  }
}

class ApiError extends Error {
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
    const parts = Object.values(body as Record<string, unknown>).flatMap(v =>
      Array.isArray(v) ? v.map(String) : [String(v)],
    )
    if (parts.length)
      return parts.join(' ')
  }
  return `API error ${status}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body)
    headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token)
    headers.set('Authorization', `Token ${token}`)

  const response = await fetch(`/api${path}`, { ...init, headers })
  if (response.status === 204)
    return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok)
    throw new ApiError(response.status, messageFrom(body, response.status))
  // Every API success is JSON. An HTML page here means a proxy answered in place of the API.
  if (body === null)
    throw new ApiError(response.status, 'Unexpected response from the server.')
  return body as T
}

function post<T>(path: string, data?: unknown) {
  return request<T>(path, { method: 'POST', body: data ? JSON.stringify(data) : undefined })
}

export const fetchWorkshops = async () => (await request<Page<Workshop>>('/workshops/')).results
export async function fetchMyRegistrations() {
  return (await request<Page<Registration>>('/registrations/')).results
}

export function register(workshopId: number) {
  return post<Registration>(`/workshops/${workshopId}/register/`)
}
export function cancel(registrationId: number) {
  return post<Registration>(`/registrations/${registrationId}/cancel/`)
}

export function signup(data: { username: string, email: string, password: string }) {
  return post<{ token: string, user: User }>('/auth/signup/', data)
}
export function login(data: { username: string, password: string }) {
  return post<{ token: string }>('/auth/login/', data)
}
export const logout = () => post<void>('/auth/logout/')
export const fetchMe = () => request<User>('/auth/me/')

export async function fetchOrganizerWorkshops() {
  return (await request<Page<OrganizerWorkshop>>('/organizer/workshops/')).results
}
export function fetchOrganizerRegistrations(workshopId: number) {
  return request<OrganizerRegistration[]>(`/organizer/workshops/${workshopId}/registrations/`)
}
