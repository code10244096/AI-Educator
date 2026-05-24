import React, { createContext, useContext, useState } from 'react'

const LayoutContext = createContext()

export const useLayout = () => {
  const context = useContext(LayoutContext)
  if (!context) {
    throw new Error('useLayout must be used within LayoutProvider')
  }
  return context
}

export const LayoutProvider = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  
  const toggleSidebar = () => {
    setSidebarOpen(prev => !prev)
  }
  
  const closeSidebar = () => {
    setSidebarOpen(false)
  }
  
  return (
    <LayoutContext.Provider value={{ sidebarOpen, toggleSidebar, closeSidebar }}>
      {children}
    </LayoutContext.Provider>
  )
}
