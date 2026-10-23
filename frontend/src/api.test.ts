import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchWorkshops, getToken, register, setToken } from './api'

function respond(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }))
}

describe('api', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('stores and clears the token', () => {
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('sends the token and unwraps the paginated list', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) => respond(200, { results: [{ id: 1 }] }))
    vi.stubGlobal('fetch', fetchMock)
    setToken('abc')

    expect(await fetchWorkshops()).toEqual([{ id: 1 }])

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/workshops/')
    expect(new Headers(init?.headers).get('Authorization')).toBe('Token abc')
  })

  it('flattens a DRF field error into one line', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond(400, { username: ['Taken.'], detail: 'Bad.' })))
    await expect(register(1)).rejects.toThrow('Taken. Bad.')
  })

  it('uses a generic message when the body is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('nope', { status: 502 }))))
    await expect(register(1)).rejects.toThrow('API error 502')
  })

  it('treats an HTML page with status 200 as a failure, not as data', async () => {
    // CloudFront once answered API 403 and 404 with index.html and status 200.
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('<!doctype html>', { status: 200 }))))
    await expect(register(1)).rejects.toThrow('Unexpected response from the server.')
  })
})
