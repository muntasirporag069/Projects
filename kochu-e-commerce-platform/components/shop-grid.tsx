'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useState } from 'react'

interface Product {
  id: number
  name: string
  category: string
  price: string
  image: string
}

interface ShopGridProps {
  products: Product[]
}

export function ShopGrid({ products }: ShopGridProps) {
  const [selectedCategory, setSelectedCategory] = useState('All')
  const categories = ['All', ...new Set(products.map((product) => product.category))]
  const visibleProducts = selectedCategory === 'All'
    ? products
    : products.filter((product) => product.category === selectedCategory)

  return (
    <section id="shop" className="py-20">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-5xl font-bold text-foreground mb-4 text-center">KOCHU Shop</h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Explore our curated collection of luxury pieces. Each item is crafted with precision and elegance.
        </p>

        {categories.length > 1 && (
          <div className="mb-10 flex flex-wrap justify-center gap-2" aria-label="Filter products by category">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                onClick={() => setSelectedCategory(category)}
                aria-pressed={selectedCategory === category}
                className={`border px-4 py-2 text-sm font-semibold transition ${selectedCategory === category ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-foreground hover:bg-muted'}`}
              >
                {category}
              </button>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {visibleProducts.map((product) => (
            <Link
              key={product.id}
              href={`/product/${product.id}`}
              className="group"
            >
              <div className="relative h-80 overflow-hidden bg-muted">
                <Image
                  src={product.image}
                  alt={product.name}
                  fill
                  className="object-cover group-hover:scale-105 transition duration-300"
                />
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-semibold text-foreground">{product.name}</h3>
                <p className="text-sm text-muted-foreground mb-2">{product.category}</p>
                <p className="text-xl font-bold text-accent">${product.price}</p>
              </div>
            </Link>
          ))}
        </div>
        {visibleProducts.length === 0 && <p className="text-center text-muted-foreground">No products in this category yet.</p>}
      </div>
    </section>
  )
}
