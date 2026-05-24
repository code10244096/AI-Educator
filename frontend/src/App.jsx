import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import HomeworkGrader from './pages/HomeworkGrader'
import LessonPlanGenerator from './pages/LessonPlanGenerator'
import ClassData from './pages/ClassData'
import QuestionBank from './pages/QuestionBank'
import MyTasks from './pages/MyTasks'
import Settings from './pages/Settings'
import WelcomePage from './pages/WelcomePage'
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
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
        </ToastProvider>
        </TaskProvider>
      </ClassProvider>
    </LayoutProvider>
  )
}

export default App
