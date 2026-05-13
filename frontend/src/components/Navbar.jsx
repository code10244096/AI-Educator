import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BookOpen, FileText, ClipboardCheck, User } from 'lucide-react'

const Navbar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  
  const menuItems = [
    { path: '/', label: '作业批改', icon: ClipboardCheck },
    { path: '/notebook', label: '错题本', icon: BookOpen },
    { path: '/lessonplan', label: '教案生成', icon: FileText },
  ]
  
  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <BookOpen className="h-8 w-8 text-primary-600" />
              <span className="ml-2 text-xl font-bold text-gray-800">
                AI 教学助手
              </span>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {menuItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path
                return (
                  <button
                    key={item.path}
                    onClick={() => navigate(item.path)}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      isActive
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.label}
                  </button>
                )
              })}
            </div>
          </div>
          <div className="flex items-center">
            <button className="flex items-center text-gray-600 hover:text-gray-900">
              <User className="h-5 w-5 mr-2" />
              <span>登录</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
