import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SeatMeter from './SeatMeter.vue'

function fill(capacity: number, taken: number) {
  const wrapper = mount(SeatMeter, { props: { capacity, taken } })
  const bar = wrapper.get('[data-testid="fill"]')
  return { width: bar.attributes('style'), classes: bar.classes() }
}

describe('seatMeter', () => {
  it('is empty and green when nobody has registered', () => {
    const { width, classes } = fill(10, 0)
    expect(width).toContain('width: 0%')
    expect(classes).toContain('bg-success')
  })

  it('turns to a warning when 80 percent of the seats are taken', () => {
    const { width, classes } = fill(10, 8)
    expect(width).toContain('width: 80%')
    expect(classes).toContain('bg-warning')
  })

  it('is full and red when every seat is taken', () => {
    expect(fill(10, 10).classes).toContain('bg-danger')
  })

  it('never goes past 100 percent', () => {
    expect(fill(10, 14).width).toContain('width: 100%')
  })

  it('treats a workshop without capacity as full', () => {
    expect(fill(0, 0).classes).toContain('bg-danger')
  })
})
