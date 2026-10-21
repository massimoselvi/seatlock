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
const actionError = shallowRef<{ workshopId: number, message: string } | null>(null)
const loaded = shallowRef(false)
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
  finally {
    loaded.value = true
  }
}

async function act(workshopId: number, run: () => Promise<unknown>) {
  actionError.value = null
  pending.value = workshopId
  try {
    await run()
    await load()
  }
  catch (e) {
    actionError.value = { workshopId, message: describeError(e) }
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
  <main class="mx-auto px-4 py-8 max-w-3xl">
    <header class="flex gap-4 items-center justify-between">
      <h1 class="text-2xl font-700 m-0 flex gap-2 items-center">
        <span class="i-lucide-armchair text-primary" aria-hidden="true" />
        Seatlock
      </h1>
      <div v-if="session.user" class="text-muted flex gap-4 items-center">
        <span>{{ session.user.username }}</span>
        <button
          v-if="session.user.is_staff"
          class="btn-link"
          @click="view = view === 'organizer' ? 'workshops' : 'organizer'"
        >
          {{ view === 'organizer' ? 'Workshops' : 'Organizer dashboard' }}
        </button>
        <button class="btn-link" @click="logOut">
          <span class="i-lucide-log-out mr-1" aria-hidden="true" />
          Log out
        </button>
      </div>
    </header>
    <p class="text-muted mb-6 mt-2">
      Workshops with limited seats. No overselling, ever.
    </p>

    <AuthPanel v-if="session.ready && !session.user" />

    <OrganizerDashboard v-if="view === 'organizer' && session.user?.is_staff" />
    <template v-else>
      <p v-if="error" class="text-danger mb-4 mt-0 p-4 rounded-lg bg-danger-subtle" role="alert">
        {{ error }}
      </p>
      <ul class="m-0 p-0 list-none gap-4 grid" :aria-busy="!loaded">
        <template v-if="!loaded">
          <li v-for="n in 3" :key="n" class="card h-36 animate-pulse" aria-hidden="true" />
        </template>
        <li v-else-if="!workshops.length && !error" class="text-muted card py-10 gap-2 grid justify-items-center">
          <span class="i-lucide-inbox text-3xl" aria-hidden="true" />
          <p class="m-0">
            No workshops yet. Check back soon.
          </p>
        </li>
        <WorkshopCard
          v-for="w in workshops"
          :key="w.id"
          :workshop="w"
          :registration="activeByWorkshop.get(w.id)"
          :signed-in="!!session.user"
          :pending="pending === w.id"
          :error="actionError?.workshopId === w.id ? actionError.message : undefined"
          @register="act(w.id, () => register(w.id))"
          @cancel="act(w.id, () => cancel(activeByWorkshop.get(w.id)!.id))"
        />
      </ul>
    </template>
  </main>
</template>
