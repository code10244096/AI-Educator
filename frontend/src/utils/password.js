// 与后端一致的新密码规则：8~64 位，同时包含字母和数字
export const PASSWORD_RULE = '新密码至少 8 位，且需同时包含字母和数字'

export const validateNewPassword = (password) => {
  const value = password || ''
  if (value.length < 8) return PASSWORD_RULE
  if (value.length > 64) return '新密码不能超过 64 位'
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return PASSWORD_RULE
  return ''
}

// 只允许站内相对路径作为登录后的跳转目标，防止跳到外部网站
export const safeRedirect = (value) => {
  if (!value || typeof value !== 'string') return '/'
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return '/'
  if (value.startsWith('/login') || value.startsWith('/set-password')) return '/'
  return value
}
