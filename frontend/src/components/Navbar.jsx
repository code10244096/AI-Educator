import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, Menu, ChevronDown, User, KeyRound, LogOut } from 'lucide-react'
import { useLayout } from '../context/LayoutContext'
import { useAuth } from '../context/AuthContext'
import TaskDrawer from './TaskDrawer'

const UserMenu = () => {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  if (!user) return null
  const name = user.display_name || user.username

  const go = (path) => {
    setOpen(false)
    navigate(path)
  }

  const handleLogout = async () => {
    setOpen(false)
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center space-x-2 px-2 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-medium">
          {name.slice(0, 1)}
        </span>
        <span className="inline text-sm font-medium text-gray-700 max-w-[4.5rem] sm:max-w-[8rem] truncate" data-testid="navbar-user-name">{name}</span>
        <ChevronDown className="h-4 w-4 text-gray-400" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-44 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50" role="menu">
          <div className="px-3 py-2 border-b border-gray-100">
            <div className="text-sm font-medium text-gray-900 truncate">{name}</div>
            <div className="text-xs text-gray-400 truncate">{user.is_guest ? '公测体验' : user.username}</div>
          </div>
          <button role="menuitem" onClick={() => go('/settings')} className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
            <User className="h-4 w-4 text-gray-400" />
            <span>个人资料</span>
          </button>
          {user.is_guest ? (
            <button role="menuitem" onClick={() => go('/login')} className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
              <KeyRound className="h-4 w-4 text-gray-400" />
              <span>已有账号登录</span>
            </button>
          ) : (
            <button role="menuitem" onClick={() => go('/settings?section=password')} className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
              <KeyRound className="h-4 w-4 text-gray-400" />
              <span>修改密码</span>
            </button>
          )}
          {!user.is_guest && (
            <button role="menuitem" onClick={handleLogout} className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50">
              <LogOut className="h-4 w-4" />
              <span>退出登录</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const Navbar = () => {
  const navigate = useNavigate()
  const { toggleSidebar, sidebarOpen } = useLayout()
  const { user } = useAuth()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 h-16">
      <div className="h-full px-3 sm:px-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {/* 窄屏打开菜单抽屉；桌面侧栏常驻，不需要这个按钮 */}
          <button
            type="button"
            onClick={toggleSidebar}
            className="lg:hidden p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label={sidebarOpen ? '关闭菜单' : '打开菜单'}
          >
            <Menu className="h-5 w-5" />
          </button>
          <button
            type="button"
            className="flex items-center gap-2 hover:opacity-80 transition-opacity min-w-0"
            onClick={() => navigate('/')}
            aria-label="回到工作台"
          >
            <span className="bg-blue-600 rounded-lg p-1.5 flex-shrink-0">
              <GraduationCap className="h-5 w-5 text-white" />
            </span>
            <span className="text-base font-bold text-gray-900 whitespace-nowrap">AI 教学助手</span>
            {user?.is_guest && (
              <span className="text-xs font-medium text-blue-700 bg-blue-50 border border-blue-100 rounded-full px-2 py-0.5">公测</span>
            )}
          </button>
        </div>

        <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
          <TaskDrawer />
          <UserMenu />
        </div>
      </div>
    </nav>
  )
}

export default Navbar
