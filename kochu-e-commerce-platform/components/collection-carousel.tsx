'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Collection {
  id: number
  title: string
  season: string
  coverImage: string
  description: string
}

interface CollectionCarouselProps {
  collections: Collection[]
}

export function CollectionCarousel({ collections }: CollectionCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0)

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev === 0 ? collections.length - 1 : prev - 1))
  }

  const handleNext = () => {
    setCurrentIndex((prev) => (prev === collections.length - 1 ? 0 : prev + 1))
  }

  if (collections.length === 0) return null

  const current = collections[currentIndex]

  return (
    <section id="collections" className="pt-32 pb-20">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-5xl font-bold text-foreground mb-12 text-center">Seasonal Collections</h2>
        
        <div className="relative">
          {/* Main carousel */}
          <div className="relative h-96 md:h-[500px] overflow-hidden">
            <Link href={`/collection/${current.id}`}>
              <div className="relative h-full cursor-pointer group">
                <Image
                  src={current.coverImage}
                  alt={current.title}
                  fill
                  className="object-cover group-hover:scale-105 transition duration-300"
                />
                <div className="absolute inset-0 bg-black/30 group-hover:bg-black/40 transition flex flex-col justify-end p-8">
                  <h3 className="text-4xl font-bold text-white mb-2">{current.title}</h3>
                  <p className="text-white/80">{current.season}</p>
                </div>
              </div>
            </Link>
          </div>

          {/* Navigation buttons */}
          <button
            onClick={handlePrev}
            className="absolute left-4 top-1/2 -translate-y-1/2 z-10 bg-white/10 hover:bg-white/20 text-white p-3 transition"
          >
            <ChevronLeft size={24} />
          </button>
          <button
            onClick={handleNext}
            className="absolute right-4 top-1/2 -translate-y-1/2 z-10 bg-white/10 hover:bg-white/20 text-white p-3 transition"
          >
            <ChevronRight size={24} />
          </button>

          {/* Dots */}
          <div className="flex justify-center gap-2 mt-8">
            {collections.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`h-2 rounded-full transition ${
                  idx === currentIndex ? 'bg-accent w-8' : 'bg-muted w-2'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
