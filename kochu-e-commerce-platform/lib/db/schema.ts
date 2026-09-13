import { pgTable, text, timestamp, boolean, serial, decimal, integer } from 'drizzle-orm/pg-core'

export const user = pgTable('user', {
  id: text('id').primaryKey(),
  name: text('name'),
  email: text('email').notNull().unique(),
  emailVerified: boolean('emailverified').notNull().default(false),
  image: text('image'),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  updatedAt: timestamp('updatedat').notNull().defaultNow(),
})

export const session = pgTable('session', {
  id: text('id').primaryKey(),
  expiresAt: timestamp('expiresat').notNull(),
  token: text('token').notNull().unique(),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  updatedAt: timestamp('updatedat').notNull().defaultNow(),
  ipAddress: text('ipAddress'),
  userAgent: text('userAgent'),
  userId: text('userid')
    .notNull()
    .references(() => user.id, { onDelete: 'cascade' }),
})

export const account = pgTable('account', {
  id: text('id').primaryKey(),
  accountId: text('accountid').notNull(),
  providerId: text('providerid').notNull(),
  userId: text('userid')
    .notNull()
    .references(() => user.id, { onDelete: 'cascade' }),
  accessToken: text('accesstoken'),
  refreshToken: text('refreshtoken'),
  idToken: text('idtoken'),
  accessTokenExpiresAt: timestamp('accesstokenexpiresat'),
  refreshTokenExpiresAt: timestamp('refreshtokenexpiresat'),
  scope: text('scope'),
  password: text('password'),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  updatedAt: timestamp('updatedat').notNull().defaultNow(),
})

export const verification = pgTable('verification', {
  id: text('id').primaryKey(),
  identifier: text('identifier').notNull(),
  value: text('value').notNull(),
  expiresAt: timestamp('expiresAt').notNull(),
  createdAt: timestamp('createdat').defaultNow(),
  updatedAt: timestamp('updatedat').defaultNow(),
})

export const collections = pgTable('collections', {
  id: serial('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description'),
  coverImage: text('coverimage').notNull(),
  season: text('season').notNull(),
  isActive: boolean('isActive').notNull().default(true),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  userId: text('userid'),
})

export const products = pgTable('products', {
  id: serial('id').primaryKey(),
  name: text('name').notNull(),
  description: text('description'),
  price: decimal('price', { precision: 10, scale: 2 }).notNull(),
  category: text('category').notNull(),
  image: text('image'),
  collectionId: integer('collectionid'),
  stock: integer('stock').default(0),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  userId: text('userid'),
})

export const articles = pgTable('articles', {
  id: serial('id').primaryKey(),
  title: text('title').notNull(),
  abstract: text('abstract').notNull(),
  content: text('content').notNull(),
  featured_image: text('featured_image'),
  collectionId: integer('collectionid'),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  userId: text('userid'),
})

export const earlyAccess = pgTable('early_access', {
  id: serial('id').primaryKey(),
  email: text('email').notNull().unique(),
  createdAt: timestamp('createdat').notNull().defaultNow(),
})

export const productDrops = pgTable('product_drops', {
  id: serial('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description'),
  dropTime: timestamp('droptime').notNull(),
  isActive: boolean('isactive').notNull().default(true),
  createdAt: timestamp('createdat').notNull().defaultNow(),
  userId: text('userid'),
})

export const orders = pgTable('orders', {
  id: serial('id').primaryKey(),
  userId: text('userid').notNull(),
  totalAmount: decimal('totalamount', { precision: 10, scale: 2 }).notNull(),
  status: text('status').notNull().default('pending'),
  stripePaymentId: text('stripepaymentid'),
  createdAt: timestamp('createdat').notNull().defaultNow(),
})

export const orderItems = pgTable('order_items', {
  id: serial('id').primaryKey(),
  orderId: integer('orderid').notNull(),
  productId: integer('productid').notNull(),
  quantity: integer('quantity').notNull(),
  price: decimal('price', { precision: 10, scale: 2 }).notNull(),
})
