import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, FileText, ClipboardCheck, ArrowRight } from 'lucide-react'
import BubbleBackground from '../components/BubbleBackground'
import TopGlowEffect from '../components/TopGlowEffect'

const Home = () => {
  const navigate = useNavigate()
  const [ripples, setRipples] = useState([])
  const featuresRef = useRef(null)
  const [hasAutoNavigated, setHasAutoNavigated] = useState(false)
  
  const features = [
    {
      title: 'AI 作业批改',
      description: '拍照上传，智能批改，实时反馈',
      icon: ClipboardCheck,
      color: 'from-blue-500 to-cyan-500',
      path: '/grader',
      gradient: 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20'
    },
    {
      title: 'AI 错题本',
      description: '智能整理，变式练习，举一反三',
      icon: BookOpen,
      color: 'from-green-500 to-emerald-500',
      path: '/notebook',
      gradient: 'bg-gradient-to-br from-green-500/20 to-emerald-500/20'
    },
    {
      title: 'AI 教案生成',
      description: '一键生成，个性化定制，省时省力',
      icon: FileText,
      color: 'from-purple-500 to-pink-500',
      path: '/lessonplan',
      gradient: 'bg-gradient-to-br from-purple-500/20 to-pink-500/20'
    }
  ]

  // 滚动监听，自动跳转到 AI 作业批改
  useEffect(() => {
    const handleScroll = () => {
      if (hasAutoNavigated) return
      
      const featuresElement = featuresRef.current
      if (!featuresElement) return
      
      const rect = featuresElement.getBoundingClientRect()
      const viewportHeight = window.innerHeight
      
      // 当功能卡片区域滚动到视口中间位置时触发
      if (rect.top < viewportHeight / 2 && rect.bottom > viewportHeight / 2) {
        setHasAutoNavigated(true)
        // 延迟 800ms 后跳转，让用户看到卡片
        setTimeout(() => {
          navigate('/grader')
        }, 800)
      }
    }
    
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [navigate, hasAutoNavigated])

  const handleCardClick = (path, event) => {
    // 创建点击波纹效果
    const button = event.currentTarget
    const rect = button.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    const ripple = {
      id: Date.now(),
      x,
      y,
    }
    
    setRipples(prev => [...prev, ripple])
    
    // 清理波纹
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== ripple.id))
    }, 600)
    
    // 延迟导航，让动画先播放
    setTimeout(() => {
      navigate(path)
    }, 400)
  }

  return (
    <div className="relative min-h-screen">
      {/* 视频背景 */}
      <div className="absolute inset-0 w-full h-full overflow-hidden">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="absolute min-w-full min-h-full object-cover"
          style={{
            filter: 'brightness(0.4)',
          }}
        >
          {/* 使用免费的教育相关视频素材 */}
          <source 
            src="https://videos.pexels.com/video-files/3205914/3205914-uhd_2560_1440_25fps.mp4" 
            type="video/mp4" 
          />
          您的浏览器不支持视频标签
        </video>
        {/* 渐变遮罩 */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/80"></div>
      </div>

      {/* 动态泡泡背景 */}
      <BubbleBackground />
      
      {/* 顶部光效 */}
      <TopGlowEffect />

      {/* 内容区域 - 添加上边距补偿 fixed 导航栏 */}
      <div className="relative z-10 pt-20">
        {/* 主标题区域 - 优化布局，减少空白 */}
        <div className="flex flex-col items-center justify-center pb-12 px-4">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-4 text-center tracking-tight animate-fade-in-down">
            你的可能
            <span className="block mt-2 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              给未来更多可能
            </span>
          </h1>
          <p className="text-lg md:text-xl text-gray-200 text-center max-w-2xl mx-auto mb-6 animate-fade-in-up">
            受益一生的能力，从 AI 教学助手开始
          </p>
          
          {/* 播放按钮（装饰性） */}
          <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border-2 border-white/30 hover:scale-110 transition-transform cursor-pointer group animate-bounce-slow">
            <div className="w-0 h-0 border-t-8 border-t-transparent border-l-12 border-l-white border-b-8 border-b-transparent ml-1 group-hover:scale-110 transition-transform"></div>
          </div>
        </div>

        {/* 功能卡片 - 优化布局，消除空白 */}
        <div ref={featuresRef} id="features" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <div
                  key={index}
                  onClick={(e) => handleCardClick(feature.path, e)}
                  className={`${feature.gradient} backdrop-blur-md rounded-2xl p-6 border border-white/10 hover:border-white/30 transition-all duration-500 cursor-pointer group hover:scale-105 hover:shadow-2xl transform hover:-translate-y-2 relative overflow-hidden`}
                  style={{
                    animationDelay: `${index * 0.15}s`,
                  }}
                >
                  {/* 点击波纹 */}
                  {ripples.map((ripple) => (
                    <div
                      key={ripple.id}
                      className="click-ripple"
                      style={{
                        left: ripple.x,
                        top: ripple.y,
                        width: '100px',
                        height: '100px',
                        marginLeft: '-50px',
                        marginTop: '-50px',
                      }}
                    />
                  ))}
                  
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-all duration-500 shadow-lg group-hover:shadow-xl group-hover:rotate-3`}>
                    <Icon className="h-7 w-7 text-white" />
                  </div>
                  
                  <h3 className="text-xl font-bold text-white mb-2 group-hover:text-blue-200 transition-colors duration-300 group-hover:translate-x-2">
                    {feature.title}
                  </h3>
                  
                  <p className="text-sm text-gray-300 mb-4 leading-relaxed group-hover:translate-x-2 transition-transform duration-300">
                    {feature.description}
                  </p>
                  
                  <div className="flex items-center text-white/80 group-hover:text-white transition-colors duration-300 group-hover:translate-x-2">
                    <span className="text-sm font-medium">立即体验</span>
                    <ArrowRight className="h-4 w-4 ml-2 group-hover:translate-x-4 transition-all duration-300" />
                  </div>
                </div>
              )
            })}
          </div>
          
          {/* 底部滚动提示 - 简化样式 */}
          <div className="flex justify-center mt-12">
            <div className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-full bg-white/10 backdrop-blur-md border border-white/20 animate-bounce-slow">
              <span className="text-white/80 text-xs font-medium">向下滚动探索更多</span>
              <div className="flex flex-col items-center space-y-0.5">
                <div className="w-1 h-2 bg-white/60 rounded-full animate-pulse"></div>
                <div className="w-1 h-2 bg-white/40 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-1 h-2 bg-white/30 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
