import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { GraduationCap, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { authAPI, getErrorMessage } from '../utils/api'
import { safeRedirect } from '../utils/password'
import { STAGE_SUBJECTS } from '../utils/stageSubjects'

const ProfileStep = ({ user, onDone }) => {
  const { updateProfile } = useAuth()
  const [name, setName] = useState(() => (/^老师\d{4}$/.test(user?.display_name || '') ? '' : (user?.display_name || '')))
  const [stage, setStage] = useState(user?.education_stage || '')
  const [subject, setSubject] = useState(() => {
    const current = user?.subject || ''
    return (STAGE_SUBJECTS[user?.education_stage] || []).includes(current) ? current : ''
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const subjects = STAGE_SUBJECTS[stage] || []

  const chooseSubject = (item) => {
    setSubject(item)
    setError('')
  }

  const save = async (e) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('请填写姓名')
      return
    }
    if (!stage) {
      setError('请选择学段')
      return
    }
    if (!subject) {
      setError('请选择学科')
      return
    }
    setSaving(true)
    setError('')
    try {
      const data = await updateProfile({ display_name: trimmed, education_stage: stage, subject })
      onDone(data)
    } catch (err) {
      setError(getErrorMessage(err, '保存失败，请稍后重试'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="mx-auto w-full max-w-lg space-y-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6" noValidate>
      <div>
        <h2 className="text-base font-semibold text-gray-900">填写基本信息</h2>
        <p className="mt-1 text-xs text-gray-400">进入体验前，请告诉我你的姓名、学段和学科</p>
      </div>
      {error && (
        <div className="flex items-start space-x-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      <div>
        <label htmlFor="profile-name" className="mb-1.5 block text-sm font-medium text-gray-700">姓名</label>
        <input
          id="profile-name"
          value={name}
          onChange={(e) => { setName(e.target.value); setError('') }}
          placeholder="你的姓名"
          className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <fieldset>
        <legend className="mb-1.5 text-sm font-medium text-gray-700">学段</legend>
        <div className="grid grid-cols-4 gap-2">
          {Object.keys(STAGE_SUBJECTS).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => { setStage(item); setSubject(''); setError('') }}
              className={`rounded-lg border px-2 py-2 text-sm ${stage === item ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700'}`}
            >
              {item}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-1.5 text-sm font-medium text-gray-700">学科</legend>
        {subjects.length === 0 ? (
          <p className="text-sm text-gray-400">请先选择学段</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {subjects.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => chooseSubject(item)}
                className={`rounded-lg border px-3 py-1.5 text-sm ${subject === item ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700'}`}
              >
                {item}
              </button>
            ))}
          </div>
        )}
      </fieldset>
      <button
        type="submit"
        disabled={saving}
        className="flex w-full items-center justify-center rounded-lg bg-blue-600 py-2.5 text-base font-medium text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        {saving ? '保存中…' : '进入体验'}
      </button>
    </form>
  )
}

const LoginPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, loading, login, notice, setNotice } = useAuth()
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [issuedCode, setIssuedCode] = useState('')
  const [showCode, setShowCode] = useState(false)
  const [phoneStep, setPhoneStep] = useState('ask')
  const [adminMode, setAdminMode] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [issuing, setIssuing] = useState(false)
  const [error, setError] = useState('')

  const redirect = safeRedirect(searchParams.get('redirect'))

  useEffect(() => {
    document.title = '登录 - AI 教学助手'
  }, [])

  const afterLogin = user?.role === 'admin' && redirect === '/' ? '/usage' : redirect

  if (!loading && user && !user.is_guest && !user.needs_profile) {
    return <Navigate to={user.must_change_password ? `/set-password?redirect=${encodeURIComponent(afterLogin)}` : afterLogin} replace />
  }

  const handleIssue = async () => {
    const trimmed = phone.replace(/[\s-]/g, '')
    if (!/^1[3-9]\d{9}$/.test(trimmed)) {
      setError('请输入 11 位手机号')
      return
    }
    setIssuing(true)
    setError('')
    try {
      const data = await authAPI.phoneCode(trimmed)
      setPhone(data.phone || trimmed)
      setCode(data.code || '')
      setIssuedCode(data.code || '')
      setShowCode(true)
      setPhoneStep('issued')
      setNotice('')
    } catch (err) {
      if (!err?.response) setError('无法连接服务器，请检查网络后重试')
      else setError(getErrorMessage(err, '暂时领不到注册码，请稍后重试'))
    } finally {
      setIssuing(false)
    }
  }

  const handlePhoneLogin = async (e) => {
    e.preventDefault()
    const trimmed = phone.replace(/[\s-]/g, '')
    if (!/^1[3-9]\d{9}$/.test(trimmed)) {
      setError('请输入 11 位手机号')
      return
    }
    if (!code.trim()) {
      setError('请输入注册码')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const data = await login(trimmed, code.trim())
      if (data?.needs_profile) return
      navigate(data.must_change_password ? `/set-password?redirect=${encodeURIComponent(redirect)}` : redirect, { replace: true })
    } catch (err) {
      const status = err?.response?.status
      if (!err?.response) setError('无法连接服务器，请检查网络后重试')
      else if (status === 401 || status === 429) setError(getErrorMessage(err))
      else setError(getErrorMessage(err, '登录失败，请稍后重试'))
      setNotice('')
    } finally {
      setSubmitting(false)
    }
  }

  const handleAdminLogin = async (e) => {
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
      const dest = data?.role === 'admin' && redirect === '/' ? '/usage' : redirect
      if (data.must_change_password) {
        navigate(`/set-password?redirect=${encodeURIComponent(dest)}`, { replace: true })
      } else {
        navigate(dest, { replace: true })
      }
    } catch (err) {
      const status = err?.response?.status
      if (!err?.response) setError('无法连接服务器，请检查网络后重试')
      else if (status === 401 || status === 429) setError(getErrorMessage(err))
      else setError(getErrorMessage(err, '登录失败，请稍后重试'))
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
          <p className="mt-2 text-sm text-gray-500 sm:text-base">用手机号领取体验码即可进入。请自己保存体验码。</p>
        </div>

        <div className="mx-auto w-full max-w-lg lg:mx-0">
          {user?.needs_profile ? (
            <ProfileStep user={user} onDone={() => navigate(redirect, { replace: true })} />
          ) : (
          <>
          {message && (
            <div className="mb-4 flex items-start space-x-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700" role="alert">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{message}</span>
            </div>
          )}

          {!adminMode ? (
            <form onSubmit={phoneStep === 'ask' ? (e) => { e.preventDefault(); handleIssue() } : handlePhoneLogin} className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6" noValidate>
              <div>
                <h2 className="text-base font-semibold text-gray-900">手机号体验</h2>
                <p className="mt-1 text-xs text-gray-400">
                  {phoneStep === 'returning' ? '输入手机号和上次保存的体验码' : '第一次使用先领取体验码，并记下来'}
                </p>
              </div>

              {issuedCode && phoneStep === 'issued' && (
                <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-3 text-sm text-blue-800">
                  <div>体验码 <span className="font-mono text-lg font-semibold tracking-widest">{issuedCode}</span></div>
                  <p className="mt-1 text-xs text-blue-700">请记下来。下次用同一个手机号和这个码进入。重新领取会使旧码失效。</p>
                </div>
              )}

              <div>
                <label htmlFor="login-phone" className="block text-sm font-medium text-gray-700 mb-1.5">手机号</label>
                <input
                  id="login-phone"
                  name="tel"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel"
                  value={phone}
                  onChange={(e) => { setPhone(e.target.value); setError('') }}
                  placeholder="11 位手机号"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {phoneStep !== 'ask' && (
                <div>
                  <label htmlFor="login-code" className="block text-sm font-medium text-gray-700 mb-1.5">体验码</label>
                  <div className="relative">
                    <input
                      id="login-code"
                      name="one-time-code"
                      type={showCode || phoneStep === 'issued' ? 'text' : 'password'}
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={code}
                      onChange={(e) => { setCode(e.target.value); setError('') }}
                      placeholder="6 位体验码"
                      className="w-full px-3 py-2.5 pr-10 border border-gray-300 rounded-lg text-base tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    {phoneStep === 'returning' && (
                      <button
                        type="button"
                        onClick={() => setShowCode(v => !v)}
                        className="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600"
                        aria-label={showCode ? '隐藏体验码' : '显示体验码'}
                      >
                        {showCode ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    )}
                  </div>
                </div>
              )}

              {phoneStep === 'ask' ? (
                <button
                  type="submit"
                  disabled={issuing}
                  className="w-full flex items-center justify-center py-2.5 rounded-lg bg-blue-600 text-white text-base font-medium hover:bg-blue-700 disabled:opacity-60"
                >
                  {issuing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  {issuing ? '获取中…' : '获取体验码'}
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={submitting || issuing}
                  className="w-full flex items-center justify-center py-2.5 rounded-lg bg-blue-600 text-white text-base font-medium hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  {submitting ? '进入中…' : '进入体验'}
                </button>
              )}

              <div className="flex items-center justify-between text-sm">
                {phoneStep === 'ask' ? (
                  <button type="button" className="text-gray-500 hover:text-gray-700" onClick={() => { setPhoneStep('returning'); setError(''); setNotice('') }}>
                    已有体验码
                  </button>
                ) : (
                  <button type="button" className="text-gray-500 hover:text-gray-700" onClick={() => { setPhoneStep('ask'); setIssuedCode(''); setCode(''); setError(''); setNotice('') }}>
                    重新领取
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => { setAdminMode(true); setError(''); setNotice('') }}
                  className="text-gray-500 hover:text-gray-700"
                >
                  管理员登录
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleAdminLogin} className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6" noValidate>
              <div>
                <h2 className="text-base font-semibold text-gray-900">管理员登录</h2>
                <p className="mt-1 text-xs text-gray-400">查看各账号用量，或使用学校已开通的账号</p>
              </div>

              <div>
                <label htmlFor="login-username" className="block text-sm font-medium text-gray-700 mb-1.5">账号</label>
                <input
                  id="login-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => { setUsername(e.target.value); setError('') }}
                  placeholder="管理员账号"
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
                disabled={submitting}
                className="w-full flex items-center justify-center py-2.5 rounded-lg bg-blue-600 text-white text-base font-medium hover:bg-blue-700 disabled:opacity-60"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {submitting ? '登录中…' : '登录'}
              </button>

              <button
                type="button"
                onClick={() => { setAdminMode(false); setError(''); setNotice('') }}
                className="w-full text-sm text-gray-500 hover:text-gray-700"
              >
                返回手机号登录
              </button>
            </form>
          )}
          </>
          )}
        </div>
      </div>
    </div>
  )
}

export default LoginPage
