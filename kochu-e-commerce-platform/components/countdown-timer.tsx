'use client'

import { useEffect, useState } from 'react'

interface CountdownTimerProps {
  dropTime: string
  title: string
}

export function CountdownTimer({ dropTime, title }: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  })
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    setIsLoaded(true)
    const interval = setInterval(() => {
      const now = new Date().getTime()
      const target = new Date(dropTime).getTime()
      const distance = target - now

      if (distance < 0) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0 })
        clearInterval(interval)
      } else {
        setTimeLeft({
          days: Math.floor(distance / (1000 * 60 * 60 * 24)),
          hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
          minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
          seconds: Math.floor((distance % (1000 * 60)) / 1000),
        })
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [dropTime])

  if (!isLoaded) return null

  return (
    <div className="bg-primary text-primary-foreground py-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h2 className="text-4xl font-bold mb-6">{title}</h2>
        <div className="flex justify-center gap-8 md:gap-12">
          <div className="flex flex-col items-center">
            <div className="text-5xl md:text-6xl font-bold">{String(timeLeft.days).padStart(2, '0')}</div>
            <div className="text-sm uppercase tracking-widest mt-2">Days</div>
          </div>
          <div className="flex flex-col items-center">
            <div className="text-5xl md:text-6xl font-bold">{String(timeLeft.hours).padStart(2, '0')}</div>
            <div className="text-sm uppercase tracking-widest mt-2">Hours</div>
          </div>
          <div className="flex flex-col items-center">
            <div className="text-5xl md:text-6xl font-bold">{String(timeLeft.minutes).padStart(2, '0')}</div>
            <div className="text-sm uppercase tracking-widest mt-2">Minutes</div>
          </div>
          <div className="flex flex-col items-center">
            <div className="text-5xl md:text-6xl font-bold">{String(timeLeft.seconds).padStart(2, '0')}</div>
            <div className="text-sm uppercase tracking-widest mt-2">Seconds</div>
          </div>
        </div>
      </div>
    </div>
  )
}
