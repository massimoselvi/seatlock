import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './api'
import { logIn, logOut, restoreSession, session } from './session'

vi.mock('./api')

const user = { id: 1, username: 'ada', email: 'ada@example.com', is_staff: false }

describe('session', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    session.user = null
    session.ready = false
  })

  it('restores the user when a token is stored', async () => {
    vi.mocked(api.getToken).mockReturnValue('abc')
    vi.mocked(api.fetchMe).mockResolvedValue(user)

    await restoreSession()

    expect(session.user).toEqual(user)
    expect(session.ready).toBe(true)
  })

  it('drops a token the server rejects', async () => {
    vi.mocked(api.getToken).mockReturnValue('stale')
    vi.mocked(api.fetchMe).mockRejectedValue(new Error('401'))

    await restoreSession()

    expect(api.setToken).toHaveBeenCalledWith(null)
    expect(session.user).toBeNull()
    expect(session.ready).toBe(true)
  })

  it('stores the token on login', async () => {
    vi.mocked(api.login).mockResolvedValue({ token: 'abc' })
    vi.mocked(api.fetchMe).mockResolvedValue(user)

    await logIn('ada', 'secret')

    expect(api.setToken).toHaveBeenCalledWith('abc')
    expect(session.user).toEqual(user)
  })

  it('clears the session on logout even when the request fails', async () => {
    session.user = user
    vi.mocked(api.logout).mockRejectedValue(new Error('offline'))

    await expect(logOut()).rejects.toThrow('offline')

    expect(api.setToken).toHaveBeenCalledWith(null)
    expect(session.user).toBeNull()
  })
})
