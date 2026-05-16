import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BookOpen, FileText, ClipboardCheck, User, GraduationCap, X } from 'lucide-react'

const Navbar = ({ transparent = false }) => {
  const navigate = useNavigate()
  const location = useLocation()
  
  const menuItems = [
    { path: '/', label: '首页', icon: GraduationCap, color: 'text-blue-500' },
    { path: '/grader', label: '作业批改', icon: ClipboardCheck, color: 'text-blue-500' },
    { path: '/notebook', label: '错题本', icon: BookOpen, color: 'text-green-500' },
    { path: '/lessonplan', label: '教案生成', icon: FileText, color: 'text-purple-500' },
  ]
  
  const handleNavClick = (path) => {
    navigate(path)
  }
  
  // 首页使用透明导航栏
  const isHomePage = location.pathname === '/'
  const navbarTransparent = transparent || isHomePage
  
  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      navbarTransparent 
        ? 'bg-transparent backdrop-blur-none' 
        : 'bg-white/90 backdrop-blur-xl shadow-lg border-b border-white/20'
    }`}>
      {/* 导航栏背景动态效果（仅非首页显示） */}
      {!navbarTransparent && (
        <>
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-pink-500/5 pointer-events-none"></div>
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"></div>
        </>
      )}
      
      {/* 顶部渐变条（仅非首页显示） */}
      {!navbarTransparent && (
        <div className="h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>
      )}
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          {/* Logo 区域（仅非首页显示） */}
          {!navbarTransparent && (
            <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => navigate('/')}>
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full blur-md opacity-70 group-hover:opacity-100 transition-opacity animate-pulse"></div>
                <div className="relative bg-gradient-to-br from-blue-500 to-purple-600 rounded-full p-2.5 shadow-lg transform group-hover:scale-110 transition-transform">
                  <GraduationCap className="h-7 w-7 text-white" />
                </div>
              </div>
              <div>
                <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  AI 教学助手
                </span>
                <p className="text-xs text-gray-500 -mt-1">智能教育伙伴</p>
              </div>
            </div>
          )}
          
          {/* 导航菜单 - 右上角 */}
          <div className={`${!navbarTransparent ? 'ml-auto' : 'ml-auto'} flex items-center space-x-2`}>
            {menuItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              return (
                <button
                    key={item.path + item.label}
                    onClick={() => handleNavClick(item.path)}
                    className={`inline-flex items-center px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 hover:scale-105 ${
                      navbarTransparent
                        ? 'text-white hover:bg-white/10'
                        : isActive
                          ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg'
                          : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className={`h-4 w-4 mr-2 transition-transform duration-300 hover:scale-110 ${
                      navbarTransparent 
                        ? 'text-white' 
                        : isActive 
                          ? 'text-white' 
                          : item.color
                    }`} />
                    {item.label}
                  </button>
              )
            })}
            
            {/* 登录按钮 */}
            <button className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg ${
              navbarTransparent
                ? 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-sm'
                : 'bg-gradient-to-r from-blue-50 to-purple-50 hover:from-blue-100 hover:to-purple-100 text-gray-700'
            }`}>
              <User className="h-4 w-4 transition-transform duration-300 hover:scale-110" />
              <span className="text-sm font-medium">登录</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
