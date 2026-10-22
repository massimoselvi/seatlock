# Frontend polish plan

Initial plan to improve the Vue frontend. It was planned on the branch `exp/frontend-polish`, now deleted.
Status: implemented with UnoCSS and merged to `main` in PR #75. The decision is recorded in [ADR 0006](architecture/adr/0006-style-the-frontend-with-unocss.md). The text below is the original plan, kept for the record.

## Current state

The frontend has about 550 lines: `App.vue`, `AuthPanel.vue`, `OrganizerDashboard.vue`, `style.css`.
It works, but it looks like an unstyled default.

- Hex colors repeat in `style.css`. There are no design tokens and no dark mode.
- The list has no loading state and no empty state.
- One global error line shows at the top. It does not show which card failed.
- Buttons have no focus style. The view switch is a text link, not a tab.
- Seat availability shows as text only.

## Goals

1. Make the UI look designed, with small visible changes per step.
2. Keep all behavior and API calls unchanged.
3. Keep the code easy to explain (portfolio project).

## Improvements

### 1. Design foundation

- Move colors, spacing and radii to CSS variables (or Tailwind `@theme`).
- Add dark mode with `prefers-color-scheme`.
- Choose a type scale and a font.
- Add a small brand identity: header, logo mark, accent color.

### 2. Workshop cards

- Show seats as a visual meter (progress bar or seat dots).
- Split the date into a day/month block and a time.
- Show status as a pill badge (confirmed, waitlisted, full) with an icon. Do not use color alone.
- Use primary, secondary and danger button styles. "Cancel" is a quiet destructive action.

### 3. UX states

- Add skeleton loaders for the list.
- Add an empty state for "no workshops".
- Show errors near the card that failed.
- Give feedback after Register and Cancel (toast or inline message).
- Stress-test long titles, long emails, capacity 0 and capacity 1000.

### 4. Organizer dashboard

- Add a seat-fill bar and a clear waitlist count per row.
- Show cards instead of a table on small screens.
- Add status filters and counts for the registrations list.

### 5. Accessibility

- Add `:focus-visible` styles.
- Check color contrast, especially `#9a6700` and the `.link` buttons.
- Use `aria-live` for seat and status changes. Use `aria-busy` while loading.
- Use a `<nav>` and a tab pattern for the Workshops / Organizer switch.

### 6. Motion

- Add small transitions only: button press, card state change, meter fill.
- Respect `prefers-reduced-motion`.

### 7. Mobile

- Set input font size to at least 16px to prevent iOS zoom.
- Make tap targets at least 44px.

## Component split

Extract these from `App.vue` before any restyle:

- `WorkshopCard.vue`
- `SeatMeter.vue`
- `StatusBadge.vue`
- `BaseButton.vue` (variants: primary, secondary, danger, link)

## Styling options (open decision)

| Option | Job-market signal | Setup effort | Templates stay clean | Tokens and motion included | Icons built in | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Plain CSS with variables | Low | None | Yes | No | No | Enough for 550 lines, but dark mode and dashboard need more hand-written CSS |
| Open Props | Low–Medium | Very low | Yes | Yes | No | CSS custom properties only: no classes, no plugin. Use scoped Vue `<style>`. Import only the needed files (`open-props/sizes`, `open-props/colors`). All layout CSS is still hand-written |
| Tailwind v4 | High | Low | No (class noise) | Partly | No | Recommended for the job market. Plugin `@tailwindcss/vite`, no config file, tokens in `@theme` |
| UnoCSS | Low | Medium | No (class noise) | Partly | Yes | Fast and flexible, fewer docs. Good for learning value |

Do not combine Open Props and Tailwind. Both define tokens, and the two token sets conflict.

Recommendation:

- Job-market goal: Tailwind v4, plus `unplugin-icons` (Iconify) if icons are needed.
- Clean-code goal: Open Props with scoped CSS.
Record the final choice as an ADR before step 1 of the order below. It became [ADR 0006](architecture/adr/0006-style-the-frontend-with-unocss.md).

## Tailwind v4 steps (if chosen)

1. `pnpm add -D tailwindcss @tailwindcss/vite`. Commit `pnpm-lock.yaml`.
2. Register the plugin in `vite.config.ts`. Replace `style.css` with `@import "tailwindcss"` and an `@theme` block.
3. Extract the components, convert the templates, delete the old CSS.
4. Use `BaseButton.vue` for repeated button classes. Do not use `@apply` widely.

## Suggested order

1. ADR for the styling choice.
2. Component split, no visual change.
3. Design foundation and workshop cards (items 1 and 2).
4. UX states and accessibility (items 3 and 5).
5. Organizer dashboard, motion, mobile (items 4, 6 and 7).

Run `pnpm build` after each step to check the types.
Run `docker compose up --build` at the end to check the full stack.

## Skills to use

`impeccable`, `redesign-existing-projects`, `frontend-design`, `break-ui`, `design:accessibility-review`, `animate`, `mobile-native`.

## Open questions (answered)

- Scope: all seven items were done.
- Visual direction: minimalist, with an indigo primary color.
- Styling option: UnoCSS, with the antfu toolchain. See ADR 0006 for the alternatives.
