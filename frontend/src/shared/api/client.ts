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

const documentTypes = {
  pdf: 'application/pdf',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

async function requestBody(
  path: string,
  options: RequestInit = {},
  format: 'json' | 'pdf' | 'xlsx' = 'json',
  timeoutMs = 10000,
): Promise<unknown> {
  const method = (options.method ?? 'GET').toUpperCase()
  const writing = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  const headers = new Headers(options.headers)
  const documentType = format === 'json' ? null : documentTypes[format]
  headers.set('Accept', documentType ? `${documentType}, application/json` : 'application/json')
  // FormData precisa do boundary multipart definido pelo próprio navegador.
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (writing) {
    const token = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
    if (!token) throw new ApiError('Atualize a página para renovar a segurança da sessão.', 400)
    headers.set('X-CSRF-Token', token)
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
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
    const expectedContentType = response.ok && documentType ? documentType : 'application/json'
    if (!contentType.includes(expectedContentType)) {
      throw new ApiError(
        writing ? 'Resposta inesperada. Confira os dados antes de repetir a operação.'
          : 'O servidor devolveu uma resposta inesperada.',
        response.status,
      )
    }
    body = response.ok && documentType ? await response.blob() : await response.json()
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
  return body
}

export async function requestJson<T>(path: string, options: RequestInit = {}, timeoutMs = 10000): Promise<T> {
  return await requestBody(path, options, 'json', timeoutMs) as T
}

export async function requestPdf(path: string): Promise<Blob> {
  return await requestBody(path, { cache: 'no-store' }, 'pdf', 30000) as Blob
}

export async function requestExcel(path: string): Promise<Blob> {
  return await requestBody(path, { cache: 'no-store' }, 'xlsx', 30000) as Blob
}
