'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { Navbar } from '@/components/navbar'
import { useCart } from '@/components/cart-provider'
import { getAllProducts } from '@/app/actions/product'

type Product = { id: number; name: string; price: string; image: string | null; stock: number | null }

export default function CartPage() {
  const { items, setQuantity, remove } = useCart()
  const [products, setProducts] = useState<Product[]>([])
  useEffect(() => { getAllProducts().then((result) => setProducts(result as Product[])) }, [])

  const cartItems = items.map((item) => ({ ...item, product: products.find((product) => product.id === item.id) })).filter((item) => item.product)
  const subtotal = cartItems.reduce((sum, item) => sum + Number(item.product!.price) * item.quantity, 0)

  return (
    <main className="min-h-screen bg-background"><Navbar /><section className="px-4 pb-20 pt-32"><div className="mx-auto max-w-6xl"><h1 className="mb-12 text-4xl font-bold text-foreground">Shopping Cart</h1>
      {items.length === 0 ? <div className="border border-border bg-card p-12 text-center"><p className="mb-8 text-muted-foreground">Your cart is empty</p><Link href="/#shop" className="inline-block bg-primary px-6 py-3 font-semibold text-primary-foreground">Continue Shopping</Link></div> : <div className="grid grid-cols-1 gap-8 lg:grid-cols-3"><div className="space-y-4 lg:col-span-2">{cartItems.map(({ id, quantity, product }) => <div key={id} className="flex items-center gap-4 border border-border bg-card p-4"><div className="relative h-24 w-20 shrink-0 bg-muted"><Image src={product!.image || '/placeholder.png'} alt={product!.name} fill className="object-cover" /></div><div className="min-w-0 flex-1"><Link href={`/product/${id}`} className="font-semibold text-foreground hover:text-accent">{product!.name}</Link><p className="text-accent">${Number(product!.price).toFixed(2)}</p></div><input type="number" min="1" max={Math.max(1, product!.stock || 1)} value={quantity} onChange={(event) => setQuantity(id, Number.parseInt(event.target.value, 10) || 1)} className="w-20 border border-border bg-background px-2 py-2" aria-label={`Quantity for ${product!.name}`} /><p className="w-24 text-right font-semibold">${(Number(product!.price) * quantity).toFixed(2)}</p><button type="button" onClick={() => remove(id)} className="text-sm font-semibold text-red-600 hover:underline">Remove</button></div>)}</div><aside className="h-fit border border-border bg-card p-8"><h2 className="mb-6 text-2xl font-bold">Order Summary</h2><div className="mb-6 flex justify-between border-b border-border pb-6"><span className="text-muted-foreground">Subtotal</span><span className="font-semibold">${subtotal.toFixed(2)}</span></div><div className="mb-8 flex justify-between"><span className="text-lg font-bold">Total</span><span className="text-2xl font-bold text-accent">${subtotal.toFixed(2)}</span></div><Link href="/checkout" className="block w-full bg-primary px-6 py-3 text-center font-semibold text-primary-foreground">Proceed to Checkout</Link></aside></div>}
      {items.length > 0 && cartItems.length === 0 && <p className="mt-4 text-sm text-red-600">Some products are no longer available.</p>}</div></section></main>
  )
}
