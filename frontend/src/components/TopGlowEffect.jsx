import React from 'react'

const TopGlowEffect = () => {
  return (
    <div className="absolute top-0 left-0 right-0 h-96 overflow-hidden pointer-events-none">
      {/* 动态渐变光带 - 延伸到导航栏区域 */}
      <div className="absolute top-0 left-0 right-0 h-48 bg-gradient-to-b from-blue-500/15 via-purple-500/8 to-transparent animate-glow-sweep"></div>
      
      {/* 导航栏区域的背景光效 */}
      <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-white/5 via-white/3 to-transparent"></div>
      
      {/* 漂浮光点 - 更多光点 */}
      <div className="absolute top-8 left-1/4 w-2 h-2 bg-blue-400/60 rounded-full animate-float-particle"></div>
      <div className="absolute top-16 left-1/3 w-1.5 h-1.5 bg-purple-400/60 rounded-full animate-float-particle" style={{ animationDelay: '1s' }}></div>
      <div className="absolute top-12 right-1/4 w-2 h-2 bg-pink-400/60 rounded-full animate-float-particle" style={{ animationDelay: '2s' }}></div>
      <div className="absolute top-20 right-1/3 w-1.5 h-1.5 bg-cyan-400/60 rounded-full animate-float-particle" style={{ animationDelay: '1.5s' }}></div>
      <div className="absolute top-24 left-1/2 w-1.5 h-1.5 bg-blue-300/60 rounded-full animate-float-particle" style={{ animationDelay: '0.5s' }}></div>
      <div className="absolute top-28 left-1/5 w-1 h-1 bg-purple-300/60 rounded-full animate-float-particle" style={{ animationDelay: '2.5s' }}></div>
      
      {/* 横向光晕 - 多条 */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent animate-shimmer-horizontal"></div>
      <div className="absolute top-8 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent animate-shimmer-horizontal" style={{ animationDelay: '0.5s' }}></div>
      <div className="absolute top-16 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer-horizontal" style={{ animationDelay: '1s' }}></div>
      
      {/* 顶部大光晕层 */}
      <div className="absolute -top-32 left-1/2 transform -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-blue-500/8 via-purple-500/5 to-transparent rounded-full blur-3xl animate-pulse-slow"></div>
      
      {/* 侧边光晕 */}
      <div className="absolute -top-20 -left-40 w-96 h-96 bg-gradient-to-br from-blue-500/5 to-purple-500/5 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      <div className="absolute -top-20 -right-40 w-96 h-96 bg-gradient-to-bl from-pink-500/5 to-cyan-500/5 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
    </div>
  )
}

export default TopGlowEffect
