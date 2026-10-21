<script setup lang="ts">
import type { Registration, Workshop } from './types'
import { computed, onMounted, shallowRef, watch } from 'vue'
import { cancel, fetchMyRegistrations, fetchWorkshops, register } from './api'
import AuthPanel from './components/AuthPanel.vue'
import OrganizerDashboard from './components/OrganizerDashboard.vue'
import WorkshopCard from './components/WorkshopCard.vue'
import { logOut, restoreSession, session } from './session'
import { describeError } from './utils'

const workshops = shallowRef<Workshop[]>([])
const registrations = shallowRef<Registration[]>([])
const error = shallowRef<string | null>(null)
const pending = shallowRef<number | null>(null)
const view = shallowRef<'workshops' | 'organizer'>('workshops')

const activeByWorkshop = computed(() => {
  const map = new Map<number, Registration>()
  for (const r of registrations.value) {
    if (r.status !== 'cancelled')
      map.set(r.workshop, r)
  }
  return map
})

async function load() {
  try {
    const [list, mine] = await Promise.all([
      fetchWorkshops(),
      session.user ? fetchMyRegistrations() : Promise.resolve([]),
    ])
    workshops.value = list
    registrations.value = mine
  }
  catch (e) {
    error.value = describeError(e)
  }
}

async function act(workshopId: number, run: () => Promise<unknown>) {
  error.value = null
  pending.value = workshopId
  try {
    await run()
    await load()
  }
  catch (e) {
    error.value = describeError(e)
  }
  finally {
    pending.value = null
  }
}

onMounted(async () => {
  await restoreSession()
  await load()
})
watch(() => session.user, (user) => {
  if (!user?.is_staff)
    view.value = 'workshops'
  load()
})
</script>

<template>
  <main>
    <header class="top">
      <h1>Seatlock</h1>
      <div v-if="session.user" class="who">
        {{ session.user.username }}
        <button
          v-if="session.user.is_staff"
          class="link"
          @click="view = view === 'organizer' ? 'workshops' : 'organizer'"
        >
          {{ view === 'organizer' ? 'Workshops' : 'Organizer dashboard' }}
        </button>
        <button class="link" @click="logOut">
          Log out
        </button>
      </div>
    </header>
    <p class="lead">
      Workshops with limited seats. No overselling, ever.
    </p>

    <AuthPanel v-if="session.ready && !session.user" />

    <OrganizerDashboard v-if="view === 'organizer' && session.user?.is_staff" />
    <template v-else>
      <p v-if="error" class="error" role="alert">
        {{ error }}
      </p>
      <ul class="cards">
        <WorkshopCard
          v-for="w in workshops"
          :key="w.id"
          :workshop="w"
          :registration="activeByWorkshop.get(w.id)"
          :signed-in="!!session.user"
          :pending="pending === w.id"
          @register="act(w.id, () => register(w.id))"
          @cancel="act(w.id, () => cancel(activeByWorkshop.get(w.id)!.id))"
        />
      </ul>
    </template>
  </main>
</template>
