'use server'

import { revalidatePath } from 'next/cache'
import { del, put } from '@vercel/blob'
import { databaseConfigured, db, pool } from '@/lib/db'
import { articles, products } from '@/lib/db/schema'
import { getAdminSession } from '@/lib/admin'

async function uploadImage(formData: FormData, name: string) {
  const file = formData.get(name)
  if (!(file instanceof File) || file.size === 0) throw new Error('Please select an image.')
  const allowedTypes = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif'])
  if (!allowedTypes.has(file.type)) throw new Error('Only JPG, PNG, WEBP, and GIF images are allowed.')
  if (file.size > 5 * 1024 * 1024) throw new Error('Images must be 5 MB or smaller.')
  if (!process.env.BLOB_READ_WRITE_TOKEN) throw new Error('Image storage is not configured.')
  const extension = file.name.split('.').pop()?.toLowerCase() || 'jpg'
  const blob = await put(`products/${crypto.randomUUID()}.${extension}`, file, { access: 'private' })
  return `/api/images?url=${encodeURIComponent(blob.url)}`
}

async function removeBlob(url: unknown) {
  if (typeof url === 'string') {
    const blobUrl = url.startsWith('/api/images?url=')
      ? new URL(url, 'http://localhost').searchParams.get('url')
      : url
    if (blobUrl?.includes('.blob.vercel-storage.com/')) {
      try { await del(blobUrl) } catch (error) { console.error('[admin] Could not remove image blob:', error) }
    }
  }
}

async function requireAdmin() {
  if (!databaseConfigured) throw new Error('Database is not configured.')
  const session = await getAdminSession()
  if (!session) throw new Error('Unauthorized')
  return session
}

function requiredText(formData: FormData, name: string) {
  const value = formData.get(name)
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${name} is required.`)
  return value.trim()
}

function positiveInteger(formData: FormData, name: string) {
  const value = Number.parseInt(requiredText(formData, name), 10)
  if (!Number.isInteger(value) || value < 0) throw new Error(`${name} must be a positive whole number.`)
  return value
}

async function getOrCreateCollectionId(name: string) {
  const title = name.trim()
  const existing = await pool.query(
    `SELECT id FROM collections WHERE lower(trim(title)) = lower($1) ORDER BY isactive DESC, id LIMIT 1`,
    [title],
  )
  if (existing.rows[0]) return existing.rows[0].id as number

  const created = await pool.query(
    `INSERT INTO collections (title, description, coverimage, season, isactive)
     VALUES ($1, $2, $3, $4, true) RETURNING id`,
    [title, null, '/placeholder.jpg', 'Custom'],
  )
  return created.rows[0].id as number
}

export async function createProduct(formData: FormData) {
  const session = await requireAdmin()
  const name = requiredText(formData, 'name')
  const category = requiredText(formData, 'category')
  const price = requiredText(formData, 'price')
  const collectionId = await getOrCreateCollectionId(requiredText(formData, 'collectionName'))
  if (!/^\d+(\.\d{1,2})?$/.test(price)) throw new Error('Price must be a valid amount.')

  await db.insert(products).values({
    name,
    category,
    price,
    description: requiredText(formData, 'description'),
    image: await uploadImage(formData, 'image'),
    stock: positiveInteger(formData, 'stock'),
    collectionId,
    userId: session.user.id,
  })

  revalidatePath('/')
  revalidatePath('/admin')
}

export async function deleteProduct(formData: FormData) {
  await requireAdmin()
  const id = positiveInteger(formData, 'id')
  const result = await pool.query('DELETE FROM products WHERE id = $1 RETURNING image', [id])
  await removeBlob(result.rows[0]?.image)
  revalidatePath('/')
  revalidatePath('/admin')
}

export async function createArticle(formData: FormData) {
  const session = await requireAdmin()
  await db.insert(articles).values({
    title: requiredText(formData, 'title'),
    abstract: requiredText(formData, 'abstract'),
    content: requiredText(formData, 'content'),
    featured_image: requiredText(formData, 'featured_image'),
    userId: session.user.id,
  })

  revalidatePath('/')
  revalidatePath('/admin')
}

export async function deleteArticle(formData: FormData) {
  await requireAdmin()
  const id = positiveInteger(formData, 'id')
  const result = await pool.query('DELETE FROM articles WHERE id = $1 RETURNING featured_image', [id])
  await removeBlob(result.rows[0]?.featured_image)
  revalidatePath('/')
  revalidatePath('/admin')
}

export async function updateOrderStatus(formData: FormData) {
  await requireAdmin()
  const id = positiveInteger(formData, 'id')
  const status = requiredText(formData, 'status')
  const allowedStatuses = new Set(['pending', 'processing', 'shipped', 'delivered', 'completed', 'cancelled'])
  if (!allowedStatuses.has(status)) throw new Error('Invalid order status.')

  const current = await pool.query('SELECT status FROM orders WHERE id = $1', [id])
  const currentStatus = current.rows[0]?.status
  const transitions: Record<string, string[]> = {
    pending: ['processing', 'cancelled'],
    processing: ['shipped', 'cancelled'],
    shipped: ['delivered'],
    delivered: ['completed'],
    completed: [],
    cancelled: [],
  }
  if (!currentStatus || !transitions[currentStatus]?.includes(status)) throw new Error('Invalid order status transition.')
  await pool.query('UPDATE orders SET status = $1 WHERE id = $2', [status, id])
  revalidatePath('/admin')
}

export async function updateProduct(formData: FormData) {
  await requireAdmin()
  const id = positiveInteger(formData, 'id')
  const name = requiredText(formData, 'name')
  const category = requiredText(formData, 'category')
  const price = requiredText(formData, 'price')
  const collectionId = await getOrCreateCollectionId(requiredText(formData, 'collectionName'))
  if (!/^\d+(\.\d{1,2})?$/.test(price)) throw new Error('Price must be a valid amount.')

  await pool.query(
    `UPDATE products SET name = $1, description = $2, price = $3, category = $4, collectionid = $5, stock = $6 WHERE id = $7`,
    [name, requiredText(formData, 'description'), price, category, collectionId, positiveInteger(formData, 'stock'), id],
  )
  revalidatePath('/')
  revalidatePath('/admin')
  revalidatePath(`/product/${id}`)
}