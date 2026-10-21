<script setup lang="ts">
import { isDark, toggleDark } from '../composables/theme'
</script>

<template>
  <button
    type="button"
    class="btn-secondary p-0 min-w-11"
    :aria-label="isDark ? 'Switch to the light theme' : 'Switch to the dark theme'"
    @click="toggleDark()"
  >
    <span :class="isDark ? 'i-lucide-sun' : 'i-lucide-moon'" aria-hidden="true" />
  </button>
</template>
