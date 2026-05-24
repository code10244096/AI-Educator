import React, { useState, useEffect } from 'react'
import {
  Clock,
  CheckCircle,
  AlertCircle,
  FileCheck,
  FileText,
  Users,
  Bell,
  Eye,
  Trash2,
  Search,
  Loader2,
  XCircle
} from 'lucide-react'
import { useTask } from '../context/TaskContext'
import { useClass } from '../context/ClassContext'
import { useToast } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

const MyTasks = () => {
  const { tasks, updateTask, removeTask, clearCompleted } = useTask()
  const { classes } = useClass()
  const { addToast } = useToast()
  const [activeTab, setActiveTab] = useState('pending')
  const [searchTerm, setSearchTerm] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteTargetId, setDeleteTargetId] = useState(null)

  const getTypeIcon = (type) => {
    switch (type) {
      case 'grader': return <FileCheck className="h-4 w-4" />
      case 'lessonplan': return <FileText className="h-4 w-4" />
      case 'alert': return <Bell className="h-4 w-4" />
      case 'exam': return <Users className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  const getTypeLabel = (type) => {
    switch (type) {
      case 'grader': return '作业批改'
      case 'lessonplan': return '教案生成'
      case 'alert': return '预警提醒'
      case 'exam': return '成绩管理'
      default: return '其他'
    }
  }

  const getTypeColor = (type) => {
    switch (type) {
      case 'grader': return 'bg-blue-100 text-blue-700'
      case 'lessonplan': return 'bg-purple-100 text-purple-700'
      case 'alert': return 'bg-red-100 text-red-700'
      case 'exam': return 'bg-green-100 text-green-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high': return <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">紧急</span>
      case 'medium': return <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">重要</span>
      case 'low': return <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">普通</span>
      default: return null
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending': return <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded-full">待处理</span>
      case 'running': return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">进行中</span>
      case 'completed': return <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">已完成</span>
      case 'failed': return <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">失败</span>
      default: return null
    }
  }

  const formatTime = (isoString) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    const now = new Date()
    const diff = now - date
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 7) return `${days}天前`
    return date.toLocaleDateString('zh-CN')
  }

  const filteredTasks = tasks.filter(t => {
    const matchesTab = t.status === activeTab
    const matchesSearch = t.title.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesTab && matchesSearch
  })

  const pendingCount = tasks.filter(t => t.status === 'pending').length
  const runningCount = tasks.filter(t => t.status === 'running').length
  const completedCount = tasks.filter(t => t.status === 'completed').length
  const failedCount = tasks.filter(t => t.status === 'failed').length

  const handleViewTask = (task) => {
    if (task.type === 'grader' && task.result) {
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
      window.location.hash = '/grader'
    } else if (task.type === 'lessonplan' && task.result) {
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
      window.location.hash = '/lessonplan'
    } else {
      addToast('该任务暂无详情可查看', 'info')
    }
  }

  const handleDeleteTask = (id) => {
    setDeleteTargetId(id)
    setShowDeleteConfirm(true)
  }

  const confirmDelete = () => {
    removeTask(deleteTargetId)
    setShowDeleteConfirm(false)
    setDeleteTargetId(null)
    addToast('任务已删除', 'success')
  }

  const handleClearCompleted = () => {
    if (completedCount === 0) {
      addToast('没有已完成的任务', 'info')
      return
    }
    clearCompleted()
    addToast(`已清除 ${completedCount} 个已完成任务`, 'success')
  }

  const tabs = [
    { id: 'running', label: '进行中', count: runningCount, icon: Loader2 },
    { id: 'pending', label: '待处理', count: pendingCount, icon: Clock },
    { id: 'completed', label: '已完成', count: completedCount, icon: CheckCircle },
    { id: 'failed', label: '失败', count: failedCount, icon: XCircle },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">我的任务</h2>
          <p className="text-sm text-gray-500 mt-1">管理待办事项与任务进度</p>
        </div>
        {completedCount > 0 && (
          <button
            onClick={handleClearCompleted}
            className="inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            <span>清除已完成</span>
          </button>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex space-x-1 bg-gray-100 rounded-xl p-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className={`h-4 w-4 ${tab.id === 'running' && activeTab === 'running' ? 'animate-spin' : ''}`} />
                <span>{tab.label}</span>
                <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                  activeTab === tab.id ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-500'
                }`}>
                  {tab.count}
                </span>
              </button>
            )
          })}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索任务..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      <div className="space-y-3">
        {filteredTasks.map((task) => (
          <div key={task.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div className={`p-2.5 rounded-xl ${getTypeColor(task.type)}`}>
                  {getTypeIcon(task.type)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1 flex-wrap gap-y-1">
                    <h4 className="text-sm font-medium text-gray-900">{task.title}</h4>
                    {task.priority && getPriorityBadge(task.priority)}
                    {getStatusBadge(task.status)}
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-500 flex-wrap gap-y-1">
                    <span className={`px-2 py-0.5 rounded-full ${getTypeColor(task.type)}`}>
                      {getTypeLabel(task.type)}
                    </span>
                    <span>{formatTime(task.createdAt)}</span>
                    {task.files && <span>{task.files.length} 个文件</span>}
                    {task.error && <span className="text-red-500">{task.error}</span>}
                  </div>
                  {task.status === 'running' && task.progress !== undefined && (
                    <div className="mt-3 w-64">
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <span>{task.progressLabel || '处理中'}</span>
                        <span>{task.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {(task.status === 'completed' || task.status === 'running') && (
                  <button
                    onClick={() => handleViewTask(task)}
                    className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors"
                    title="查看详情"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={() => handleDeleteTask(task.id)}
                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors"
                  title="删除任务"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {filteredTasks.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-gray-300" />
            </div>
            <p className="text-gray-500 font-medium">暂无任务</p>
            <p className="text-sm text-gray-400 mt-1">
              {activeTab === 'running' && '当前没有进行中的任务'}
              {activeTab === 'pending' && '去作业批改或教案生成页面创建任务吧'}
              {activeTab === 'completed' && '还没有已完成的任务'}
              {activeTab === 'failed' && '没有失败的任务'}
            </p>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="删除任务"
        message="确定要删除这个任务吗？删除后无法恢复。"
        onConfirm={confirmDelete}
        onCancel={() => { setShowDeleteConfirm(false); setDeleteTargetId(null) }}
        confirmText="确认删除"
        cancelText="再想想"
      />
    </div>
  )
}

export default MyTasks
