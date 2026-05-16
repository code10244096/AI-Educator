import { useState, useEffect } from 'react'

const PageTransition = ({ children, onNavigate }) => {
  const [isExiting, setIsExiting] = useState(false)
  const [isEntering, setIsEntering] = useState(true)

  useEffect(() => {
    // 进入动画
    const enterTimer = setTimeout(() => {
      setIsEntering(false)
    }, 500)

    return () => clearTimeout(enterTimer)
  }, [])

  const handleClick = (path) => {
    setIsExiting(true)
    
    // 等待退出动画完成后再导航
    setTimeout(() => {
      onNavigate(path)
    }, 400)
  }

  // 克隆子元素并注入 handleClick
  const childrenWithProps = React.Children.map(children, child => {
    if (child.type === 'div' || child.type === 'main' || child.type === 'section') {
      return React.cloneElement(child, {
        className: `${child.props.className || ''} page-transition-container ${isExiting ? 'page-exit' : ''} ${isEntering ? 'page-enter' : ''}`.trim(),
        style: {
          ...child.props.style,
          opacity: isExiting ? 0 : isEntering ? 0 : 1,
          transform: isExiting ? 'scale(0.95)' : isEntering ? 'scale(0.98)' : 'scale(1)',
          transition: 'opacity 0.4s ease, transform 0.4s ease'
        }
      })
    }
    return child
  })

  return (
    <>
      <style>{`
        .page-transition-container {
          will-change: opacity, transform;
        }
        
        .page-enter {
          animation: pageEnter 0.8s ease-out forwards;
        }
        
        .page-exit {
          animation: pageExit 0.6s ease-in forwards;
        }
        
        @keyframes pageEnter {
          from {
            opacity: 0;
            transform: scale(0.95) translateY(20px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        
        @keyframes pageExit {
          from {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
          to {
            opacity: 0;
            transform: scale(0.97) translateY(-20px);
          }
        }
        
        .click-ripple {
          position: absolute;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.6);
          transform: scale(0);
          animation: rippleEffect 0.8s ease-out;
          pointer-events: none;
        }
        
        @keyframes rippleEffect {
          to {
            transform: scale(4);
            opacity: 0;
          }
        }
      `}</style>
      {childrenWithProps}
    </>
  )
}

export default PageTransition
