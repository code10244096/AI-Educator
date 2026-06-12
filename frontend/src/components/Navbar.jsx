import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { GraduationCap, Bell, User, Search, Menu, LogIn } from 'lucide-react'
import { useLayout } from '../context/LayoutContext'

const Navbar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarOpen, toggleSidebar } = useLayout()
  
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 h-16">
      <div className="h-full px-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={toggleSidebar}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div
            className="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => navigate('/')}
          >
            <div className="bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg p-1.5">
              <GraduationCap className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-base font-bold text-gray-900">AI 教学助手</span>
              <span className="text-xs text-gray-400 ml-2">(教师版)</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg">
            <Search className="h-5 w-5" />
          </button>
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg relative">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <button 
            onClick={() => navigate('/login')}
            className="flex items-center space-x-2 px-3 py-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <LogIn className="h-4 w-4" />
            <span className="text-sm font-medium">登录</span>
          </button>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
