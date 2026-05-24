import React, { useEffect, useRef } from 'react'

const ParticleStream = () => {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animationId
    let particles = []

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    class Particle {
      constructor() {
        this.reset()
      }

      reset() {
        this.x = Math.random() * canvas.width
        this.y = Math.random() * canvas.height
        this.size = Math.random() * 2 + 0.5
        this.speedX = (Math.random() - 0.5) * 0.5
        this.speedY = (Math.random() - 0.5) * 0.3
        this.opacity = Math.random() * 0.5 + 0.1
        this.life = Math.random() * 200 + 100
        this.maxLife = this.life
        this.hue = Math.random() > 0.5 ? 220 : 280
      }

      update() {
        this.x += this.speedX
        this.y += this.speedY
        this.life--
        if (this.life <= 0 || this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) {
          this.reset()
        }
      }

      draw() {
        const lifeRatio = this.life / this.maxLife
        const alpha = this.opacity * lifeRatio
        ctx.beginPath()
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
        ctx.fillStyle = `hsla(${this.hue}, 80%, 75%, ${alpha})`
        ctx.fill()
      }
    }

    class Stream {
      constructor(startX, startY, endX, endY, color1, color2) {
        this.startX = startX
        this.startY = startY
        this.endX = endX
        this.endY = endY
        this.color1 = color1
        this.color2 = color2
        this.points = []
        this.offset = Math.random() * 100
        this.generatePoints()
      }

      generatePoints() {
        const segments = 50
        for (let i = 0; i <= segments; i++) {
          const t = i / segments
          const baseX = this.startX + (this.endX - this.startX) * t
          const baseY = this.startY + (this.endY - this.startY) * t
          const wave = Math.sin(t * Math.PI * 3 + this.offset) * 60
          const wave2 = Math.cos(t * Math.PI * 2 + this.offset * 0.7) * 30
          this.points.push({
            x: baseX + wave,
            y: baseY + wave2,
            t
          })
        }
      }

      draw(time) {
        if (this.points.length < 2) return

        const gradient = ctx.createLinearGradient(
          this.startX, this.startY, this.endX, this.endY
        )
        gradient.addColorStop(0, this.color1)
        gradient.addColorStop(1, this.color2)

        ctx.beginPath()
        ctx.moveTo(this.points[0].x, this.points[0].y)

        for (let i = 1; i < this.points.length - 1; i++) {
          const xc = (this.points[i].x + this.points[i + 1].x) / 2
          const yc = (this.points[i].y + this.points[i + 1].y) / 2
          ctx.quadraticCurveTo(this.points[i].x, this.points[i].y, xc, yc)
        }

        ctx.strokeStyle = gradient
        ctx.lineWidth = 2
        ctx.globalAlpha = 0.3 + Math.sin(time * 0.001 + this.offset) * 0.15
        ctx.stroke()
        ctx.globalAlpha = 1

        this.points.forEach((point, i) => {
          const wave = Math.sin(time * 0.002 + i * 0.1 + this.offset) * 2
          const px = point.x + wave
          const py = point.y + Math.cos(time * 0.0015 + i * 0.15) * 1.5
          const size = 1.5 + Math.sin(time * 0.003 + i * 0.2) * 0.5
          const alpha = 0.4 + Math.sin(time * 0.002 + i * 0.1) * 0.3

          ctx.beginPath()
          ctx.arc(px, py, size, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`
          ctx.fill()
        })
      }
    }

    for (let i = 0; i < 150; i++) {
      particles.push(new Particle())
    }

    const streams = [
      new Stream(0, canvas.height * 0.3, canvas.width, canvas.height * 0.2, 'rgba(100, 180, 255, 0.4)', 'rgba(200, 100, 255, 0.2)'),
      new Stream(canvas.width, canvas.height * 0.7, 0, canvas.height * 0.8, 'rgba(200, 100, 255, 0.4)', 'rgba(100, 180, 255, 0.2)'),
      new Stream(0, canvas.height * 0.5, canvas.width, canvas.height * 0.5, 'rgba(150, 130, 255, 0.3)', 'rgba(100, 200, 255, 0.15)'),
      new Stream(canvas.width * 0.2, 0, canvas.width * 0.8, canvas.height, 'rgba(180, 120, 255, 0.25)', 'rgba(100, 150, 255, 0.15)'),
      new Stream(canvas.width * 0.8, 0, canvas.width * 0.2, canvas.height, 'rgba(100, 200, 255, 0.25)', 'rgba(200, 100, 255, 0.15)'),
    ]

    const animate = (time) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      particles.forEach(p => {
        p.update()
        p.draw()
      })

      streams.forEach(s => s.draw(time))

      animationId = requestAnimationFrame(animate)
    }

    animate(0)

    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ pointerEvents: 'none' }}
    />
  )
}

export default ParticleStream
