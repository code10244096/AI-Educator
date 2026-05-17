import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import HomeworkGrader from './pages/HomeworkGrader'
import WrongNotebook from './pages/WrongNotebook'
import LessonPlanGenerator from './pages/LessonPlanGenerator'
import QuestionBank from './pages/QuestionBank'
import { TaskProvider } from './context/TaskContext'

function App() {
  return (
    <TaskProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-100">
          <Navbar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/grader" element={<HomeworkGrader />} />
            <Route path="/notebook" element={<WrongNotebook />} />
            <Route path="/lessonplan" element={<LessonPlanGenerator />} />
            <Route path="/questionbank" element={<QuestionBank />} />
          </Routes>
        </div>
      </BrowserRouter>
    </TaskProvider>
  )
}

export default App
