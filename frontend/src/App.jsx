import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import RequireAuth from './components/RequireAuth'
import Workbench from './pages/Workbench'
import HomeworkGrader from './pages/HomeworkGrader'
import LessonPlanGenerator from './pages/LessonPlanGenerator'
import WrongNotebook from './pages/WrongNotebook'
import ClassData from './pages/ClassData'
import TaskDetail from './pages/TaskDetail'
import Settings from './pages/Settings'
import UsageStats from './pages/UsageStats'
import LoginPage from './pages/LoginPage'
import SetPasswordPage from './pages/SetPasswordPage'
import { TaskProvider } from './context/TaskContext'
import { LayoutProvider, useLayout } from './context/LayoutContext'
import { ClassProvider } from './context/ClassContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/Toast'

// 运维页面仅管理员可见；教师直接访问显示“无权限”
const AdminOnly = ({ children }) => {
  const { isAdmin } = useAuth()
  if (isAdmin) return children
  return (
    <div className="max-w-md mx-auto mt-24 text-center px-4">
      <h2 className="text-lg font-semibold text-gray-900">无权限访问</h2>
      <p className="mt-2 text-sm text-gray-500">该页面仅学校管理员可以查看。</p>
    </div>
  )
}

// 登录后的主布局：顶栏 + 侧栏（桌面常驻 232px / 折叠 64px，窄屏抽屉）+ 内容
const MainLayout = ({ children }) => {
  const { collapsed } = useLayout()
  useEffect(() => {
    document.title = 'AI 教学助手'
  }, [])
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <Sidebar />
      <main className={`pt-16 min-h-screen min-w-0 ${collapsed ? 'lg:pl-16' : 'lg:pl-[232px]'}`}>{children}</main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LayoutProvider>
          <ClassProvider>
            <ToastProvider>
              <TaskProvider>
                <Routes>
                  {/* 登录 / 设置新密码 - 全屏展示 */}
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/set-password" element={<SetPasswordPage />} />

                  {/* 主应用布局：必须登录 */}
                  <Route path="*" element={
                    <RequireAuth>
                      <MainLayout>
                        <Routes>
                          <Route path="/" element={<Workbench />} />
                          <Route path="/grader" element={<HomeworkGrader />} />
                          <Route path="/lessonplan" element={<LessonPlanGenerator />} />
                          <Route path="/notebook" element={<WrongNotebook />} />
                          <Route path="/class/*" element={<ClassData />} />
                          {/* 题库页面已下线（R1-004），旧链接回工作台 */}
                          <Route path="/questionbank/*" element={<Navigate to="/" replace />} />
                          {/* 本地任务列表页取消（R1-006），后台任务改在顶栏任务抽屉 */}
                          <Route path="/tasks" element={<Navigate to="/" replace />} />
                          <Route path="/tasks/:taskId" element={<TaskDetail />} />
                          <Route path="/usage" element={<AdminOnly><UsageStats /></AdminOnly>} />
                          <Route path="/settings" element={<Settings />} />
                        </Routes>
                      </MainLayout>
                    </RequireAuth>
                  } />
                </Routes>
              </TaskProvider>
            </ToastProvider>
          </ClassProvider>
        </LayoutProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
