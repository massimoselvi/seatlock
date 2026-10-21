<script setup lang="ts">
import type { OrganizerRegistration, OrganizerWorkshop } from '../api'
import { onMounted, ref } from 'vue'
import {
  fetchOrganizerRegistrations,
  fetchOrganizerWorkshops,

} from '../api'

const workshops = ref<OrganizerWorkshop[]>([])
const openId = ref<number | null>(null)
const rows = ref<OrganizerRegistration[]>([])
const error = ref<string | null>(null)
const loading = ref(true)

function describe(e: unknown): string {
  return e instanceof Error ? e.message : 'Something went wrong'
}

async function toggle(id: number) {
  if (openId.value === id) {
    openId.value = null
    return
  }
  error.value = null
  try {
    rows.value = await fetchOrganizerRegistrations(id)
    openId.value = id
  }
  catch (e) {
    error.value = describe(e)
  }
}

onMounted(async () => {
  try {
    workshops.value = await fetchOrganizerWorkshops()
  }
  catch (e) {
    error.value = describe(e)
  }
  finally {
    loading.value = false
  }
})
</script>

<template>
  <section>
    <h2>Organizer dashboard</h2>
    <p v-if="error" class="error" role="alert">
      {{ error }}
    </p>
    <p v-if="loading">
      Loading...
    </p>
    <p v-else-if="!workshops.length && !error">
      No workshops yet.
    </p>
    <table v-else-if="workshops.length" class="table">
      <thead>
        <tr><th>Workshop</th><th>Seats taken</th><th>Waitlist</th><th /></tr>
      </thead>
      <tbody>
        <template v-for="w in workshops" :key="w.id">
          <tr>
            <td>{{ w.title }}</td>
            <td>{{ w.seats_taken }} / {{ w.capacity }}</td>
            <td>{{ w.waitlist_size }}</td>
            <td>
              <button class="link" :aria-expanded="openId === w.id" @click="toggle(w.id)">
                {{ openId === w.id ? 'Hide' : 'Registrations' }}
              </button>
            </td>
          </tr>
          <tr v-if="openId === w.id">
            <td colspan="4">
              <p v-if="!rows.length">
                Nobody has registered yet.
              </p>
              <ul v-else class="people">
                <li v-for="r in rows" :key="r.id">
                  {{ r.username }} ({{ r.email }})
                  <span class="badge" :class="r.status">{{ r.status }}</span>
                </li>
              </ul>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>
