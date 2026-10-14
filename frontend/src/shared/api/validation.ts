// O contrato do APIFlask agrupa erros por origem: detail.json, detail.query etc.
export function validationMessages<Field extends string>(
  detail: unknown, fields: readonly Field[], location = 'json',
): Record<Field, string> {
  const source = typeof detail === 'object' && detail !== null
    ? (detail as Record<string, unknown>)[location] : undefined
  return Object.fromEntries(fields.map(field => {
    const messages = typeof source === 'object' && source !== null
      ? (source as Record<string, unknown>)[field] : undefined
    const message = Array.isArray(messages) && typeof messages[0] === 'string' ? messages[0] : ''
    return [field, message]
  })) as Record<Field, string>
}
