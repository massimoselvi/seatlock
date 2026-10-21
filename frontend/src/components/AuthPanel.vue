<script setup lang="ts">
import { shallowRef } from 'vue'
import { logIn, signUp } from '../session'
import { describeError } from '../utils'

const mode = shallowRef<'login' | 'signup'>('login')
const username = shallowRef('')
const email = shallowRef('')
const password = shallowRef('')
const error = shallowRef<string | null>(null)
const busy = shallowRef(false)

async function submit() {
  error.value = null
  busy.value = true
  try {
    if (mode.value === 'login')
      await logIn(username.value, password.value)
    else await signUp(username.value, email.value, password.value)
  }
  catch (e) {
    error.value = describeError(e)
  }
  finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="mb-6 card gap-3 grid max-w-80" @submit.prevent="submit">
    <h2 class="text-lg font-600 m-0">
      {{ mode === 'login' ? 'Log in' : 'Create an account' }}
    </h2>
    <div class="field">
      <label for="auth-username">Username</label>
      <input id="auth-username" v-model="username" class="input" autocomplete="username" required>
    </div>
    <div v-if="mode === 'signup'" class="field">
      <label for="auth-email">Email</label>
      <input id="auth-email" v-model="email" class="input" type="email" autocomplete="email" required>
    </div>
    <div class="field">
      <label for="auth-password">Password</label>
      <input
        id="auth-password"
        v-model="password"
        class="input"
        type="password"
        :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
        required
      >
    </div>
    <p v-if="error" class="text-sm text-danger m-0" role="alert">
      {{ error }}
    </p>
    <button type="submit" class="btn-primary" :disabled="busy">
      {{ mode === 'login' ? 'Log in' : 'Sign up' }}
    </button>
    <button type="button" class="btn-link justify-self-start" @click="mode = mode === 'login' ? 'signup' : 'login'">
      {{ mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Log in' }}
    </button>
  </form>
</template>
