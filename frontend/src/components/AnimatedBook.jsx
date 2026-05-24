import React from 'react'

const AnimatedBook = () => {
  return (
    <div className="relative">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-32 h-32 rounded-full bg-white/10 animate-ping" style={{ animationDuration: '3s' }} />
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-24 h-24 rounded-full bg-white/10 animate-ping" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
      </div>
      <div className="relative animate-float">
        <svg width="120" height="100" viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="bookGrad" x1="0" y1="0" x2="120" y2="100">
              <stop offset="0%" stopColor="rgba(255,255,255,0.95)" />
              <stop offset="100%" stopColor="rgba(200,220,255,0.9)" />
            </linearGradient>
            <linearGradient id="pageGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="rgba(255,255,255,0.8)" />
              <stop offset="100%" stopColor="rgba(220,230,255,0.6)" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          
          <g filter="url(#glow)">
            <path d="M60 20 L60 85" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
            
            <path d="M15 25 Q37.5 15 60 20 L60 85 Q37.5 80 15 85 Z" fill="url(#bookGrad)" opacity="0.9">
              <animate attributeName="d" dur="4s" repeatCount="indefinite"
                values="M15 25 Q37.5 15 60 20 L60 85 Q37.5 80 15 85 Z;
                        M15 25 Q37.5 18 60 20 L60 85 Q37.5 78 15 85 Z;
                        M15 25 Q37.5 15 60 20 L60 85 Q37.5 80 15 85 Z" />
            </path>
            
            <path d="M105 25 Q82.5 15 60 20 L60 85 Q82.5 80 105 85 Z" fill="url(#bookGrad)" opacity="0.9">
              <animate attributeName="d" dur="4s" repeatCount="indefinite"
                values="M105 25 Q82.5 15 60 20 L60 85 Q82.5 80 105 85 Z;
                        M105 25 Q82.5 18 60 20 L60 85 Q82.5 78 105 85 Z;
                        M105 25 Q82.5 15 60 20 L60 85 Q82.5 80 105 85 Z" />
            </path>
            
            <path d="M20 30 Q37.5 22 58 25 L58 80 Q37.5 77 20 80 Z" fill="url(#pageGrad)" opacity="0.6">
              <animate attributeName="d" dur="4s" repeatCount="indefinite"
                values="M20 30 Q37.5 22 58 25 L58 80 Q37.5 77 20 80 Z;
                        M20 30 Q37.5 25 58 25 L58 80 Q37.5 75 20 80 Z;
                        M20 30 Q37.5 22 58 25 L58 80 Q37.5 77 20 80 Z" />
            </path>
            
            <path d="M100 30 Q82.5 22 62 25 L62 80 Q82.5 77 100 80 Z" fill="url(#pageGrad)" opacity="0.6">
              <animate attributeName="d" dur="4s" repeatCount="indefinite"
                values="M100 30 Q82.5 22 62 25 L62 80 Q82.5 77 100 80 Z;
                        M100 30 Q82.5 25 62 25 L62 80 Q82.5 75 100 80 Z;
                        M100 30 Q82.5 22 62 25 L62 80 Q82.5 77 100 80 Z" />
            </path>
            
            <line x1="30" y1="40" x2="50" y2="38" stroke="rgba(100,150,255,0.3)" strokeWidth="1.5" strokeLinecap="round">
              <animate attributeName="x2" dur="4s" repeatCount="indefinite" values="50;48;50" />
            </line>
            <line x1="30" y1="50" x2="52" y2="48" stroke="rgba(100,150,255,0.3)" strokeWidth="1.5" strokeLinecap="round">
              <animate attributeName="x2" dur="4s" repeatCount="indefinite" values="52;50;52" />
            </line>
            <line x1="30" y1="60" x2="48" y2="58" stroke="rgba(100,150,255,0.3)" strokeWidth="1.5" strokeLinecap="round">
              <animate attributeName="x2" dur="4s" repeatCount="indefinite" values="48;46;48" />
            </line>
            
            <line x1="70" y1="38" x2="90" y2="40" stroke="rgba(100,150,255,0.3)" strokeWidth="1.5" strokeLinecap="round">
              <animate attributeName="x2" dur="4s" repeatCount="indefinite" values="90;88;90" />
            </line>
            <line x1="68" y1="48" x2="90" y2="50" stroke="rgba(100,150,255,0.3)" strokeWidth="1.5" strokeLinecap="round">
              <animate attributeName="x2" dur="4s" repeatCount="indefinite" values="90;88;90" />
            </line>
            <line x1="72" y1="58" x2="90" y2="60" stroke="rgba(100,150,255,0.3)" strokeWidth="1.5" strokeLinecap="round">
              <animate attributeName="x2" dur="4s" repeatCount="indefinite" values="90;88;90" />
            </line>
          </g>
        </svg>
      </div>
      
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
        .animate-float {
          animation: float 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}

export default AnimatedBook
