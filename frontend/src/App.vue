<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  cancel,
  fetchMyRegistrations,
  fetchWorkshops,
  register,
  type Registration,
  type Workshop,
} from './api'
import AuthPanel from './components/AuthPanel.vue'
import { logOut, restoreSession, session } from './session'

const workshops = ref<Workshop[]>([])
const registrations = ref<Registration[]>([])
const error = ref<string | null>(null)
const pending = ref<number | null>(null)

const activeByWorkshop = computed(() => {
  const map = new Map<number, Registration>()
  for (const r of registrations.value) if (r.status !== 'cancelled') map.set(r.workshop, r)
  return map
})

function describe(e: unknown): string {
  return e instanceof Error ? e.message : 'Something went wrong'
}

async function load() {
  try {
    const [list, mine] = await Promise.all([
      fetchWorkshops(),
      session.user ? fetchMyRegistrations() : Promise.resolve([]),
    ])
    workshops.value = list
    registrations.value = mine
  } catch (e) {
    error.value = describe(e)
  }
}

async function act(workshopId: number, run: () => Promise<unknown>) {
  error.value = null
  pending.value = workshopId
  try {
    await run()
    await load()
  } catch (e) {
    error.value = describe(e)
  } finally {
    pending.value = null
  }
}

onMounted(async () => {
  await restoreSession()
  await load()
})
watch(() => session.user, load)
</script>

<template>
  <main>
    <header class="top">
      <h1>Seatlock</h1>
      <div v-if="session.user" class="who">
        {{ session.user.username }}
        <button class="link" @click="logOut">Log out</button>
      </div>
    </header>
    <p class="lead">Workshops with limited seats. No overselling, ever.</p>

    <AuthPanel v-if="session.ready && !session.user" />

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <ul class="cards">
      <li v-for="w in workshops" :key="w.id">
        <h2>{{ w.title }}</h2>
        <time :datetime="w.starts_at">{{ new Date(w.starts_at).toLocaleString() }}</time>
        <p class="seats" :class="{ full: w.seats_left === 0 }">
          {{ w.seats_left === 0 ? 'Full - join the waitlist' : `${w.seats_left} of ${w.capacity} seats left` }}
        </p>
        <template v-if="session.user">
          <p v-if="activeByWorkshop.get(w.id)" class="badge" :class="activeByWorkshop.get(w.id)!.status">
            {{ activeByWorkshop.get(w.id)!.status === 'confirmed' ? 'You have a seat' : 'You are on the waitlist' }}
          </p>
          <button
            v-if="activeByWorkshop.get(w.id)"
            :disabled="pending === w.id"
            @click="act(w.id, () => cancel(activeByWorkshop.get(w.id)!.id))"
          >
            Cancel
          </button>
          <button v-else :disabled="pending === w.id" @click="act(w.id, () => register(w.id))">
            {{ w.seats_left === 0 ? 'Join waitlist' : 'Register' }}
          </button>
        </template>
      </li>
    </ul>
  </main>
</template>
