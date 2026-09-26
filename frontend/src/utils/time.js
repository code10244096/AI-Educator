// 后端 SQLite 的 created_at 等时间是不带时区的 UTC 时间，这里按 UTC 解析后再转本地显示
export const parseServerTime = (value) => {
  if (!value) return null
  if (value instanceof Date) return value
  const str = String(value)
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(str)
  return new Date(hasZone ? str : `${str.replace(' ', 'T')}Z`)
}

export const formatServerTime = (value) => {
  const d = parseServerTime(value)
  return d && !Number.isNaN(d.getTime()) ? d.toLocaleString('zh-CN') : ''
}
