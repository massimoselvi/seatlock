import {
  defineConfig,
  presetIcons,
  presetWind4,
  transformerDirectives,
  transformerVariantGroup,
} from 'unocss'

/**
 * Colors point at CSS variables from src/styles/theme.css, so light and dark mode
 * need no `dark:` variants on individual classes.
 */
export default defineConfig({
  presets: [
    // The reset stays off until style.css is gone, so unconverted components keep their look.
    presetWind4({ dark: 'class', preflights: { reset: false } }),
    presetIcons({
      scale: 1.2,
      // An explicit import, because pnpm's strict layout hides the package from the preset.
      collections: { lucide: () => import('@iconify-json/lucide/icons.json').then(m => m.default) },
      extraProperties: { 'display': 'inline-block', 'vertical-align': 'middle' },
    }),
  ],
  transformers: [transformerDirectives(), transformerVariantGroup()],
  theme: {
    colors: {
      canvas: 'var(--c-canvas)',
      surface: { DEFAULT: 'var(--c-surface)', raised: 'var(--c-surface-raised)' },
      line: 'var(--c-border)',
      ink: 'var(--c-text)',
      muted: 'var(--c-text-muted)',
      primary: { DEFAULT: 'var(--c-primary)', fg: 'var(--c-primary-fg)', subtle: 'var(--c-primary-subtle)' },
      secondary: { DEFAULT: 'var(--c-secondary)', fg: 'var(--c-secondary-fg)' },
      success: { DEFAULT: 'var(--c-success)', subtle: 'var(--c-success-subtle)' },
      warning: { DEFAULT: 'var(--c-warning)', subtle: 'var(--c-warning-subtle)' },
      danger: { DEFAULT: 'var(--c-danger)', subtle: 'var(--c-danger-subtle)' },
    },
  },
  // A class pattern used three times or more becomes a shortcut.
  shortcuts: {
    'btn': 'inline-flex items-center justify-center gap-2 min-h-11 px-4 rounded-md border-0 font-600 cursor-pointer transition-colors duration-150 focus-visible:(outline-2 outline-offset-2 outline-primary) disabled:(opacity-60 cursor-progress)',
    'btn-primary': 'btn bg-primary text-primary-fg hover:bg-primary/90',
    'btn-secondary': 'btn bg-secondary text-secondary-fg hover:bg-secondary/80',
    'btn-danger': 'btn bg-danger text-white hover:bg-danger/90',
    'btn-ghost-danger': 'btn bg-transparent text-danger hover:bg-danger-subtle',
    'btn-link': 'inline-flex items-center min-h-11 bg-transparent border-0 p-0 text-primary underline cursor-pointer focus-visible:(outline-2 outline-offset-2 outline-primary)',
    'card': 'bg-surface rounded-lg border border-line p-5 shadow-sm',
    'field': 'grid gap-1 text-sm',
    'input': 'min-h-11 px-3 rounded-md border border-line bg-surface text-ink text-base focus-visible:(outline-2 outline-offset-1 outline-primary)',
  },
})
