'use client'

import { useCart } from '@/components/cart-provider'

export function AddToCartButton({ productId }: { productId: number }) {
  const { add } = useCart()
  return <button type="button" onClick={() => add(productId)} className="flex-1 bg-primary px-6 py-4 font-semibold text-primary-foreground transition hover:opacity-90">Add to Cart</button>
}
