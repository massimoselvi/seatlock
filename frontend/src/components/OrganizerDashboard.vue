<script setup lang="ts">
import type { OrganizerRegistration, OrganizerWorkshop, RegistrationStatus } from '../types'
import { computed, onMounted, shallowRef } from 'vue'
import { fetchOrganizerRegistrations, fetchOrganizerWorkshops } from '../api'
import { describeError } from '../utils'
import SeatMeter from './SeatMeter.vue'
import StatusBadge from './StatusBadge.vue'

type StatusFilter = 'all' | RegistrationStatus

const FILTERS: StatusFilter[] = ['all', 'confirmed', 'waitlisted', 'cancelled']

const workshops = shallowRef<OrganizerWorkshop[]>([])
const openId = shallowRef<number | null>(null)
const rows = shallowRef<OrganizerRegistration[]>([])
const filter = shallowRef<StatusFilter>('all')
const error = shallowRef<string | null>(null)
const loading = shallowRef(true)

const counts = computed(() => {
  const result: Record<StatusFilter, number> = { all: rows.value.length, confirmed: 0, waitlisted: 0, cancelled: 0 }
  for (const r of rows.value)
    result[r.status]++
  return result
})
const visibleRows = computed(() =>
  filter.value === 'all' ? rows.value : rows.value.filter(r => r.status === filter.value),
)

async function toggle(id: number) {
  if (openId.value === id) {
    openId.value = null
    return
  }
  error.value = null
  try {
    rows.value = await fetchOrganizerRegistrations(id)
    filter.value = 'all'
    openId.value = id
  }
  catch (e) {
    error.value = describeError(e)
  }
}

onMounted(async () => {
  try {
    workshops.value = await fetchOrganizerWorkshops()
  }
  catch (e) {
    error.value = describeError(e)
  }
  finally {
    loading.value = false
  }
})
</script>

<template>
  <section>
    <h2 class="text-xl font-700 m-0 mb-4">
      Organizer dashboard
    </h2>
    <p v-if="error" class="text-danger mb-4 mt-0 p-4 rounded-lg bg-danger-subtle" role="alert">
      {{ error }}
    </p>
    <ul v-if="loading" class="m-0 p-0 list-none gap-4 grid" aria-busy="true">
      <li v-for="n in 2" :key="n" class="card h-32 animate-pulse" aria-hidden="true" />
    </ul>
    <p v-else-if="!workshops.length && !error" class="text-muted">
      No workshops yet.
    </p>
    <ul v-else class="m-0 p-0 list-none gap-4 grid">
      <li v-for="w in workshops" :key="w.id" class="card gap-3 grid">
        <div class="flex flex-wrap gap-2 items-start justify-between">
          <h3 class="text-lg font-600 m-0">
            {{ w.title }}
          </h3>
          <p class="text-sm text-muted m-0 flex gap-1 items-center">
            <span class="i-lucide-hourglass" aria-hidden="true" />
            {{ w.waitlist_size }} on the waitlist
          </p>
        </div>
        <div class="gap-1 grid">
          <SeatMeter :capacity="w.capacity" :taken="w.seats_taken" />
          <p class="text-sm text-muted m-0 flex gap-1 items-center">
            <span class="i-lucide-armchair" aria-hidden="true" />
            {{ w.seats_taken }} / {{ w.capacity }} seats taken
          </p>
        </div>
        <button
          class="btn-link self-start"
          :aria-expanded="openId === w.id"
          :aria-controls="`registrations-${w.id}`"
          @click="toggle(w.id)"
        >
          <span class="mr-1" :class="openId === w.id ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'" aria-hidden="true" />
          {{ openId === w.id ? 'Hide' : 'Registrations' }}
        </button>
        <div v-if="openId === w.id" :id="`registrations-${w.id}`" class="gap-3 grid">
          <p v-if="!rows.length" class="text-muted m-0">
            Nobody has registered yet.
          </p>
          <template v-else>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="f in FILTERS"
                :key="f"
                class="text-sm font-600 px-3 border-0 rounded-full min-h-11 capitalize"
                :class="filter === f ? 'bg-primary text-primary-fg' : 'bg-secondary text-secondary-fg'"
                :aria-pressed="filter === f"
                @click="filter = f"
              >
                {{ f }} ({{ counts[f] }})
              </button>
            </div>
            <ul class="m-0 p-0 list-none grid">
              <li
                v-for="r in visibleRows"
                :key="r.id"
                class="py-2 border-t border-line flex flex-wrap gap-2 items-center justify-between first:border-t-0"
              >
                <span class="min-w-0 break-words">
                  {{ r.username }}
                  <span class="text-muted break-all">({{ r.email }})</span>
                </span>
                <StatusBadge :status="r.status">
                  {{ r.status }}
                </StatusBadge>
              </li>
            </ul>
          </template>
        </div>
      </li>
    </ul>
  </section>
</template>
