import React, { createContext, useCallback, useContext, useState } from 'react'

const LayoutContext = createContext()

const COLLAPSE_KEY = 'sidebarCollapsed'

export const useLayout = () => {
  const context = useContext(LayoutContext)
  if (!context) {
    throw new Error('useLayout must be used within LayoutProvider')
  }
  return context
}

const readCollapsed = () => {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1'
  } catch {
    return false
  }
}

// 桌面（≥1024px）侧栏常驻，可折叠为图标栏（记在 localStorage）；窄屏为抽屉（sidebarOpen）
export const LayoutProvider = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(readCollapsed)

  const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), [])
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])
  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0')
      } catch {
        // 本地存储不可用时只在本次会话生效
      }
      return next
    })
  }, [])

  return (
    <LayoutContext.Provider value={{ sidebarOpen, toggleSidebar, closeSidebar, collapsed, toggleCollapsed }}>
      {children}
    </LayoutContext.Provider>
  )
}
