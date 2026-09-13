'use server'

import { headers } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { auth } from '@/lib/auth'
import { databaseConfigured, pool } from '@/lib/db'

const allowedPaymentMethods = new Set(['cod'])

export async function createOrder(formData: FormData) {
  if (!databaseConfigured || !auth) return { success: false, message: 'Checkout is currently unavailable.' }
  const session = await auth.api.getSession({ headers: await headers() })
  if (!session?.user) return { success: false, message: 'Please sign in before checkout.' }

  const name = String(formData.get('customerName') || '').trim()
  const phone = String(formData.get('phone') || '').trim()
  const address = String(formData.get('address') || '').trim()
  const paymentMethod = String(formData.get('paymentMethod') || '')
  const idempotencyKey = String(formData.get('idempotencyKey') || '').trim()
  if (!name || !phone || !address || !idempotencyKey) return { success: false, message: 'Complete all delivery fields.' }
  if (!allowedPaymentMethods.has(paymentMethod)) return { success: false, message: 'This payment method is not available yet.' }

  let requestedItems: Array<{ id: number; quantity: number }>
  try { requestedItems = JSON.parse(String(formData.get('items') || '')) } catch { return { success: false, message: 'Invalid cart.' } }
  if (!Array.isArray(requestedItems) || requestedItems.length === 0) return { success: false, message: 'Your cart is empty.' }
  if (requestedItems.some((item) => !Number.isInteger(item.id) || !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 99)) return { success: false, message: 'Invalid cart quantity.' }

  const client = await pool.connect()
  try {
    await client.query('BEGIN')
    const existing = await client.query('SELECT id FROM orders WHERE idempotencykey = $1', [idempotencyKey])
    if (existing.rows[0]) { await client.query('COMMIT'); return { success: true, orderId: existing.rows[0].id } }

    const ids = [...new Set(requestedItems.map((item) => item.id))]
    const products = await client.query('SELECT id, price, stock FROM products WHERE id = ANY($1::int[]) FOR UPDATE', [ids])
    if (products.rows.length !== ids.length) throw new Error('One or more products are no longer available.')
    const byId = new Map(products.rows.map((product) => [product.id, product]))
    let total = 0
    for (const item of requestedItems) {
      const product = byId.get(item.id)
      if (!product || product.stock < item.quantity) throw new Error('One or more products do not have enough stock.')
      total += Number(product.price) * item.quantity
    }

    const order = await client.query(
      `INSERT INTO orders (userid, totalamount, status, paymentmethod, paymentstatus, customername, phone, address, idempotencykey)
       VALUES ($1, $2, 'pending', $3, 'unpaid', $4, $5, $6, $7) RETURNING id`,
      [session.user.id, total.toFixed(2), paymentMethod, name, phone, address, idempotencyKey],
    )
    for (const item of requestedItems) {
      const product = byId.get(item.id)
      await client.query('INSERT INTO order_items (orderid, productid, quantity, price) VALUES ($1, $2, $3, $4)', [order.rows[0].id, item.id, item.quantity, product.price])
      await client.query('UPDATE products SET stock = stock - $1 WHERE id = $2', [item.quantity, item.id])
    }
    await client.query('COMMIT')
    revalidatePath('/admin')
    return { success: true, orderId: order.rows[0].id }
  } catch (error) {
    await client.query('ROLLBACK')
    return { success: false, message: error instanceof Error ? error.message : 'Checkout failed.' }
  } finally { client.release() }
}