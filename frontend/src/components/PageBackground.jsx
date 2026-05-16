import React from 'react'

const PageBackground = ({ children, gradient = 'default' }) => {
  const gradients = {
    default: 'from-blue-50 via-purple-50 to-pink-50',
    grader: 'from-blue-50 via-blue-100 to-cyan-50',
    notebook: 'from-green-50 via-emerald-50 to-teal-50',
    lessonplan: 'from-purple-50 via-pink-50 to-rose-50',
  }

  return (
    <div className={`min-h-screen bg-gradient-to-br ${gradients[gradient]} relative`}>
      {/* 背景装饰图案 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* 左上角圆形装饰 */}
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
        
        {/* 右下角圆形装饰 */}
        <div className="absolute -bottom-40 -right-40 w-80 h-80 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse" style={{ animationDelay: '1s' }}></div>
        
        {/* 中间圆形装饰 */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>
        
        {/* 网格图案 */}
        <div 
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #666 1px, transparent 0)`,
            backgroundSize: '40px 40px'
          }}
        ></div>
      </div>

      {/* 内容区域 */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  )
}

export default PageBackground
