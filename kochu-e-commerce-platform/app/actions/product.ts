'use server'

import { databaseConfigured, db, pool } from '@/lib/db'
import { earlyAccess } from '@/lib/db/schema'
import { eq } from 'drizzle-orm'

const fallbackCollections = [
  {
    id: 1,
    title: 'Summer Elegance 2024',
    description: 'Ethereal summer collection featuring flowing silhouettes and light fabrics',
    coverImage: '/collections/summer-2024.png',
    season: 'Summer 2024',
    isActive: true,
  },
]

const fallbackProducts = [
  { id: 1, name: 'Tailored Pants', description: 'Elegant high-waisted tailored pants with cream silk lining', price: '180.00', category: 'Pants', image: '/products/kochu-pants-1.png', stock: 15 },
  { id: 2, name: 'Silk Button-Up Shirt', description: 'Oversized cream silk button-up with gold embroidery details', price: '220.00', category: 'Shirts', image: '/products/kochu-shirt-1.png', stock: 10 },
  { id: 3, name: 'Midi Skirt', description: 'Flowing A-line black midi skirt with gold pleating details', price: '200.00', category: 'Skirts', image: '/products/kochu-skirt-1.png', stock: 12 },
  { id: 4, name: 'Structured Corset', description: 'Structured black satin corset with gold lacing details', price: '280.00', category: 'Corsets', image: '/products/kochu-corset-1.png', stock: 8 },
]

const fallbackArticles = [
  { id: 1, title: 'The Art of Luxury Minimalism', abstract: 'Discover how less can be more in luxury fashion. Explore the philosophy behind minimalist design.', content: '', featured_image: '/collections/summer-2024.png' },
  { id: 2, title: 'Sustainable Fashion Forward', abstract: 'Learn about our commitment to sustainable and ethical fashion practices.', content: '', featured_image: '/collections/summer-2024.png' },
  { id: 3, title: 'The Power of Tailoring', abstract: 'How perfect tailoring transforms a piece from good to exceptional.', content: '', featured_image: '/collections/summer-2024.png' },
]

export async function getAllCollections() {
  if (!databaseConfigured) return fallbackCollections

  try {
    const result = await pool.query(`
      SELECT id, title, description, coverimage AS "coverImage", season, isactive AS "isActive", createdat AS "createdAt", userid AS "userId"
      FROM collections
      WHERE isactive = true
    `)
    return result.rows
  } catch (error) {
    console.error('[v0] Error fetching collections:', error)
    return []
  }
}

export async function getCollectionById(id: number) {
  if (!databaseConfigured) return fallbackCollections.find((collection) => collection.id === id) || null

  try {
    const result = await pool.query(
      `SELECT id, title, description, coverimage AS "coverImage", season, isactive AS "isActive", createdat AS "createdAt", userid AS "userId"
       FROM collections WHERE id = $1`,
      [id]
    )
    return result.rows[0] || null
  } catch (error) {
    console.error('[v0] Error fetching collection:', error)
    return null
  }
}

export async function getAllProducts() {
  if (!databaseConfigured) return fallbackProducts

  try {
    const result = await pool.query(`
      SELECT id, name, description, price, category, image, collectionid AS "collectionId", stock, createdat AS "createdAt", userid AS "userId"
      FROM products
    `)
    return result.rows
  } catch (error) {
    console.error('[v0] Error fetching products:', error)
    return []
  }
}

export async function getProductsByCategory(category: string) {
  if (!databaseConfigured) return fallbackProducts.filter((product) => product.category === category)

  try {
    const result = await pool.query(
      `SELECT id, name, description, price, category, image, collectionid AS "collectionId", stock, createdat AS "createdAt", userid AS "userId"
       FROM products WHERE category = $1`,
      [category]
    )
    return result.rows
  } catch (error) {
    console.error('[v0] Error fetching products by category:', error)
    return []
  }
}

export async function getProductsByCollection(collectionId: number) {
  if (!databaseConfigured) return fallbackProducts.filter((product) => product.id <= 4)

  try {
    const result = await pool.query(
      `SELECT id, name, description, price, category, image, collectionid AS "collectionId", stock, createdat AS "createdAt", userid AS "userId"
       FROM products WHERE collectionid = $1 ORDER BY createdat DESC`,
      [collectionId]
    )
    return result.rows
  } catch (error) {
    console.error('[v0] Error fetching products by collection:', error)
    return []
  }
}

export async function getProductById(id: number) {
  if (!databaseConfigured) return fallbackProducts.find((product) => product.id === id) || null

  try {
    const result = await pool.query(
      `SELECT id, name, description, price, category, image, collectionid AS "collectionId", stock, createdat AS "createdAt", userid AS "userId"
       FROM products WHERE id = $1`,
      [id]
    )
    return result.rows[0] || null
  } catch (error) {
    console.error('[v0] Error fetching product:', error)
    return null
  }
}

export async function getAllArticles() {
  if (!databaseConfigured) return fallbackArticles

  try {
    const result = await pool.query(`
      SELECT id, title, abstract, content, featured_image, collectionid AS "collectionId", createdat AS "createdAt", userid AS "userId"
      FROM articles
    `)
    return result.rows
  } catch (error) {
    console.error('[v0] Error fetching articles:', error)
    return []
  }
}

export async function getArticleById(id: number) {
  if (!databaseConfigured) return fallbackArticles.find((article) => article.id === id) || null

  try {
    const result = await pool.query(
      `SELECT id, title, abstract, content, featured_image, collectionid AS "collectionId", createdat AS "createdAt", userid AS "userId"
       FROM articles WHERE id = $1`,
      [id]
    )
    return result.rows[0] || null
  } catch (error) {
    console.error('[v0] Error fetching article:', error)
    return null
  }
}

export async function registerForEarlyAccess(email: string) {
  if (!databaseConfigured) {
    return { success: false, message: 'Early access registration is unavailable until the database is configured.' }
  }

  try {
    await db.insert(earlyAccess).values({ email })
    return { success: true, message: 'Successfully registered for early access!' }
  } catch (error: any) {
    if (error.code === '23505') {
      return { success: false, message: 'Email already registered' }
    }
    console.error('[v0] Error registering for early access:', error)
    return { success: false, message: 'Failed to register. Please try again.' }
  }
}
