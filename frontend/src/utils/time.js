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

// “刚刚 / 5 分钟前 / 今天 14:30 / 9月25日”
export const formatRelative = (value) => {
  const d = parseServerTime(value)
  if (!d || Number.isNaN(d.getTime())) return ''
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  const now = new Date()
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (d.toDateString() === now.toDateString()) return `今天 ${hm}`
  const y = new Date(now)
  y.setDate(now.getDate() - 1)
  if (d.toDateString() === y.toDateString()) return `昨天 ${hm}`
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}月${d.getDate()}日`
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}
