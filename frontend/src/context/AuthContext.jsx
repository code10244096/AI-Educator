import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
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
    localStorage.removeItem('isLoggedIn')
    localStorage.removeItem('userName')
  } catch (e) {
    // 浏览器禁用本地存储时忽略
  }
}

const skipAutoEnter = () => {
  const path = window.location.pathname
  return path === '/login' || path === '/set-password'
}

export const AuthProvider = ({ children }) => {
  // undefined = 正在确认登录状态；null = 未登录
  const [user, setUser] = useState(undefined)
  // 登录页上显示的提示（如“登录已过期，请重新登录”）
  const [notice, setNotice] = useState('')
  // 本次打开已经确认是公测（会话失效后重新进入，而不是回到登录页）
  const location = useLocation()
  const publicBetaRef = useRef(false)

  const adoptEnter = useCallback((data) => {
    publicBetaRef.current = Boolean(data?.public_beta)
    if (data && Object.prototype.hasOwnProperty.call(data, 'public_beta')) {
      const next = { ...data }
      delete next.public_beta
      return next
    }
    return data
  }, [])

  useEffect(() => {
    let cancelled = false
    authAPI.me()
      .then((data) => { if (!cancelled) setUser(data) })
      .catch(async (err) => {
        if (cancelled) return
        if (skipAutoEnter()) {
          if (err?.response?.data?.detail === MSG_SESSION_EXPIRED) setNotice(MSG_SESSION_EXPIRED)
          setUser(null)
          return
        }
        try {
          const data = adoptEnter(await authAPI.enter())
          if (!cancelled) setUser(data)
        } catch (enterErr) {
          if (cancelled) return
          if (enterErr?.response?.data?.detail === MSG_SESSION_EXPIRED) setNotice(MSG_SESSION_EXPIRED)
          setUser(null)
        }
      })
    return () => { cancelled = true }
  }, [adoptEnter])

  // 从登录页回到站内时再试一次自动进入（公测开启才会成功）
  useEffect(() => {
    if (user !== null || skipAutoEnter()) return undefined
    let cancelled = false
    authAPI.enter()
      .then((data) => { if (!cancelled) setUser(adoptEnter(data)) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [user, location.pathname, adoptEnter])

  useEffect(() => {
    setAuthHandlers({
      onUnauthorized: (message) => {
        clearLocalData()
        if (publicBetaRef.current && !skipAutoEnter()) {
          authAPI.enter()
            .then((data) => setUser(adoptEnter(data)))
            .catch(() => {
              setNotice(message || MSG_SESSION_EXPIRED)
              setUser(null)
            })
          return
        }
        setNotice(message || MSG_SESSION_EXPIRED)
        setUser(null)
      },
      onMustChangePassword: () => {
        setUser(prev => (prev ? { ...prev, must_change_password: true } : prev))
      },
    })
  }, [adoptEnter])

  const login = useCallback(async (username, password) => {
    const data = await authAPI.login(username, password)
    clearLocalData()
    publicBetaRef.current = false
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
