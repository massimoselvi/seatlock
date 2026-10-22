# 0006. Style the frontend with UnoCSS and the antfu toolchain

Status: Proposed

## Context

The frontend was 550 lines with one global `style.css`. It repeated hex colors, had no dark mode, no loading or empty states, no lint and no tests. A portfolio reviewer reads the UI first and the code second, so both need to look deliberate.

## Decision

- Style with UnoCSS (`presetWind4`, `presetIcons`). Class names match Tailwind, so the Tailwind docs still apply.
- Define colors once as semantic CSS variables in `src/styles/theme.css` (OKLCH, light and dark). `uno.config.ts` maps them to theme colors such as `primary`, `danger` and `surface`. Components never use raw color values, so dark mode needs no `dark:` variants.
- Put repeated class patterns in shortcuts (`btn-primary`, `card`, `input`) instead of a `BaseButton` component or `@apply`.
- Use one Iconify set, `lucide`, loaded by an explicit import because pnpm hides the package from the preset.
- Lint and format with `@antfu/eslint-config` (`antislop`, `unocss`, Vue a11y). Find dead code with Knip. Test with Vitest and happy-dom. The `ci` script in `frontend/` runs all of them plus the build, and GitHub Actions calls it.
- Use VueUse `useDark` for the theme toggle. An inline script in `index.html` sets the theme before first paint.
- Use `shallowRef` for state that is replaced as a whole.

## Alternatives

- **Plain CSS with tokens and `@layer`.** No dependency, clean templates, but more hand-written CSS, no icons and no lint gate for styles.
- **Tailwind v4.** The strongest job-market signal. UnoCSS gives the same class names plus built-in icons, and fits the Vue ecosystem tools used here.
- **Open Props or Pico CSS.** Fast, but they give tokens or defaults, not a component system, and Pico gives a recognizable look.
- **Storybook.** Deferred. It is a large toolchain for six small components. Vitest component tests cover the states.

## Consequences

- About 12 new dev dependencies for a small app. Knip keeps them honest.
- Class names must be complete static strings, because UnoCSS finds classes by scanning source. Dynamic classes use lookup objects.
- The frontend has a `ci` gate that matches the backend one: lint, types, dead code, tests, build.
- The reset is on, so every heading and button carries its own classes.
