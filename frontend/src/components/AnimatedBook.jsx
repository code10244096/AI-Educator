import React from 'react'

const AnimatedBook = () => {
  return (
    <div className="relative" style={{ perspective: '2500px' }}>
      <div className="relative animate-float" style={{ transformStyle: 'preserve-3d' }}>
        <svg width="500" height="400" viewBox="0 0 500 400" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="coverLeft" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#ff2d55" />
              <stop offset="30%" stopColor="#ff8fab" />
              <stop offset="70%" stopColor="#d061ff" />
              <stop offset="100%" stopColor="#7c3aed" />
            </linearGradient>
            <linearGradient id="coverRight" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#4c1d95" />
              <stop offset="30%" stopColor="#7c3aed" />
              <stop offset="70%" stopColor="#d061ff" />
              <stop offset="100%" stopColor="#e879f9" />
            </linearGradient>
            <linearGradient id="spine" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#2d1b4e" />
              <stop offset="50%" stopColor="#7c3aed" />
              <stop offset="100%" stopColor="#2d1b4e" />
            </linearGradient>
            <linearGradient id="edge" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ff4d6d" />
              <stop offset="50%" stopColor="#d061ff" />
              <stop offset="100%" stopColor="#ff4d6d" />
            </linearGradient>
            <linearGradient id="pageGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#f0f4ff" />
            </linearGradient>
            <filter id="shadow">
              <feDropShadow dx="0" dy="25" stdDeviation="20" floodColor="rgba(0,0,0,0.35)" />
            </filter>
            <filter id="glow">
              <feGaussianBlur stdDeviation="10" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          
          <g filter="url(#shadow)">
            <path d="M40 40 L40 360 L10 375 L10 25 Z" fill="url(#edge)" opacity="0.9" />
            <path d="M32 43 L32 357 L18 367 L18 32 Z" fill="url(#spine)" opacity="0.7" />
            
            <path d="M50 35 Q150 5 250 30 L250 355 Q150 340 50 370 Z" fill="url(#coverLeft)" filter="url(#glow)" />
            
            <path d="M460 40 L460 360 L490 375 L490 25 Z" fill="url(#edge)" opacity="0.85" />
            <path d="M468 43 L468 357 L482 367 L482 32 Z" fill="url(#spine)" opacity="0.65" />
            
            <path d="M450 35 Q350 5 250 30 L250 355 Q350 340 450 370 Z" fill="url(#coverRight)" filter="url(#glow)" />
            
            <rect x="242" y="30" width="18" height="330" fill="url(#spine)" rx="4" />
            
            <path d="M80 48 Q160 28 245 45 L245 345 Q160 328 80 358 Z" fill="url(#pageGrad)" opacity="0.95" />
            <path d="M105 58 Q175 43 242 55 L242 340 Q175 323 105 353 Z" fill="url(#pageGrad)" opacity="0.85" />
            <path d="M130 70 Q185 55 240 65 L240 335 Q185 318 130 348 Z" fill="url(#pageGrad)" opacity="0.7" />
            
            <path d="M420 48 Q340 28 255 45 L255 345 Q340 328 420 358 Z" fill="url(#pageGrad)" opacity="0.95" />
            <path d="M395 58 Q325 43 258 55 L258 340 Q325 323 395 353 Z" fill="url(#pageGrad)" opacity="0.85" />
            <path d="M370 70 Q315 55 260 65 L260 335 Q315 318 370 348 Z" fill="url(#pageGrad)" opacity="0.7" />
            
            <g opacity="0.7">
              <line x1="120" y1="90" x2="210" y2="88" stroke="#ff6b6b" strokeWidth="4" />
              <line x1="120" y1="130" x2="220" y2="128" stroke="#ff8fab" strokeWidth="4" />
              <line x1="120" y1="170" x2="200" y2="168" stroke="#d061ff" strokeWidth="4" />
              <line x1="120" y1="210" x2="215" y2="208" stroke="#7c3aed" strokeWidth="4" />
              <line x1="120" y1="250" x2="195" y2="248" stroke="#ff8fab" strokeWidth="4" />
              <line x1="120" y1="290" x2="210" y2="288" stroke="#ff6b6b" strokeWidth="4" />
            </g>
            
            <g opacity="0.7">
              <line x1="290" y1="88" x2="380" y2="90" stroke="#7c3aed" strokeWidth="4" />
              <line x1="280" y1="128" x2="380" y2="130" stroke="#d061ff" strokeWidth="4" />
              <line x1="300" y1="168" x2="380" y2="170" stroke="#ff8fab" strokeWidth="4" />
              <line x1="285" y1="208" x2="380" y2="210" stroke="#ff8fab" strokeWidth="4" />
              <line x1="305" y1="248" x2="380" y2="250" stroke="#d061ff" strokeWidth="4" />
              <line x1="290" y1="288" x2="380" y2="290" stroke="#7c3aed" strokeWidth="4" />
            </g>
            
            <g>
              <path 
                d="M255 30 Q350 12 445 32 L445 365 Q350 348 255 360 Z" 
                fill="#ffffff" 
                opacity="0"
              >
                <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                  values="0;0.9;1;1;1;0.9;0"
                  keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                <animate attributeName="d" dur="2.5s" repeatCount="indefinite"
                  values="M255 30 Q350 12 445 32 L445 365 Q350 348 255 360 Z;
                          M255 30 Q350 12 445 32 L445 365 Q350 348 255 360 Z;
                          M255 30 Q270 8 255 30 L255 360 Q270 352 255 360 Z;
                          M255 30 Q180 10 85 30 L85 365 Q180 348 255 360 Z;
                          M255 30 Q180 10 85 30 L85 365 Q180 348 255 360 Z;
                          M255 30 Q180 10 85 30 L85 365 Q180 348 255 360 Z;
                          M255 30 Q180 10 85 30 L85 365 Q180 348 255 360 Z"
                  keyTimes="0;0.15;0.3;0.45;0.6;0.8;1" />
              </path>
              
              <g>
                <line x1="280" y1="90" x2="420" y2="88" stroke="#ff6b6b" strokeWidth="4">
                  <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                    values="0;0.7;0.7;0.7;0.7;0.7;0"
                    keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                </line>
                <line x1="270" y1="130" x2="420" y2="132" stroke="#ff8fab" strokeWidth="4">
                  <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                    values="0;0.7;0.7;0.7;0.7;0.7;0"
                    keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                </line>
                <line x1="285" y1="170" x2="420" y2="168" stroke="#d061ff" strokeWidth="4">
                  <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                    values="0;0.7;0.7;0.7;0.7;0.7;0"
                    keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                </line>
                <line x1="275" y1="210" x2="420" y2="212" stroke="#7c3aed" strokeWidth="4">
                  <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                    values="0;0.7;0.7;0.7;0.7;0.7;0"
                    keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                </line>
                <line x1="280" y1="250" x2="420" y2="248" stroke="#ff8fab" strokeWidth="4">
                  <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                    values="0;0.7;0.7;0.7;0.7;0.7;0"
                    keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                </line>
                <line x1="275" y1="290" x2="420" y2="292" stroke="#ff6b6b" strokeWidth="4">
                  <animate attributeName="opacity" dur="2.5s" repeatCount="indefinite"
                    values="0;0.7;0.7;0.7;0.7;0.7;0"
                    keyTimes="0;0.2;0.35;0.5;0.65;0.8;1" />
                </line>
              </g>
            </g>
            
            <ellipse cx="250" cy="35" rx="180" ry="18" fill="rgba(255,255,255,0.35)" />
          </g>
        </svg>
      </div>
      
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotateY(0deg); }
          25% { transform: translateY(-20px) rotateY(3deg); }
          50% { transform: translateY(-8px) rotateY(0deg); }
          75% { transform: translateY(-20px) rotateY(-3deg); }
        }
        .animate-float {
          animation: float 6s ease-in-out infinite;
          transform-style: preserve-3d;
        }
      `}</style>
    </div>
  )
}

export default AnimatedBook
