import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { User, KeyRound, Save, Loader2, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/Toast'
import { getErrorMessage } from '../utils/api'
import { PASSWORD_RULE, validateNewPassword } from '../utils/password'

const inputClass = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'

const ProfileSection = () => {
  const { user, updateProfile } = useAuth()
  const { addToast } = useToast()
  const [form, setForm] = useState({ display_name: user?.display_name || '', school: user?.school || '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setForm({ display_name: user?.display_name || '', school: user?.school || '' })
  }, [user?.display_name, user?.school])

  const handleSave = async () => {
    if (!form.display_name.trim()) {
      addToast('姓名不能为空', 'error')
      return
    }
    setSaving(true)
    try {
      await updateProfile({ display_name: form.display_name.trim(), school: form.school.trim() })
      addToast('个人资料已保存', 'success')
    } catch (err) {
      addToast(getErrorMessage(err, '保存失败，请重试'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">个人资料</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="profile-name">姓名</label>
          <input
            id="profile-name"
            type="text"
            value={form.display_name}
            maxLength={50}
            onChange={(e) => setForm(prev => ({ ...prev, display_name: e.target.value }))}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-400">这是显示名称，可以修改</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="profile-account">账号</label>
          <input id="profile-account" type="text" value={user?.username || ''} disabled className={`${inputClass} bg-gray-50 text-gray-500`} />
          <p className="mt-1 text-xs text-gray-400">账号不能修改，如需更换请联系学校管理员</p>
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="profile-school">学校</label>
          <input
            id="profile-school"
            type="text"
            value={form.school}
            placeholder="选填，例如：某某中学"
            maxLength={100}
            onChange={(e) => setForm(prev => ({ ...prev, school: e.target.value }))}
            className={inputClass}
          />
        </div>
      </div>
      <div className="mt-6">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-60"
        >
          {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
          保存修改
        </button>
      </div>
    </div>
  )
}

const PasswordField = ({ id, label, value, onChange, autoComplete, hint }) => {
  const [visible, setVisible] = useState(false)
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor={id}>{label}</label>
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          className={`${inputClass} pr-10`}
        />
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          className="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600"
          aria-label={visible ? '隐藏密码' : '显示密码'}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

const PasswordSection = () => {
  const { changePassword } = useAuth()
  const { addToast } = useToast()
  const [form, setForm] = useState({ old: '', next: '', confirm: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const update = (key) => (e) => {
    setForm(prev => ({ ...prev, [key]: e.target.value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.old) return setError('请输入当前密码')
    const problem = validateNewPassword(form.next)
    if (problem) return setError(problem)
    if (form.next !== form.confirm) return setError('两次输入的新密码不一致')
    setSaving(true)
    try {
      await changePassword(form.old, form.next)
      setForm({ old: '', next: '', confirm: '' })
      addToast('密码已修改，下次请用新密码登录', 'success')
    } catch (err) {
      setError(getErrorMessage(err, '修改失败，请重试'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="p-6" onSubmit={handleSubmit} noValidate>
      <h3 className="text-lg font-semibold text-gray-900 mb-6">修改密码</h3>
      <div className="space-y-4 max-w-sm">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700" role="alert">{error}</div>
        )}
        <PasswordField id="pwd-old" label="当前密码" autoComplete="current-password" value={form.old} onChange={update('old')} />
        <PasswordField id="pwd-new" label="新密码" autoComplete="new-password" value={form.next} onChange={update('next')} hint={PASSWORD_RULE} />
        <PasswordField id="pwd-confirm" label="再次输入新密码" autoComplete="new-password" value={form.confirm} onChange={update('confirm')} />
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-60"
        >
          {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          确认修改
        </button>
      </div>
    </form>
  )
}

const SECTIONS = [
  { id: 'profile', label: '个人资料', icon: User },
  { id: 'password', label: '修改密码', icon: KeyRound },
]

const Settings = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get('section')
  const activeSection = SECTIONS.some(s => s.id === requested) ? requested : 'profile'

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900">设置</h2>
        <p className="text-sm text-gray-500 mt-1">个人资料与登录密码</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        <div className="md:w-56 flex-shrink-0">
          <nav className="bg-white rounded-xl border border-gray-200 overflow-hidden flex md:block">
            {SECTIONS.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setSearchParams(section.id === 'profile' ? {} : { section: section.id })}
                  className={`flex-1 md:w-full flex items-center justify-center md:justify-start space-x-2 md:space-x-3 px-4 py-3 text-sm transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-50 text-blue-600 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="whitespace-nowrap">{section.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-xl border border-gray-200">
            {activeSection === 'profile' && <ProfileSection />}
            {activeSection === 'password' && <PasswordSection />}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
