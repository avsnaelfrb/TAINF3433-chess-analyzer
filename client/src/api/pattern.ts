export const API_TIMEOUT_MS = 15_000

export interface PatternLabel {
  label: string
  probability: number
}

export interface AnalyzeResponse {
  labels: PatternLabel[]
  model_version: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function baseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE || '/api'
  return raw.replace(/\/+$/, '')
}

function detailFrom(payload: unknown): string | null {
  if (typeof payload !== 'object' || payload === null) return null
  const detail = (payload as { detail?: unknown }).detail
  return typeof detail === 'string' ? detail : null
}

function isLabel(value: unknown): value is PatternLabel {
  if (typeof value !== 'object' || value === null) return false
  const label = value as Partial<PatternLabel>
  return (
    typeof label.label === 'string' &&
    typeof label.probability === 'number' &&
    Number.isFinite(label.probability)
  )
}

function isAnalyzeResponse(payload: unknown): payload is AnalyzeResponse {
  if (typeof payload !== 'object' || payload === null) return false
  const response = payload as Partial<AnalyzeResponse>
  return (
    Array.isArray(response.labels) &&
    response.labels.every(isLabel) &&
    typeof response.model_version === 'string'
  )
}

export async function classifyPattern(
  fen: string,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, API_TIMEOUT_MS)

  const forwardAbort = () => controller.abort(signal?.reason)
  if (signal) {
    if (signal.aborted) controller.abort(signal.reason)
    else signal.addEventListener('abort', forwardAbort, { once: true })
  }

  try {
    const response = await fetch(`${baseUrl()}/analyze-pattern`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fen }),
      signal: controller.signal,
    })

    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      // Error responses without JSON still get a usable message below.
    }

    if (!response.ok) {
      throw new ApiError(detailFrom(payload) ?? `HTTP ${response.status}`, response.status)
    }
    if (!isAnalyzeResponse(payload)) {
      throw new ApiError('Respons model tidak valid', response.status)
    }
    return payload
  } catch (error) {
    if (timedOut) throw new ApiError('Permintaan habis waktu', 0)
    if (error instanceof ApiError) throw error
    if (signal?.aborted) throw error
    if (error instanceof TypeError) throw new ApiError('Gagal terhubung ke server', 0)
    throw error
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', forwardAbort)
  }
}
