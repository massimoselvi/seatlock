import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './api'
import App from './App.vue'
import { session } from './session'

vi.mock('./api')

const member = { id: 1, username: 'ada', email: 'ada@example.com', is_staff: false }

async function render(user = member) {
  vi.mocked(api.getToken).mockReturnValue('abc')
  vi.mocked(api.fetchMe).mockResolvedValue(user)
  const wrapper = mount(App)
  await flushPromises()
  return wrapper
}

describe('app', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    session.user = null
    session.ready = false
    vi.mocked(api.fetchWorkshops).mockResolvedValue([])
    vi.mocked(api.fetchMyRegistrations).mockResolvedValue([])
    vi.mocked(api.fetchOrganizerWorkshops).mockResolvedValue([])
  })

  it('shows an empty state when there are no workshops', async () => {
    expect((await render()).text()).toContain('No workshops yet. Check back soon.')
  })

  it('shows the sign-in form to a visitor', async () => {
    vi.mocked(api.getToken).mockReturnValue(null)
    const wrapper = mount(App)
    await flushPromises()
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('gives a member no view switch', async () => {
    expect((await render()).find('nav').exists()).toBe(false)
  })

  it('lets staff switch views and marks the current one', async () => {
    const wrapper = await render({ ...member, is_staff: true })
    const [workshops, dashboard] = wrapper.findAll('nav button')
    expect(workshops.attributes('aria-current')).toBe('page')

    await dashboard.trigger('click')

    expect(dashboard.attributes('aria-current')).toBe('page')
    expect(workshops.attributes('aria-current')).toBeUndefined()
    expect(wrapper.find('h2').text()).toBe('Organizer dashboard')
  })
})
