import React from 'react'
import AnimatedBook from '../components/AnimatedBook'

const WelcomePage = () => {
  return (
    <div className="min-h-screen relative overflow-hidden" style={{
      background: 'linear-gradient(135deg, #4a6cf7 0%, #7c3aed 30%, #a855f7 60%, #6366f1 100%)'
    }}>
      
      <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="strongGlow">
            <feGaussianBlur stdDeviation="10" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <linearGradient id="beadGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9"/>
            <stop offset="50%" stopColor="#ff8fab" stopOpacity="0.8"/>
            <stop offset="100%" stopColor="#d061ff" stopOpacity="0.6"/>
          </linearGradient>
          <linearGradient id="beadGradient2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9"/>
            <stop offset="50%" stopColor="#7c3aed" stopOpacity="0.8"/>
            <stop offset="100%" stopColor="#4c1d95" stopOpacity="0.6"/>
          </linearGradient>
        </defs>
        
        {[0, 1, 2, 3, 4, 5].map((row, i) => {
          const y = 80 + row * 90;
          return (
            <g key={`left-row-${i}`}>
              {[0, 1, 2, 3, 4, 5, 6].map((bead, j) => {
                const x = j * 90 + 30;
                return (
                  <g key={`bead-l-${i}-${j}`}>
                    <circle 
                      cx={x} 
                      cy={y} 
                      r={6}
                      fill="url(#beadGradient)"
                      filter="url(#strongGlow)">
                      <animate 
                        attributeName="opacity" 
                        dur={1.5 + Math.random() * 2} 
                        repeatCount="indefinite" 
                        values="0.4;1;0.4" 
                        begin={`${j * 0.15}s`}/>
                      <animate 
                        attributeName="r" 
                        dur={2 + Math.random() * 2} 
                        repeatCount="indefinite" 
                        values="4;8;4" 
                        begin={`${j * 0.15}s`}/>
                    </circle>
                  </g>
                );
              })}
            </g>
          );
        })}
        
        {[0, 1, 2, 3, 4, 5].map((row, i) => {
          const y = 80 + row * 90;
          return (
            <g key={`right-row-${i}`}>
              {[0, 1, 2, 3, 4, 5, 6].map((bead, j) => {
                const x = window.innerWidth ? window.innerWidth - j * 90 - 30 : 1200 - j * 90 - 30;
                return (
                  <g key={`bead-r-${i}-${j}`}>
                    <circle 
                      cx={x} 
                      cy={y} 
                      r={6}
                      fill="url(#beadGradient2)"
                      filter="url(#strongGlow)">
                      <animate 
                        attributeName="opacity" 
                        dur={1.5 + Math.random() * 2} 
                        repeatCount="indefinite" 
                        values="0.4;1;0.4" 
                        begin={`${j * 0.15}s`}/>
                      <animate 
                        attributeName="r" 
                        dur={2 + Math.random() * 2} 
                        repeatCount="indefinite" 
                        values="4;8;4" 
                        begin={`${j * 0.15}s`}/>
                    </circle>
                  </g>
                );
              })}
            </g>
          );
        })}
        
        {[...Array(8)].map((_, i) => (
          <g key={`curve-${i}`}>
            <path 
              d={`M${-50 + i * 180} ${120 + (i % 3) * 150} Q${50 + i * 180} ${80 + (i % 3) * 150} ${150 + i * 180} ${120 + (i % 3) * 150}`}
              fill="none" 
              stroke="rgba(255,255,255,0.4)" 
              strokeWidth="3" 
              strokeDasharray="15 20">
              <animate attributeName="stroke-dashoffset" dur="4s" repeatCount="indefinite" values="0; -140" begin={`${i * 0.3}s`}/>
            </path>
          </g>
        ))}
        
        {[...Array(30)].map((_, i) => (
          <circle 
            key={`particle-${i}`}
            cx={Math.random() * 1200} 
            cy={Math.random() * 800} 
            r={Math.random() * 5 + 3}
            fill="rgba(255,255,255,0.9)"
            filter="url(#strongGlow)">
            <animate 
              attributeName="opacity" 
              dur={Math.random() * 1.5 + 1} 
              repeatCount="indefinite" 
              values="0.2;1;0.2" 
            />
            <animate 
              attributeName="r" 
              dur={Math.random() * 1.5 + 1} 
              repeatCount="indefinite" 
              values="3;7;3" 
            />
            <animate 
              attributeName="cy" 
              dur={Math.random() * 3 + 2} 
              repeatCount="indefinite" 
              values={`${Math.random() * 800};${Math.random() * 800}`} 
            />
          </circle>
        ))}
      </svg>
      
      <div className="relative z-10 flex flex-col items-center justify-start min-h-screen px-4 pt-8 pb-12">
        <div className="my-4">
          <AnimatedBook />
        </div>
        
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3 tracking-wide">
          AI+教育让学习与教育变得更美好
        </h1>
        
        <p className="text-base text-white/80 mb-4 font-medium">
          教师版 · 让教学更智能
        </p>
        
        <div className="text-center max-w-lg mb-8">
          <p className="text-sm text-white/50 leading-relaxed">
            基于人工智能的教学辅助平台，提供作业批改、教案生成、班级管理、题库管理等
          </p>
          <p className="text-sm text-white/50 leading-relaxed">
            一站式教学服务
          </p>
        </div>
      </div>
    </div>
  )
}

export default WelcomePage
