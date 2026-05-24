import React from 'react'

const AnimatedBook = () => {
  return (
    <div className="relative">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-48 h-48 rounded-full bg-white/10 animate-pulse" />
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-36 h-36 rounded-full bg-white/5 animate-pulse" style={{ animationDelay: '0.5s' }} />
      </div>
      <div className="relative animate-float">
        <svg width="180" height="140" viewBox="0 0 180 140" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="bookGrad" x1="0" y1="0" x2="180" y2="140">
              <stop offset="0%" stopColor="rgba(255,255,255,0.98)" />
              <stop offset="100%" stopColor="rgba(210,225,255,0.9)" />
            </linearGradient>
            <linearGradient id="pageGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="rgba(255,255,255,0.75)" />
              <stop offset="100%" stopColor="rgba(225,235,255,0.55)" />
            </linearGradient>
            <linearGradient id="flipGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="rgba(190,215,255,0.7)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0.85)" />
            </linearGradient>
            <linearGradient id="shadowGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(0,0,0,0)" />
              <stop offset="100%" stopColor="rgba(0,0,0,0.1)" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="5" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="shadow">
              <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="rgba(0,0,0,0.15)" />
            </filter>
          </defs>
          
          <g filter="url(#glow)">
            <path d="M90 30 L90 120" stroke="rgba(255,255,255,0.5)" strokeWidth="2" />
            
            <path d="M20 38 Q55 22 90 30 L90 120 Q55 112 20 120 Z" fill="url(#bookGrad)" opacity="0.95" filter="url(#shadow)">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M20 38 Q55 22 90 30 L90 120 Q55 112 20 120 Z;
                        M20 38 Q55 28 90 30 L90 120 Q55 108 20 120 Z;
                        M20 38 Q55 22 90 30 L90 120 Q55 112 20 120 Z" />
            </path>
            
            <path d="M160 38 Q125 22 90 30 L90 120 Q125 112 160 120 Z" fill="url(#bookGrad)" opacity="0.95" filter="url(#shadow)">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M160 38 Q125 22 90 30 L90 120 Q125 112 160 120 Z;
                        M160 38 Q125 28 90 30 L90 120 Q125 108 160 120 Z;
                        M160 38 Q125 22 90 30 L90 120 Q125 112 160 120 Z" />
            </path>
            
            <path d="M28 44 Q55 34 88 40 L88 114 Q55 108 28 114 Z" fill="url(#pageGrad)" opacity="0.6">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M28 44 Q55 34 88 40 L88 114 Q55 108 28 114 Z;
                        M28 44 Q55 38 88 40 L88 114 Q55 106 28 114 Z;
                        M28 44 Q55 34 88 40 L88 114 Q55 108 28 114 Z" />
            </path>
            
            <path d="M152 44 Q125 34 92 40 L92 114 Q125 108 152 114 Z" fill="url(#pageGrad)" opacity="0.6">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M152 44 Q125 34 92 40 L92 114 Q125 108 152 114 Z;
                        M152 44 Q125 38 92 40 L92 114 Q125 106 152 114 Z;
                        M152 44 Q125 34 92 40 L92 114 Q125 108 152 114 Z" />
            </path>
            
            <path d="M34 50 Q55 42 86 48 L86 108 Q55 102 34 108 Z" fill="url(#pageGrad)" opacity="0.5">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M34 50 Q55 42 86 48 L86 108 Q55 102 34 108 Z;
                        M34 50 Q55 46 86 48 L86 108 Q55 100 34 108 Z;
                        M34 50 Q55 42 86 48 L86 108 Q55 102 34 108 Z" />
            </path>
            
            <path d="M146 50 Q125 42 94 48 L94 108 Q125 102 146 108 Z" fill="url(#pageGrad)" opacity="0.5">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M146 50 Q125 42 94 48 L94 108 Q125 102 146 108 Z;
                        M146 50 Q125 46 94 48 L94 108 Q125 100 146 108 Z;
                        M146 50 Q125 42 94 48 L94 108 Q125 102 146 108 Z" />
            </path>
            
            <path d="M40 56 Q55 50 86 56 L86 102 Q55 96 40 102 Z" fill="url(#pageGrad)" opacity="0.4">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M40 56 Q55 50 86 56 L86 102 Q55 96 40 102 Z;
                        M40 56 Q55 54 86 56 L86 102 Q55 94 40 102 Z;
                        M40 56 Q55 50 86 56 L86 102 Q55 96 40 102 Z" />
            </path>
            
            <path d="M140 56 Q125 50 94 56 L94 102 Q125 96 140 102 Z" fill="url(#pageGrad)" opacity="0.4">
              <animate attributeName="d" dur="5s" repeatCount="indefinite"
                values="M140 56 Q125 50 94 56 L94 102 Q125 96 140 102 Z;
                        M140 56 Q125 54 94 56 L94 102 Q125 94 140 102 Z;
                        M140 56 Q125 50 94 56 L94 102 Q125 96 140 102 Z" />
            </path>
            
            <line x1="36" y1="56" x2="72" y2="52" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="72;68;72" />
            </line>
            <line x1="36" y1="68" x2="76" y2="64" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="76;72;76" />
            </line>
            <line x1="36" y1="80" x2="70" y2="76" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="70;66;70" />
            </line>
            <line x1="36" y1="92" x2="74" y2="88" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="74;70;74" />
            </line>
            
            <line x1="108" y1="52" x2="144" y2="56" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="144;140;144" />
            </line>
            <line x1="104" y1="64" x2="144" y2="68" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="144;140;144" />
            </line>
            <line x1="110" y1="76" x2="144" y2="80" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="144;140;144" />
            </line>
            <line x1="106" y1="88" x2="144" y2="92" stroke="rgba(110,150,255,0.45)" strokeWidth="2.5" strokeLinecap="round">
              <animate attributeName="x2" dur="5s" repeatCount="indefinite" values="144;140;144" />
            </line>
            
            <g>
              <animateTransform attributeName="transform" type="rotate" dur="3s" repeatCount="indefinite"
                values="0 90 75; -10 90 75; 0 90 75; 10 90 75; 0 90 75" />
              
              <path d="M90 34 Q110 24 130 34 L130 116 Q110 108 90 116 Z" fill="url(#flipGrad)" opacity="0">
                <animate attributeName="opacity" dur="3s" repeatCount="indefinite"
                  values="0; 0; 0.85; 0.85; 0; 0"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="d" dur="3s" repeatCount="indefinite"
                  values="M90 34 Q110 24 130 34 L130 116 Q110 108 90 116 Z;
                          M90 34 Q110 24 130 34 L130 116 Q110 108 90 116 Z;
                          M90 34 Q98 18 90 34 L90 116 Q98 110 90 116 Z;
                          M90 34 Q70 24 50 34 L50 116 Q70 108 90 116 Z;
                          M90 34 Q70 24 50 34 L50 116 Q70 108 90 116 Z;
                          M90 34 Q110 24 130 34 L130 116 Q110 108 90 116 Z"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
              </path>
              
              <line x1="96" y1="52" x2="122" y2="56" stroke="rgba(110,150,255,0.35)" strokeWidth="2" strokeLinecap="round" opacity="0">
                <animate attributeName="opacity" dur="3s" repeatCount="indefinite"
                  values="0; 0; 0.6; 0.6; 0; 0"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="x1" dur="3s" repeatCount="indefinite"
                  values="96; 96; 90; 78; 78; 96"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="x2" dur="3s" repeatCount="indefinite"
                  values="122; 122; 90; 70; 70; 122"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
              </line>
              <line x1="94" y1="66" x2="124" y2="70" stroke="rgba(110,150,255,0.35)" strokeWidth="2" strokeLinecap="round" opacity="0">
                <animate attributeName="opacity" dur="3s" repeatCount="indefinite"
                  values="0; 0; 0.6; 0.6; 0; 0"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="x1" dur="3s" repeatCount="indefinite"
                  values="94; 94; 90; 76; 76; 94"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="x2" dur="3s" repeatCount="indefinite"
                  values="124; 124; 90; 68; 68; 124"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
              </line>
              <line x1="98" y1="80" x2="122" y2="84" stroke="rgba(110,150,255,0.35)" strokeWidth="2" strokeLinecap="round" opacity="0">
                <animate attributeName="opacity" dur="3s" repeatCount="indefinite"
                  values="0; 0; 0.6; 0.6; 0; 0"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="x1" dur="3s" repeatCount="indefinite"
                  values="98; 98; 90; 74; 74; 98"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
                <animate attributeName="x2" dur="3s" repeatCount="indefinite"
                  values="122; 122; 90; 66; 66; 122"
                  keyTimes="0; 0.3; 0.4; 0.7; 0.8; 1" />
              </line>
            </g>
          </g>
        </svg>
      </div>
      
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-15px); }
        }
        .animate-float {
          animation: float 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}

export default AnimatedBook
