import React from 'react'
import ParticleStream from '../components/ParticleStream'
import AnimatedBook from '../components/AnimatedBook'

const WelcomePage = () => {
  return (
    <div className="min-h-screen relative overflow-hidden" style={{
      background: 'linear-gradient(135deg, #4a6cf7 0%, #7c3aed 30%, #a855f7 60%, #6366f1 100%)'
    }}>
      <ParticleStream />
      
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="mb-8">
          <AnimatedBook />
        </div>
        
        <div className="inline-flex items-center justify-center w-14 h-14 bg-white/15 backdrop-blur-sm rounded-xl shadow-lg mb-6 border border-white/20">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
        </div>
        
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3 tracking-wide">
          AI+教育让学习与教育变得更美好
        </h1>
        
        <p className="text-base text-white/80 mb-2 font-medium">
          教师版 · 让教学更智能
        </p>
        
        <p className="text-sm text-white/50 max-w-lg mx-auto leading-relaxed">
          基于人工智能的教学辅助平台，提供作业批改、教案生成、班级管理、题库管理等一站式教学服务
        </p>
      </div>
    </div>
  )
}

export default WelcomePage
