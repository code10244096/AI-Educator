import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { GraduationCap, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/api'
import { safeRedirect } from '../utils/password'

const LoginPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, loading, login, startTrial, notice, setNotice } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [entering, setEntering] = useState(false)
  const [error, setError] = useState('')

  const redirect = safeRedirect(searchParams.get('redirect'))

  useEffect(() => {
    document.title = '登录 - AI 教学助手'
  }, [])

  if (!loading && user && !user.is_guest) {
    return <Navigate to={user.must_change_password ? `/set-password?redirect=${encodeURIComponent(redirect)}` : redirect} replace />
  }

  const handleTrial = async () => {
    if (user?.is_guest) {
      navigate(redirect || '/', { replace: true })
      return
    }
    setEntering(true)
    setError('')
    try {
      const data = await startTrial()
      if (!data?.is_guest && data?.must_change_password) {
        navigate(`/set-password?redirect=${encodeURIComponent(redirect)}`, { replace: true })
      } else {
        navigate(redirect || '/', { replace: true })
      }
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (!err?.response) {
        setError('无法连接服务器，请检查网络后重试')
      } else if (detail === '请先登录' || err?.response?.status === 401) {
        setError('体验入口暂未开放，请使用已有账号登录')
      } else {
        setError(getErrorMessage(err, '暂时进不去，请稍后重试'))
      }
    } finally {
      setEntering(false)
    }
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
    <div className="min-h-screen overflow-y-auto bg-gray-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 lg:min-h-[calc(100vh-4rem)] lg:flex-row lg:items-center lg:gap-16">
        <div className="text-center lg:flex-1 lg:text-left">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 mb-4">
            <GraduationCap className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">AI 教学助手</h1>
          <p className="mt-2 text-sm text-gray-500 sm:text-base">拍照上传作业，AI 逐题批改，老师一键复核</p>
          <button
            type="button"
            onClick={handleTrial}
            disabled={entering || submitting}
            className="mt-6 inline-flex w-full max-w-sm items-center justify-center rounded-lg bg-blue-600 px-5 py-3 text-base font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
          >
            {entering ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {user?.is_guest ? '返回工作台' : '开始体验'}
          </button>
          <p className="mx-auto mt-3 max-w-sm text-xs text-gray-400 lg:mx-0">不用注册。点开始体验就能用，每位访客的数据互不影响。</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="mx-auto w-full max-w-sm space-y-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6 lg:mx-0"
          noValidate
        >
          <div>
            <h2 className="text-base font-semibold text-gray-900">已有账号</h2>
            <p className="mt-1 text-xs text-gray-400">学校发过账号的老师从这里登录</p>
          </div>

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
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                className="w-full px-3 py-2.5 pr-10 border border-gray-300 rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
            disabled={submitting || entering}
            className="w-full flex items-center justify-center py-2.5 rounded-lg border border-gray-300 bg-white text-gray-800 text-base font-medium hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            {submitting ? '登录中…' : '登录'}
          </button>

          <p className="text-center text-xs text-gray-400">忘记密码？请联系学校管理员重置</p>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
