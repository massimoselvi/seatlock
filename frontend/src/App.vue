<script setup lang="ts">
import type { Registration, Workshop } from './types'
import { computed, onMounted, shallowRef, watch } from 'vue'
import { cancel, fetchMyRegistrations, fetchWorkshops, register } from './api'
import AuthPanel from './components/AuthPanel.vue'
import OrganizerDashboard from './components/OrganizerDashboard.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import WorkshopCard from './components/WorkshopCard.vue'
import { logOut, restoreSession, session } from './session'
import { describeError } from './utils'

const workshops = shallowRef<Workshop[]>([])
const registrations = shallowRef<Registration[]>([])
const error = shallowRef<string | null>(null)
const actionError = shallowRef<{ workshopId: number, message: string } | null>(null)
const loaded = shallowRef(false)
const pending = shallowRef<number | null>(null)
type View = 'workshops' | 'organizer'

const VIEWS: { id: View, label: string }[] = [
  { id: 'workshops', label: 'Workshops' },
  { id: 'organizer', label: 'Organizer dashboard' },
]

const view = shallowRef<View>('workshops')

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
    <header class="flex flex-wrap gap-4 items-center justify-between">
      <h1 class="text-2xl font-700 m-0 flex gap-2 items-center">
        <span class="i-lucide-armchair text-primary" aria-hidden="true" />
        Seatlock
      </h1>
      <div class="flex flex-wrap gap-x-4 gap-y-2 items-center">
        <template v-if="session.user">
          <span class="text-muted">{{ session.user.username }}</span>
          <nav v-if="session.user.is_staff" aria-label="Views" class="flex gap-4">
            <button
              v-for="v in VIEWS"
              :key="v.id"
              class="btn-link"
              :class="view === v.id ? 'font-700 no-underline' : ''"
              :aria-current="view === v.id ? 'page' : undefined"
              @click="view = v.id"
            >
              {{ v.label }}
            </button>
          </nav>
          <button class="btn-link" @click="logOut">
            <span class="i-lucide-log-out mr-1" aria-hidden="true" />
            Log out
          </button>
        </template>
        <ThemeToggle />
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
