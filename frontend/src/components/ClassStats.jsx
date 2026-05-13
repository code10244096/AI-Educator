import React from 'react'
import { Users, TrendingDown, FileText } from 'lucide-react'

const ClassStats = ({ stats }) => {
  if (!stats) return null
  
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-bold mb-4">班级统计</h3>
      
      <div className="space-y-4">
        <div className="flex items-center">
          <Users className="h-5 w-5 text-primary-600 mr-3" />
          <div>
            <p className="text-sm text-gray-600">总人数</p>
            <p className="text-xl font-bold">{stats.total_students}</p>
          </div>
        </div>
        
        <div className="flex items-center">
          <TrendingDown className="h-5 w-5 text-red-600 mr-3" />
          <div>
            <p className="text-sm text-gray-600">平均错题数</p>
            <p className="text-xl font-bold">{stats.average_wrong_count}</p>
          </div>
        </div>
        
        <div>
          <p className="text-sm text-gray-600 mb-2">高频错题</p>
          <div className="space-y-2">
            {stats.common_wrong_questions.map((q, idx) => (
              <div key={idx} className="flex items-start">
                <span className="text-red-600 font-medium mr-2">{idx + 1}.</span>
                <span className="text-sm text-gray-700">{q.question}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClassStats
