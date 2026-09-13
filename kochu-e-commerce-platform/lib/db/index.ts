import { drizzle } from 'drizzle-orm/node-postgres'
import { Pool } from 'pg'
import * as schema from './schema'

export const databaseConfigured = Boolean(process.env.DATABASE_URL?.trim())

export const pool = new Pool({
  ...(databaseConfigured ? { connectionString: process.env.DATABASE_URL } : {}),
})

export const db = drizzle(pool, { schema })
