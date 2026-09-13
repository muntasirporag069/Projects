'use client'

import { useRef, useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/navbar'
import { useCart } from '@/components/cart-provider'
import { createOrder } from '@/app/actions/order'

export default function CheckoutPage() {
  const { items, clear } = useCart()
  const [message, setMessage] = useState('')
  const [pending, startTransition] = useTransition()
  const router = useRouter()
  const idempotencyKey = useRef<string | null>(null)
  const submit = (formData: FormData) => {
    formData.set('items', JSON.stringify(items))
    idempotencyKey.current ??= crypto.randomUUID()
    formData.set('idempotencyKey', idempotencyKey.current)
    startTransition(async () => {
      const result = await createOrder(formData)
      if (result.success) { idempotencyKey.current = null; clear(); router.push(`/cart?order=${result.orderId}`) } else setMessage(result.message || 'Checkout failed.')
    })
  }

  return <main className="min-h-screen bg-background"><Navbar /><section className="px-4 pb-20 pt-32"><div className="mx-auto max-w-xl"><h1 className="mb-8 text-4xl font-bold text-foreground">Checkout</h1>{items.length === 0 ? <p className="text-muted-foreground">Your cart is empty.</p> : <form action={submit} className="grid gap-4 bg-card p-8"><input name="customerName" required placeholder="Full name" className="border border-border bg-background px-4 py-3" /><input name="phone" required type="tel" placeholder="Phone number" className="border border-border bg-background px-4 py-3" /><textarea name="address" required placeholder="Delivery address" rows={4} className="border border-border bg-background px-4 py-3" /><select name="paymentMethod" defaultValue="cod" className="border border-border bg-background px-4 py-3"><option value="cod">Cash on delivery</option><option value="bkash" disabled>bKash unavailable</option><option value="nagad" disabled>Nagad unavailable</option></select>{message && <p className="text-sm text-red-600">{message}</p>}<button disabled={pending} className="bg-primary px-4 py-3 font-semibold text-primary-foreground disabled:opacity-50">{pending ? 'Submitting...' : 'Place order'}</button></form>}</div></section></main>
}