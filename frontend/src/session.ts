import { reactive } from 'vue'
import * as api from './api'

export const session = reactive<{ user: api.User | null, ready: boolean }>({
  user: null,
  ready: false,
})

export async function restoreSession(): Promise<void> {
  if (api.getToken()) {
    try {
      session.user = await api.fetchMe()
    }
    catch {
      api.setToken(null)
    }
  }
  session.ready = true
}

export async function logIn(username: string, password: string): Promise<void> {
  const { token } = await api.login({ username, password })
  api.setToken(token)
  session.user = await api.fetchMe()
}

export async function signUp(username: string, email: string, password: string): Promise<void> {
  const { token, user } = await api.signup({ username, email, password })
  api.setToken(token)
  session.user = user
}

export async function logOut(): Promise<void> {
  try {
    await api.logout()
  }
  finally {
    api.setToken(null)
    session.user = null
  }
}
