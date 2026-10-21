import type { Registration, Workshop } from '../types'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WorkshopCard from './WorkshopCard.vue'

const workshop: Workshop = {
  id: 1,
  title: 'Intro to Postgres locks',
  description: '',
  starts_at: '2026-11-01T10:00:00Z',
  capacity: 10,
  seats_taken: 4,
  seats_left: 6,
}

function registration(status: Registration['status']): Registration {
  return { id: 7, workshop: 1, workshop_title: workshop.title, status, created_at: '2026-10-01T10:00:00Z' }
}

function render(props: Partial<InstanceType<typeof WorkshopCard>['$props']> = {}) {
  return mount(WorkshopCard, { props: { workshop, signedIn: true, pending: false, ...props } })
}

describe('workshopCard', () => {
  it('shows the seats left', () => {
    expect(render().text()).toContain('6 of 10 seats left')
  })

  it('offers the waitlist when the workshop is full', () => {
    const wrapper = render({ workshop: { ...workshop, seats_left: 0 } })
    expect(wrapper.text()).toContain('Full - join the waitlist')
    expect(wrapper.find('button').text()).toBe('Join waitlist')
  })

  it('emits register when the user clicks Register', async () => {
    const wrapper = render()
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('register')).toHaveLength(1)
  })

  it('shows the confirmed status and emits cancel', async () => {
    const wrapper = render({ registration: registration('confirmed') })
    expect(wrapper.text()).toContain('You have a seat')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('shows the waitlisted status', () => {
    expect(render({ registration: registration('waitlisted') }).text()).toContain('You are on the waitlist')
  })

  it('treats a cancelled registration as no registration', () => {
    expect(render({ registration: registration('cancelled') }).find('button').text()).toBe('Register')
  })

  it('shows no actions when signed out', () => {
    expect(render({ signedIn: false }).find('button').exists()).toBe(false)
  })

  it('shows an action error inside the card', () => {
    expect(render({ error: 'Seat already taken.' }).get('[role="alert"]').text()).toBe('Seat already taken.')
  })

  it('shows a Full badge to a signed-in user on a full workshop', () => {
    expect(render({ workshop: { ...workshop, seats_left: 0 } }).text()).toContain('Full')
  })

  it('disables the button while a request is pending', () => {
    expect(render({ pending: true }).find('button').attributes('disabled')).toBeDefined()
  })
})
