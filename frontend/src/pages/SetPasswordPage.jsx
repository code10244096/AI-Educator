import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { KeyRound, Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/api'
import { PASSWORD_RULE, safeRedirect, validateNewPassword } from '../utils/password'

// 首次登录（或密码被管理员重置后）必须先设置自己的新密码
const SetPasswordPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, loading, changePassword, logout } = useAuth()
  const [form, setForm] = useState({ old: '', next: '', confirm: '' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const redirect = safeRedirect(searchParams.get('redirect'))

  useEffect(() => {
    document.title = '设置新密码 - AI 教学助手'
  }, [])

  if (!loading && !user) return <Navigate to="/login" replace />
  if (!loading && user && !user.must_change_password) return <Navigate to={redirect} replace />

  const update = (key) => (e) => {
    setForm(prev => ({ ...prev, [key]: e.target.value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.old) return setError('请输入初始密码')
    const problem = validateNewPassword(form.next)
    if (problem) return setError(problem)
    if (form.next !== form.confirm) return setError('两次输入的新密码不一致')
    if (form.next === form.old) return setError('新密码不能与初始密码相同')
    setSubmitting(true)
    try {
      await changePassword(form.old, form.next)
      navigate(redirect, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, '设置失败，请重试'))
    } finally {
      setSubmitting(false)
    }
  }

  const inputClass = 'w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 mb-4">
            <KeyRound className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">设置新密码</h1>
          <p className="mt-2 text-sm text-gray-500">
            {user?.display_name ? `${user.display_name}，` : ''}为了账号安全，请先把初始密码改成只有你知道的新密码
          </p>
        </div>
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4" noValidate>
          {error && (
            <div className="flex items-start space-x-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700" role="alert">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div>
            <label htmlFor="sp-old" className="block text-sm font-medium text-gray-700 mb-1.5">初始密码</label>
            <input id="sp-old" type="password" autoComplete="current-password" value={form.old} onChange={update('old')} className={inputClass} autoFocus />
          </div>
          <div>
            <label htmlFor="sp-new" className="block text-sm font-medium text-gray-700 mb-1.5">新密码</label>
            <input id="sp-new" type="password" autoComplete="new-password" value={form.next} onChange={update('next')} className={inputClass} />
            <p className="mt-1 text-xs text-gray-400">{PASSWORD_RULE}</p>
          </div>
          <div>
            <label htmlFor="sp-confirm" className="block text-sm font-medium text-gray-700 mb-1.5">再次输入新密码</label>
            <input id="sp-confirm" type="password" autoComplete="new-password" value={form.confirm} onChange={update('confirm')} className={inputClass} />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            保存并进入
          </button>
          <button type="button" onClick={logout} className="w-full text-center text-xs text-gray-400 hover:text-gray-600">
            退出登录
          </button>
        </form>
      </div>
    </div>
  )
}

export default SetPasswordPage
