import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatusBadge from './StatusBadge.vue'

describe('statusBadge', () => {
  it.each([
    ['confirmed', 'i-lucide-circle-check', 'text-success'],
    ['waitlisted', 'i-lucide-hourglass', 'text-warning'],
    ['cancelled', 'i-lucide-ban', 'text-muted'],
    ['full', 'i-lucide-circle-alert', 'text-danger'],
  ] as const)('renders the %s status with an icon and its label', (status, icon, tone) => {
    const wrapper = mount(StatusBadge, { props: { status }, slots: { default: 'Label' } })
    expect(wrapper.text()).toBe('Label')
    expect(wrapper.find(`.${icon}`).attributes('aria-hidden')).toBe('true')
    expect(wrapper.classes()).toContain(tone)
  })
})
