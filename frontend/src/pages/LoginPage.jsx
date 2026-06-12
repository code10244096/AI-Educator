import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, User, Lock, Eye, EyeOff, LogIn, ArrowLeft } from 'lucide-react'

const LoginPage = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    account: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [loginSuccess, setLoginSuccess] = useState(false)
  const [errors, setErrors] = useState({})

  const validateForm = () => {
    const newErrors = {}
    if (!formData.account.trim()) {
      newErrors.account = '请输入账号（姓名/手机号/邮箱）'
    }
    if (!formData.password) {
      newErrors.password = '请输入密码'
    } else if (formData.password.length < 6) {
      newErrors.password = '密码长度不能少于6位'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) return

    setIsLoading(true)
    
    // 模拟登录请求
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 验证成功（模拟）
    if (formData.password === '123456') {
      setLoginSuccess(true)
      // 保存登录状态
      localStorage.setItem('isLoggedIn', 'true')
      localStorage.setItem('userName', formData.account || '教师')
    } else {
      setErrors({ password: '密码错误，请输入 123456' })
    }
    
    setIsLoading(false)
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    // 清除对应字段的错误
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }
  }

  if (loginSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">登录成功</h2>
          <p className="text-gray-600 mb-8">欢迎回来，{formData.account || '教师'}！</p>
          <button
            onClick={() => navigate('/')}
            className="w-full inline-flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <GraduationCap className="h-5 w-5 mr-2" />
            进入系统
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* 返回按钮 */}
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center space-x-1 text-gray-500 hover:text-gray-700 mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">返回首页</span>
        </button>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* Logo 和标题 */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center space-x-2 mb-4">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg p-2">
                <GraduationCap className="h-8 w-8 text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">AI 教学助手</h1>
            <p className="text-gray-500 mt-1">教师版登录</p>
          </div>

          {/* 登录表单 */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* 账号（姓名/手机号/邮箱三选一） */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">账号</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  name="account"
                  value={formData.account}
                  onChange={handleInputChange}
                  placeholder="请输入姓名、手机号或邮箱"
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                />
              </div>
              {errors.account && (
                <p className="mt-1 text-sm text-red-600">{errors.account}</p>
              )}
            </div>

            {/* 密码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="请输入密码（演示密码：123456）"
                  className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password}</p>
              )}
            </div>

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full inline-flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  登录中...
                </>
              ) : (
                <>
                  <LogIn className="h-5 w-5 mr-2" />
                  登录
                </>
              )}
            </button>
          </form>

          {/* 底部提示 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              演示账号：密码输入 <span className="font-mono bg-gray-100 px-2 py-0.5 rounded">123456</span> 即可登录
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage