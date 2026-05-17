import React from 'react'
import { Clock, CheckCircle, XCircle, Trash2, FileText } from 'lucide-react'

const TaskBar = ({ tasks, onRemoveTask, onViewTask, expanded, onToggle }) => {
  if (!tasks || tasks.length === 0) return null
  
  const runningCount = tasks.filter(t => t.status === 'running').length
  const completedCount = tasks.filter(t => t.status === 'completed').length
  
  return (
    <div className="fixed top-20 right-4 z-50">
      {/* 展开/收起按钮 */}
      <button
        onClick={onToggle}
        className="flex items-center space-x-2 bg-white/90 backdrop-blur-md px-4 py-2 rounded-full shadow-lg hover:shadow-xl transition-all border border-gray-200"
      >
        <FileText className="h-5 w-5 text-purple-600" />
        <span className="text-sm font-medium text-gray-700">我的任务</span>
        {runningCount > 0 && (
          <span className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full animate-pulse">
            {runningCount}
          </span>
        )}
        {completedCount > 0 && (
          <span className="bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">
            {completedCount}
          </span>
        )}
      </button>
      
      {/* 任务列表 */}
      {expanded && (
        <div className="mt-2 w-80 bg-white/95 backdrop-blur-md rounded-xl shadow-xl border border-gray-200 overflow-hidden">
          <div className="p-3 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">任务列表</h3>
              <span className="text-xs text-gray-500">{tasks.length} 个任务</span>
            </div>
          </div>
          
          <div className="max-h-96 overflow-y-auto">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between p-3 hover:bg-gray-50 transition-all cursor-pointer border-b border-gray-50 last:border-b-0"
                onClick={() => onViewTask(task)}
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  {task.status === 'running' && (
                    <Clock className="h-4 w-4 text-blue-500 animate-spin flex-shrink-0" />
                  )}
                  {task.status === 'completed' && (
                    <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                  )}
                  {task.status === 'failed' && (
                    <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                  )}
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
                    <p className="text-xs text-gray-500">
                      {task.status === 'running' && `已用 ${task.elapsedTime || 0}秒`}
                      {task.status === 'completed' && '已完成'}
                      {task.status === 'failed' && (task.error || '生成失败')}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 ml-2">
                  <span className={`text-xs px-2 py-1 rounded ${
                    task.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    task.status === 'completed' ? 'bg-green-100 text-green-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {task.status === 'running' ? '进行中' :
                     task.status === 'completed' ? '已完成' : '失败'}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onRemoveTask(task.id)
                    }}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    <Trash2 className="h-4 w-4 text-gray-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default TaskBar
