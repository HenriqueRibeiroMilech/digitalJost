export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail: unknown = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const writing = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body) headers.set('Content-Type', 'application/json')
  if (writing) {
    const token = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
    if (!token) throw new ApiError('Atualize a página para renovar a segurança da sessão.', 400)
    headers.set('X-CSRF-Token', token)
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 10000)
  let response: Response
  let body: unknown
  try {
    response = await fetch(path, {
      ...options,
      headers,
      credentials: 'same-origin',
      signal: controller.signal,
    })
    if (response.redirected) {
      throw new ApiError('A sessão precisa ser renovada. Acesse novamente o portal.', 401)
    }
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) {
      throw new ApiError(
        writing ? 'Resposta inesperada. Confira os dados antes de repetir a operação.'
          : 'O servidor devolveu uma resposta inesperada.',
        response.status,
      )
    }
    body = await response.json()
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(
      writing ? 'Não foi possível confirmar a operação. Confira os dados antes de tentar novamente.'
        : 'Não foi possível carregar os dados. Verifique a conexão.',
      0,
    )
  } finally {
    window.clearTimeout(timeout)
  }

  if (!response.ok) {
    const value = typeof body === 'object' && body !== null
      ? body as { message?: unknown; detail?: unknown } : {}
    const message = response.status === 401 ? 'Sua sessão expirou. Acesse novamente o portal.'
      : response.status === 403 ? 'Você não tem permissão para esta operação.'
      : response.status >= 500 ? 'Não foi possível concluir a operação.'
      : typeof value.message === 'string' ? value.message : 'Revise os dados enviados.'
    throw new ApiError(message, response.status, value.detail)
  }
  return body as T
}
