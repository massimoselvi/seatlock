import type { OrganizerRegistration, OrganizerWorkshop } from '../types'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api'
import OrganizerDashboard from './OrganizerDashboard.vue'

vi.mock('../api')

const workshop: OrganizerWorkshop = {
  id: 1,
  title: 'Intro to Postgres locks',
  description: '',
  starts_at: '2026-11-01T10:00:00Z',
  capacity: 2,
  seats_taken: 2,
  seats_left: 0,
  waitlist_size: 1,
}

function row(id: number, username: string, status: OrganizerRegistration['status']): OrganizerRegistration {
  return { id, username, email: `${username}@example.com`, status, created_at: '2026-10-01T10:00:00Z' }
}

async function openRegistrations() {
  const wrapper = mount(OrganizerDashboard)
  await flushPromises()
  await wrapper.get('button[aria-expanded]').trigger('click')
  await flushPromises()
  return wrapper
}

describe('organizerDashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(api.fetchOrganizerWorkshops).mockResolvedValue([workshop])
  })

  it('shows seats taken and the waitlist size', async () => {
    const wrapper = mount(OrganizerDashboard)
    await flushPromises()
    expect(wrapper.text()).toContain('2 / 2 seats taken')
    expect(wrapper.text()).toContain('1 on the waitlist')
  })

  it('shows an empty state without workshops', async () => {
    vi.mocked(api.fetchOrganizerWorkshops).mockResolvedValue([])
    const wrapper = mount(OrganizerDashboard)
    await flushPromises()
    expect(wrapper.text()).toContain('No workshops yet.')
  })

  it('shows an error when the workshops fail to load', async () => {
    vi.mocked(api.fetchOrganizerWorkshops).mockRejectedValue(new Error('Forbidden'))
    const wrapper = mount(OrganizerDashboard)
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toBe('Forbidden')
  })

  it('lists the registrations and filters them by status', async () => {
    vi.mocked(api.fetchOrganizerRegistrations).mockResolvedValue([
      row(1, 'ada', 'confirmed'),
      row(2, 'bob', 'waitlisted'),
      row(3, 'eve', 'cancelled'),
    ])
    const wrapper = await openRegistrations()
    expect(wrapper.text()).toContain('ada')
    expect(wrapper.text()).toContain('all (3)')

    const waitlisted = wrapper.findAll('button[aria-pressed]').find(b => b.text().startsWith('waitlisted'))
    await waitlisted!.trigger('click')

    expect(wrapper.text()).toContain('bob')
    expect(wrapper.text()).not.toContain('ada')
  })

  it('says so when nobody has registered', async () => {
    vi.mocked(api.fetchOrganizerRegistrations).mockResolvedValue([])
    expect((await openRegistrations()).text()).toContain('Nobody has registered yet.')
  })

  it('hides the registrations on a second click', async () => {
    vi.mocked(api.fetchOrganizerRegistrations).mockResolvedValue([row(1, 'ada', 'confirmed')])
    const wrapper = await openRegistrations()
    await wrapper.get('button[aria-expanded]').trigger('click')
    expect(wrapper.text()).not.toContain('ada')
  })
})
