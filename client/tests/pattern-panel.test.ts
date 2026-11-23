import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { classifyMock } = vi.hoisted(() => ({ classifyMock: vi.fn() }))

vi.mock('../src/api/pattern', () => ({
  classifyPattern: classifyMock,
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.status = status
    }
  },
}))

import { ApiError } from '../src/api/pattern'
import PatternPanel from '../src/components/PatternPanel.vue'

const FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
const payload = {
  labels: [
    { label: 'kingsideAttack', probability: 0.61 },
    { label: 'fork', probability: 0.42 },
    { label: 'pin', probability: 0.1 },
  ],
  model_version: '0.1.0',
}

beforeEach(() => {
  classifyMock.mockReset()
})

describe('PatternPanel', () => {
  it('nonaktif saat giliran hitam', async () => {
    const wrapper = mount(PatternPanel, { props: { fen: FEN, turn: 'black' } })
    const button = wrapper.find('button.primary')

    expect(button.attributes('disabled')).toBeDefined()
    await button.trigger('click')
    expect(classifyMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('hanya tersedia saat giliran putih')
  })

  it('menampilkan dua motif teratas dengan catatan eksperimental', async () => {
    classifyMock.mockResolvedValue(payload)
    const wrapper = mount(PatternPanel, { props: { fen: FEN, turn: 'white' } })

    await wrapper.find('button.primary').trigger('click')
    await flushPromises()

    expect(classifyMock.mock.calls[0][0]).toBe(FEN)
    expect(wrapper.findAll('.result-list li')).toHaveLength(2)
    expect(wrapper.text()).toContain('kingside Attack')
    expect(wrapper.text()).toContain('61.0%')
    expect(wrapper.text()).toContain('eksperimental')
  })

  it('menampilkan pesan error sebagai teks biasa', async () => {
    classifyMock.mockRejectedValue(new ApiError('Model belum tersedia', 503))
    const wrapper = mount(PatternPanel, { props: { fen: FEN, turn: 'white' } })

    await wrapper.find('button.primary').trigger('click')
    await flushPromises()

    expect(wrapper.find('.error').text()).toBe('Model belum tersedia')
  })

  it('membatalkan request saat posisi berubah', async () => {
    let capturedSignal: AbortSignal | undefined
    classifyMock.mockImplementation((_fen: string, signal?: AbortSignal) => {
      capturedSignal = signal
      return new Promise(() => {})
    })
    const wrapper = mount(PatternPanel, { props: { fen: FEN, turn: 'white' } })

    await wrapper.find('button.primary').trigger('click')
    expect(wrapper.text()).toContain('Menghubungi model…')

    await wrapper.setProps({ fen: 'posisi-baru' })
    expect(capturedSignal?.aborted).toBe(true)
    expect(wrapper.text()).not.toContain('Menghubungi model…')
    expect(wrapper.findAll('.result-list')).toHaveLength(0)
  })

  it('mengabaikan respons lama setelah posisi berubah', async () => {
    let resolveFirst: (value: typeof payload) => void = () => {}
    classifyMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve
        }),
    )
    const wrapper = mount(PatternPanel, { props: { fen: FEN, turn: 'white' } })

    await wrapper.find('button.primary').trigger('click')
    await wrapper.setProps({ fen: 'posisi-baru' })
    resolveFirst(payload)
    await flushPromises()

    expect(wrapper.findAll('.result-list')).toHaveLength(0)
  })
})
