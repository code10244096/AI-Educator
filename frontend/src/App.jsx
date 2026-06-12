import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import HomeworkGrader from './pages/HomeworkGrader'
import LessonPlanGenerator from './pages/LessonPlanGenerator'
import ClassData from './pages/ClassData'
import QuestionBank from './pages/QuestionBank'
import MyTasks from './pages/MyTasks'
import TaskDetail from './pages/TaskDetail'
import Settings from './pages/Settings'
import WelcomePage from './pages/WelcomePage'
import LoginPage from './pages/LoginPage'
import { TaskProvider } from './context/TaskContext'
import { LayoutProvider } from './context/LayoutContext'
import { ClassProvider } from './context/ClassContext'
import { ToastProvider } from './components/Toast'


function App() {
  return (
    <LayoutProvider>
      <ClassProvider>
        <TaskProvider>
          <ToastProvider>
            <BrowserRouter>
              <Routes>
                {/* 登录页面 - 全屏展示 */}
                <Route path="/login" element={<LoginPage />} />
                
                {/* 主应用布局 */}
                <Route path="*" element={
                  <div className="min-h-screen bg-gray-50">
                    <Navbar />
                    <Sidebar />
                    <main className="pt-16 min-h-screen">
                      <Routes>
                        <Route path="/" element={<WelcomePage />} />
                        <Route path="/grader" element={<HomeworkGrader />} />
                        <Route path="/lessonplan" element={<LessonPlanGenerator />} />
                        <Route path="/class/*" element={<ClassData />} />
                        <Route path="/questionbank/*" element={<QuestionBank />} />
                        <Route path="/tasks" element={<MyTasks />} />
                        <Route path="/tasks/:taskId" element={<TaskDetail />} />
                        <Route path="/settings" element={<Settings />} />
                      </Routes>
                    </main>
                  </div>
                } />
              </Routes>
            </BrowserRouter>
        </ToastProvider>
        </TaskProvider>
      </ClassProvider>
    </LayoutProvider>
  )
}

export default App
