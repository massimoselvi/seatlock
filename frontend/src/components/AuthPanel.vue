<script setup lang="ts">
import { ref } from 'vue'
import { logIn, signUp } from '../session'

const mode = ref<'login' | 'signup'>('login')
const username = ref('')
const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const busy = ref(false)

async function submit() {
  error.value = null
  busy.value = true
  try {
    if (mode.value === 'login') await logIn(username.value, password.value)
    else await signUp(username.value, email.value, password.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="auth" @submit.prevent="submit">
    <h2>{{ mode === 'login' ? 'Log in' : 'Create an account' }}</h2>
    <label>Username <input v-model="username" autocomplete="username" required /></label>
    <label v-if="mode === 'signup'">
      Email <input v-model="email" type="email" autocomplete="email" required />
    </label>
    <label>
      Password
      <input
        v-model="password"
        type="password"
        :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
        required
      />
    </label>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="busy">{{ mode === 'login' ? 'Log in' : 'Sign up' }}</button>
    <button type="button" class="link" @click="mode = mode === 'login' ? 'signup' : 'login'">
      {{ mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Log in' }}
    </button>
  </form>
</template>
