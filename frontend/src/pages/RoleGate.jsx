import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { GraduationCap, Presentation, Backpack, ArrowLeft, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// 进入网页的第一步：选择身份。教师 → 体验登录；学生 → 功能尚未发布提示。
const RoleGate = () => {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const [role, setRole] = useState('') // '' 选择中 | 'student' 学生未发布提示

  useEffect(() => {
    document.title = 'AI 教学助手'
  }, [])

  if (!loading && user) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="min-h-screen overflow-y-auto bg-gray-50 px-4 py-10 sm:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-4xl flex-col items-center justify-center">
        <div className="mb-10 text-center">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 mb-5">
            <GraduationCap className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">AI 教学助手</h1>
          <p className="mt-3 text-sm text-gray-500 sm:text-base">请选择你的身份，开始使用</p>
        </div>

        {role !== 'student' ? (
          <div className="grid w-full gap-5 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => navigate('/login', { replace: true })}
              className="group flex flex-col items-center rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue-50 transition group-hover:bg-blue-100">
                <Presentation className="h-7 w-7 text-blue-600" />
              </div>
              <h2 className="mt-5 text-lg font-semibold text-gray-900">我是教师</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-500">
                作业批改、教案生成、错题本与学情分析
              </p>
              <span className="mt-5 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition group-hover:bg-blue-700">
                <Sparkles className="h-4 w-4" />
                进入体验
              </span>
            </button>

            <button
              type="button"
              onClick={() => setRole('student')}
              className="group flex flex-col items-center rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-50 transition group-hover:bg-emerald-100">
                <Backpack className="h-7 w-7 text-emerald-600" />
              </div>
              <h2 className="mt-5 text-lg font-semibold text-gray-900">我是学生</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-500">
                个性化练习与自主学习的专属空间
              </p>
              <span className="mt-5 inline-flex items-center rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition group-hover:border-emerald-300 group-hover:text-emerald-700">
                了解一下
              </span>
            </button>
          </div>
        ) : (
          <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-50">
              <Backpack className="h-7 w-7 text-emerald-600" />
            </div>
            <h2 className="mt-5 text-lg font-semibold text-gray-900">学生版即将上线</h2>
            <p className="mt-3 text-sm leading-relaxed text-gray-500">
              学生端功能尚未发布，正在加紧打磨中，敬请期待。当前版本仅面向教师开放体验。
            </p>
            <button
              type="button"
              onClick={() => setRole('')}
              className="mt-6 inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
            >
              <ArrowLeft className="h-4 w-4" />
              返回重新选择
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default RoleGate
