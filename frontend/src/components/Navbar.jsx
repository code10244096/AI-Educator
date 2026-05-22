import React, { useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BookOpen, FileText, ClipboardCheck, User, GraduationCap, X, FileCheck, Bell, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useTask } from '../context/TaskContext'

const TaskCard = ({ task, onRemove, onView }) => {
  const statusColors = {
    running: 'border-blue-200 bg-blue-50',
    completed: 'border-green-200 bg-green-50',
    failed: 'border-red-200 bg-red-50',
  }
  
  const statusIcons = {
    running: <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />,
    completed: <CheckCircle2 className="h-3 w-3 text-green-500" />,
    failed: <AlertCircle className="h-3 w-3 text-red-500" />,
  }
  
  return (
    <div
      className={`p-2 rounded-lg border cursor-pointer hover:shadow-sm transition-all ${statusColors[task.status] || 'border-gray-200 bg-gray-50'}`}
      onClick={() => onView(task)}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center space-x-1">
          {statusIcons[task.status]}
          <span className="text-xs font-medium text-gray-700 truncate max-w-[100px]">{task.title}</span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onRemove(task.id)
          }}
          className="p-0.5 hover:bg-white/50 rounded"
        >
          <X className="h-3 w-3 text-gray-400" />
        </button>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-500 truncate max-w-[80px]">{task.progressLabel || ''}</span>
        <span className={`text-[10px] font-medium ${
          task.status === 'running' ? 'text-blue-600' :
          task.status === 'completed' ? 'text-green-600' : 'text-red-600'
        }`}>
          {task.status === 'running' ? `${task.progress || 0}%` :
           task.status === 'completed' ? '完成' : '失败'}
        </span>
      </div>
      {task.status === 'running' && task.progress !== undefined && (
        <div className="mt-1">
          <div className="w-full bg-gray-200 rounded-full h-1 overflow-hidden">
            <div
              className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full rounded-full transition-all duration-300 ease-out"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

const Navbar = ({ transparent = false }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { tasks, taskBarExpanded, setTaskBarExpanded, removeTask, updateTask } = useTask()
  const taskBarRef = useRef(null)
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (taskBarRef.current && !taskBarRef.current.contains(event.target)) {
        setTaskBarExpanded(false)
      }
    }
    
    if (taskBarExpanded) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [taskBarExpanded, setTaskBarExpanded])
  
  const menuItems = [
    { path: '/', label: '首页', icon: GraduationCap, color: 'text-blue-500' },
    { path: '/grader', label: '作业批改', icon: ClipboardCheck, color: 'text-blue-500' },
    { path: '/notebook', label: '错题本', icon: BookOpen, color: 'text-green-500' },
    { path: '/lessonplan', label: '教案生成', icon: FileText, color: 'text-purple-500' },
    { path: '/questionbank', label: '题库管理', icon: BookOpen, color: 'text-orange-500' },
  ]
  
  const handleNavClick = (path) => {
    navigate(path)
  }
  
  const handleViewTask = (task) => {
    if (task.type === 'lessonplan' && task.status === 'completed') {
      navigate('/lessonplan')
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
    } else if (task.type === 'grader' && task.status === 'completed') {
      navigate('/grader')
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
    } else if (task.type === 'notebook' && task.status === 'completed') {
      navigate('/notebook')
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
    }
  }
  
  const runningCount = tasks.filter(t => t.status === 'running').length
  const completedCount = tasks.filter(t => t.status === 'completed').length
  const totalCount = runningCount + completedCount
  
  const isHomePage = location.pathname === '/'
  const navbarTransparent = transparent || isHomePage
  
  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      navbarTransparent 
        ? 'bg-transparent backdrop-blur-none' 
        : 'bg-white/90 backdrop-blur-xl shadow-lg border-b border-white/20'
    }`}>
      {!navbarTransparent && (
        <>
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-pink-500/5 pointer-events-none"></div>
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"></div>
        </>
      )}
      
      {!navbarTransparent && (
        <div className="h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>
      )}
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
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
            
            <div className="relative" ref={taskBarRef}>
              <button
                onClick={() => setTaskBarExpanded(!taskBarExpanded)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg ${
                  navbarTransparent
                    ? 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-sm'
                    : 'bg-gradient-to-r from-blue-50 to-purple-50 hover:from-blue-100 hover:to-purple-100 text-gray-700'
                }`}
              >
                <FileCheck className="h-4 w-4 transition-transform duration-300 hover:scale-110" />
                <span className="text-sm font-medium">我的任务</span>
                {totalCount > 0 && (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    runningCount > 0 ? 'bg-blue-500 text-white animate-pulse' : 'bg-green-500 text-white'
                  }`}>
                    {totalCount}
                  </span>
                )}
              </button>
              
              {taskBarExpanded && (
                <div className="absolute right-0 top-full mt-2 w-[480px] bg-white/95 backdrop-blur-md rounded-xl shadow-xl border border-gray-200 overflow-hidden">
                  <div className="p-3 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-gray-700">任务中心</h3>
                      <span className="text-xs text-gray-500">{tasks.length} 个任务</span>
                    </div>
                  </div>
                  
                  <div className="max-h-[480px] overflow-y-auto">
                    {tasks.length === 0 ? (
                      <div className="p-8 text-center text-gray-500 text-sm">
                        暂无任务
                      </div>
                    ) : (
                      <div className="grid grid-cols-3 divide-x divide-gray-100">
                        {/* 批改作业 */}
                        <div className="p-3">
                          <div className="flex items-center space-x-1.5 mb-2">
                            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                            <span className="text-xs font-semibold text-gray-600">作业批改</span>
                          </div>
                          <div className="space-y-2">
                            {tasks.filter(t => t.type === 'grader').length === 0 ? (
                              <p className="text-xs text-gray-400 text-center py-2">暂无任务</p>
                            ) : (
                              tasks.filter(t => t.type === 'grader').map((task) => (
                                <TaskCard key={task.id} task={task} onRemove={removeTask} onView={handleViewTask} />
                              ))
                            )}
                          </div>
                        </div>
                        
                        {/* 整理错题 */}
                        <div className="p-3">
                          <div className="flex items-center space-x-1.5 mb-2">
                            <div className="w-2 h-2 rounded-full bg-green-500"></div>
                            <span className="text-xs font-semibold text-gray-600">错题整理</span>
                          </div>
                          <div className="space-y-2">
                            {tasks.filter(t => t.type === 'notebook').length === 0 ? (
                              <p className="text-xs text-gray-400 text-center py-2">暂无任务</p>
                            ) : (
                              tasks.filter(t => t.type === 'notebook').map((task) => (
                                <TaskCard key={task.id} task={task} onRemove={removeTask} onView={handleViewTask} />
                              ))
                            )}
                          </div>
                        </div>
                        
                        {/* 教案生成 */}
                        <div className="p-3">
                          <div className="flex items-center space-x-1.5 mb-2">
                            <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                            <span className="text-xs font-semibold text-gray-600">教案生成</span>
                          </div>
                          <div className="space-y-2">
                            {tasks.filter(t => t.type === 'lessonplan').length === 0 ? (
                              <p className="text-xs text-gray-400 text-center py-2">暂无任务</p>
                            ) : (
                              tasks.filter(t => t.type === 'lessonplan').map((task) => (
                                <TaskCard key={task.id} task={task} onRemove={removeTask} onView={handleViewTask} />
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            
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
