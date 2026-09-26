import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authAPI, setAuthHandlers, MSG_SESSION_EXPIRED } from '../utils/api'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

// 退出 / 换账号时清掉浏览器里残留的上一位老师的数据
const clearLocalData = () => {
  try {
    localStorage.removeItem('globalTasks')
    localStorage.removeItem('isLoggedIn')
    localStorage.removeItem('userName')
  } catch (e) {
    // 浏览器禁用本地存储时忽略
  }
}

export const AuthProvider = ({ children }) => {
  // undefined = 正在确认登录状态；null = 未登录
  const [user, setUser] = useState(undefined)
  // 登录页上显示的提示（如“登录已过期，请重新登录”）
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let cancelled = false
    authAPI.me()
      .then((data) => { if (!cancelled) setUser(data) })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.data?.detail === MSG_SESSION_EXPIRED) setNotice(MSG_SESSION_EXPIRED)
        setUser(null)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    setAuthHandlers({
      onUnauthorized: (message) => {
        clearLocalData()
        setNotice(message || MSG_SESSION_EXPIRED)
        setUser(null)
      },
      onMustChangePassword: () => {
        setUser(prev => (prev ? { ...prev, must_change_password: true } : prev))
      },
    })
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await authAPI.login(username, password)
    clearLocalData()
    setNotice('')
    setUser(data)
    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      await authAPI.logout()
    } catch (e) {
      // 网络异常时也在本地退出
    }
    clearLocalData()
    setNotice('')
    setUser(null)
  }, [])

  const changePassword = useCallback(async (oldPassword, newPassword) => {
    const data = await authAPI.changePassword(oldPassword, newPassword)
    if (data?.user) setUser(data.user)
    return data
  }, [])

  const updateProfile = useCallback(async (profile) => {
    const data = await authAPI.updateProfile(profile)
    setUser(data)
    return data
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      loading: user === undefined,
      isAdmin: user?.role === 'admin',
      notice,
      setNotice,
      login,
      logout,
      changePassword,
      updateProfile,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
