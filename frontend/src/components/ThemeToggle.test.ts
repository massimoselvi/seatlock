import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import ThemeToggle from './ThemeToggle.vue'

describe('themeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  it('switches the dark class on the root element and the label', async () => {
    const wrapper = mount(ThemeToggle)
    expect(wrapper.attributes('aria-label')).toBe('Switch to the dark theme')

    await wrapper.trigger('click')

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(wrapper.attributes('aria-label')).toBe('Switch to the light theme')

    await wrapper.trigger('click')

    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
