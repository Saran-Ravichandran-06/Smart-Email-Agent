const BAD_TASK_PATTERNS = [
  /^\s*```/i,
  /^\s*\/\//,
  /^\s*\{?\s*"?\s*(tasks?|deadline|due|items|actions|todos)\s*"?\s*:?/i,
  /^\s*[\[\]\{\},]\s*$/,
  /\bassuming today\b/i,
]

export function cleanTaskTitle(value: string | null | undefined): string | null {
  if (!value) return null
  let text = value.trim()
  text = text.replace(/^```(?:json)?/i, '').replace(/```$/i, '').trim()
  text = text.replace(/^\s*(?:[-*]|\d+[.)])\s*/, '').trim()
  text = text.replace(/^(?:task|action|todo|title)\s*[:=\-]\s*/i, '').trim()
  text = text.replace(/^["']|["'],?$/g, '').trim()
  if (!text || ['null', 'none', 'n/a', '[]', '{}'].includes(text.toLowerCase())) {
    return null
  }
  if (BAD_TASK_PATTERNS.some((pattern) => pattern.test(text))) {
    return null
  }
  if (/[{}\[\]]/.test(text)) {
    return null
  }
  return text
}
