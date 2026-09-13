'use client'

import { createContext, useContext, useEffect, useState } from 'react'

type CartItem = { id: number; quantity: number }
type CartContextValue = { items: CartItem[]; count: number; add: (id: number) => void; setQuantity: (id: number, quantity: number) => void; remove: (id: number) => void; clear: () => void }
const CartContext = createContext<CartContextValue | null>(null)
const storageKey = 'kochu-cart'

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || '[]')
      if (Array.isArray(saved)) setItems(saved.filter((item) => Number.isInteger(item?.id) && Number.isInteger(item?.quantity) && item.quantity > 0))
    } catch { /* Ignore malformed local cart data. */ }
    setReady(true)
  }, [])

  useEffect(() => {
    if (ready) localStorage.setItem(storageKey, JSON.stringify(items))
  }, [items, ready])

  const add = (id: number) => setItems((current) => {
    const existing = current.find((item) => item.id === id)
    return existing ? current.map((item) => item.id === id ? { ...item, quantity: item.quantity + 1 } : item) : [...current, { id, quantity: 1 }]
  })
  const setQuantity = (id: number, quantity: number) => setItems((current) => quantity > 0 ? current.map((item) => item.id === id ? { ...item, quantity: Math.min(quantity, 99) } : item) : current.filter((item) => item.id !== id))
  const remove = (id: number) => setItems((current) => current.filter((item) => item.id !== id))
  const clear = () => setItems([])

  return <CartContext.Provider value={{ items, count: items.reduce((total, item) => total + item.quantity, 0), add, setQuantity, remove, clear }}>{children}</CartContext.Provider>
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) throw new Error('useCart must be used within CartProvider')
  return context
}
