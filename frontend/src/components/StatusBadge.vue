<script setup lang="ts">
type BadgeStatus = 'confirmed' | 'waitlisted' | 'cancelled' | 'full'

defineProps<{ status: BadgeStatus }>()

// Full class strings, so UnoCSS can find them. Status never relies on color alone: each one has an icon.
const TONE: Record<BadgeStatus, string> = {
  confirmed: 'bg-success-subtle text-success',
  waitlisted: 'bg-warning-subtle text-warning',
  cancelled: 'bg-secondary text-muted',
  full: 'bg-danger-subtle text-danger',
}

const ICON: Record<BadgeStatus, string> = {
  confirmed: 'i-lucide-circle-check',
  waitlisted: 'i-lucide-hourglass',
  cancelled: 'i-lucide-ban',
  full: 'i-lucide-circle-alert',
}
</script>

<template>
  <span class="text-sm font-600 px-2.5 py-0.5 rounded-full inline-flex gap-1 items-center" :class="TONE[status]">
    <span :class="ICON[status]" aria-hidden="true" />
    <slot />
  </span>
</template>
