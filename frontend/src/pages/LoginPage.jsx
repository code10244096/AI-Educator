import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { GraduationCap, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/api'
import { safeRedirect } from '../utils/password'

const LoginPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, loading, login, notice, setNotice } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const redirect = safeRedirect(searchParams.get('redirect'))

  useEffect(() => {
    document.title = '登录 - AI 教学助手'
  }, [])

  if (!loading && user) {
    return <Navigate to={user.must_change_password ? `/set-password?redirect=${encodeURIComponent(redirect)}` : redirect} replace />
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim()) {
      setError('请输入账号')
      return
    }
    if (!password) {
      setError('请输入密码')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const data = await login(username.trim(), password)
      if (data.must_change_password) {
        navigate(`/set-password?redirect=${encodeURIComponent(redirect)}`, { replace: true })
      } else {
        navigate(redirect, { replace: true })
      }
    } catch (err) {
      const status = err?.response?.status
      if (!err?.response) {
        setError('无法连接服务器，请检查网络后重试')
      } else if (status === 401 || status === 429) {
        setError(getErrorMessage(err))
      } else {
        setError(getErrorMessage(err, '登录失败，请稍后重试'))
      }
      setNotice('')
    } finally {
      setSubmitting(false)
    }
  }

  const message = error || notice

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 mb-4">
            <GraduationCap className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">AI 教学助手</h1>
          <p className="mt-2 text-sm text-gray-500">拍照上传作业，AI 逐题批改，老师一键复核</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5"
          noValidate
        >
          {message && (
            <div className="flex items-start space-x-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700" role="alert">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{message}</span>
            </div>
          )}

          <div>
            <label htmlFor="login-username" className="block text-sm font-medium text-gray-700 mb-1.5">账号</label>
            <input
              id="login-username"
              name="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError('') }}
              placeholder="手机号或工号"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
            <div className="relative">
              <input
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError('') }}
                placeholder="请输入密码"
                className="w-full px-3 py-2.5 pr-10 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                className="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600"
                aria-label={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            {submitting ? '登录中…' : '登 录'}
          </button>

          <p className="text-center text-xs text-gray-400">忘记密码？请联系学校管理员重置</p>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
