// @env browser
import { useDark, useToggle } from '@vueuse/core'

/**
 * Follows the system setting until the user picks a side. The choice is kept in localStorage
 * under VueUse's default key, which the inline script in index.html reads before first paint.
 */
export const isDark = useDark()
export const toggleDark = useToggle(isDark)
