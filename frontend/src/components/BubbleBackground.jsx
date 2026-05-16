import React, { useEffect, useState } from 'react'

const BubbleBackground = () => {
  const [bubbles, setBubbles] = useState([])

  useEffect(() => {
    // 生成初始泡泡
    const initialBubbles = Array.from({ length: 20 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 5,
      duration: 8 + Math.random() * 7,
      size: 10 + Math.random() * 40,
    }))
    setBubbles(initialBubbles)

    // 定期生成新泡泡
    const interval = setInterval(() => {
      setBubbles(prev => {
        const newBubble = {
          id: Date.now(),
          left: Math.random() * 100,
          delay: 0,
          duration: 8 + Math.random() * 7,
          size: 10 + Math.random() * 40,
        }
        return [...prev.slice(-19), newBubble] // 保持最多 20 个泡泡
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {bubbles.map((bubble) => (
        <div
          key={bubble.id}
          className="absolute rounded-full bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/10"
          style={{
            left: `${bubble.left}%`,
            bottom: '-100px',
            width: `${bubble.size}px`,
            height: `${bubble.size}px`,
            animation: `floatUp ${bubble.duration}s ease-in ${bubble.delay}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes floatUp {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 0;
          }
          10% {
            opacity: 0.6;
          }
          90% {
            opacity: 0.6;
          }
          100% {
            transform: translateY(-120vh) rotate(360deg);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  )
}

export default BubbleBackground
