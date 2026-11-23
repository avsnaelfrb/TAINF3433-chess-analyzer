import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  API_TIMEOUT_MS,
  ApiError,
  classifyPattern,
  type AnalyzeResponse,
} from '../src/api/pattern'

const FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
const payload: AnalyzeResponse = {
  labels: Array.from({ length: 23 }, (_, index) => ({
    label: `theme${index}`,
    probability: 1 - index / 23,
  })),
  model_version: '0.1.0',
}

function fakeResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  vi.useRealTimers()
})

describe('classifyPattern', () => {
  it('mengirim payload FEN ke /api/analyze-pattern', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(payload))
    vi.stubGlobal('fetch', fetchMock)

    await expect(classifyPattern(FEN)).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/analyze-pattern',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fen: FEN }),
      }),
    )
  })

  it('memakai VITE_API_BASE bila di-set', async () => {
    vi.stubEnv('VITE_API_BASE', 'http://localhost:8000/api/')
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(payload))
    vi.stubGlobal('fetch', fetchMock)

    await classifyPattern(FEN)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/api/analyze-pattern')
  })

  it.each([
    [422, 'FEN tidak valid'],
    [503, 'Model belum tersedia'],
  ])('menampilkan detail HTTP %i sebagai ApiError', async (status, detail) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(fakeResponse({ detail }, status)))

    await expect(classifyPattern(FEN)).rejects.toMatchObject({
      name: 'ApiError',
      status,
      message: detail,
    })
  })

  it('mengubah gagal jaringan menjadi status 0', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(classifyPattern(FEN)).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
      message: 'Gagal terhubung ke server',
    })
  })

  it('meneruskan abort dari pemanggil', async () => {
    const controller = new AbortController()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () => {
              reject(new DOMException('Aborted', 'AbortError'))
            })
          }),
      ),
    )

    const request = classifyPattern(FEN, controller.signal)
    controller.abort()
    await expect(request).rejects.toMatchObject({ name: 'AbortError' })
    await expect(request).rejects.not.toBeInstanceOf(ApiError)
  })

  it('mengubah timeout 15 detik menjadi ApiError status 0', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () => {
              reject(new DOMException('Aborted', 'AbortError'))
            })
          }),
      ),
    )

    const assertion = expect(classifyPattern(FEN)).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
      message: 'Permintaan habis waktu',
    })
    await vi.advanceTimersByTimeAsync(API_TIMEOUT_MS)
    await assertion
  })
})
