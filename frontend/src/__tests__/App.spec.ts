import { describe, it, expect } from 'vitest'

import { mount } from '@vue/test-utils'
import App from '../App.vue'

describe('App', () => {
  it('renders the application shell', () => {
    const wrapper = mount(App, {
      global: { stubs: { RouterView: true } },
    })
    expect(wrapper.text()).toContain('Digital JOST')
    expect(wrapper.find('a[href="/"]').text()).toBe('Voltar ao portal')
  })
})
