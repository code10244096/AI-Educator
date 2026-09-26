import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// 路由守卫：未登录 → /login?redirect=<原路径>；初始密码未修改 → 只能看到“设置新密码”页
const RequireAuth = ({ children }) => {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />
      </div>
    )
  }

  const current = `${location.pathname}${location.search}`
  if (!user) {
    const redirect = current && current !== '/' ? `?redirect=${encodeURIComponent(current)}` : ''
    return <Navigate to={`/login${redirect}`} replace />
  }

  if (user.must_change_password) {
    const redirect = current && current !== '/' ? `?redirect=${encodeURIComponent(current)}` : ''
    return <Navigate to={`/set-password${redirect}`} replace />
  }

  return children
}

export default RequireAuth
