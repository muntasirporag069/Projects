import Link from 'next/link'
import Image from 'next/image'
import { redirect } from 'next/navigation'
import { getAdminSession } from '@/lib/admin'
import { databaseConfigured, pool } from '@/lib/db'
import { createArticle, createProduct, deleteArticle, deleteProduct, updateOrderStatus, updateProduct } from '@/app/actions/admin'
import { AdminDeleteButton } from '@/components/admin-delete-button'

type Order = {
  id: number
  email: string
  totalAmount: string
  status: string
  createdAt: Date
  itemCount: string
}

async function getAdminData() {
  const [statsResult, currentResult, historyResult, productsResult, articlesResult] = await Promise.all([
    pool.query(`
      SELECT
        COUNT(*)::int AS "totalOrders",
        COUNT(*) FILTER (WHERE status IN ('pending', 'processing', 'paid'))::int AS "openOrders",
        COUNT(*) FILTER (WHERE status IN ('delivered', 'completed'))::int AS "completedOrders",
        COALESCE(SUM(totalamount::numeric), 0)::text AS "grossRevenue"
      FROM orders
    `),
    pool.query(`
      SELECT o.id, COALESCE(u.email, o.userid) AS email, o.totalamount AS "totalAmount", o.status, o.createdat AS "createdAt",
        COALESCE(SUM(oi.quantity), 0)::text AS "itemCount"
      FROM orders o
      LEFT JOIN "user" u ON u.id = o.userid
      LEFT JOIN order_items oi ON oi.orderid = o.id
      WHERE o.status IN ('pending', 'processing', 'paid')
      GROUP BY o.id, u.email
      ORDER BY o.createdat DESC
      LIMIT 20
    `),
    pool.query(`
      SELECT o.id, COALESCE(u.email, o.userid) AS email, o.totalamount AS "totalAmount", o.status, o.createdat AS "createdAt",
        COALESCE(SUM(oi.quantity), 0)::text AS "itemCount"
      FROM orders o
      LEFT JOIN "user" u ON u.id = o.userid
      LEFT JOIN order_items oi ON oi.orderid = o.id
      WHERE o.status NOT IN ('pending', 'processing', 'paid')
      GROUP BY o.id, u.email
      ORDER BY o.createdat DESC
      LIMIT 20
    `),
    pool.query(`SELECT p.id, p.name, p.description, p.category, p.price, p.stock, c.title AS collectiontitle
      FROM products p LEFT JOIN collections c ON c.id = p.collectionid ORDER BY p.createdat DESC`),
    pool.query('SELECT id, title, abstract, createdat AS "createdAt" FROM articles ORDER BY createdat DESC'),
  ])

  return {
    stats: statsResult.rows[0],
    currentOrders: currentResult.rows as Order[],
    historyOrders: historyResult.rows as Order[],
    products: productsResult.rows,
    articles: articlesResult.rows,
  }
}

function formatDate(value: Date) {
  return new Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(new Date(value))
}

function OrderTable({ orders, emptyText }: { orders: Order[]; emptyText: string }) {
  if (orders.length === 0) return <p className="px-5 py-8 text-sm text-muted-foreground">{emptyText}</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="px-5 py-3 font-medium">Order</th>
            <th className="px-5 py-3 font-medium">Customer</th>
            <th className="px-5 py-3 font-medium">Items</th>
            <th className="px-5 py-3 font-medium">Total</th>
            <th className="px-5 py-3 font-medium">Status</th>
            <th className="px-5 py-3 font-medium">Placed</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {orders.map((order) => (
            <tr key={order.id} className="hover:bg-muted/20">
              <td className="px-5 py-4 font-semibold">#{order.id.toString().padStart(5, '0')}</td>
              <td className="px-5 py-4 text-muted-foreground">{order.email}</td>
              <td className="px-5 py-4">{order.itemCount}</td>
              <td className="px-5 py-4 font-medium">${Number(order.totalAmount).toFixed(2)}</td>
              <td className="px-5 py-4"><form action={updateOrderStatus} className="flex items-center gap-2"><input type="hidden" name="id" value={order.id} /><select name="status" defaultValue={order.status} className="border border-border bg-background px-2 py-1 text-xs capitalize"><option value="pending">Pending</option><option value="processing">Processing</option><option value="shipped">Shipped</option><option value="delivered">Delivered</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select><button className="text-xs font-semibold text-accent hover:underline">Save</button></form></td>
              <td className="px-5 py-4 text-muted-foreground">{formatDate(order.createdAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default async function AdminPage() {
  if (!databaseConfigured) {
    return <main className="min-h-screen bg-background p-8"><h1 className="text-3xl font-bold">Admin setup required</h1><p className="mt-3 text-muted-foreground">Set DATABASE_URL and ADMIN_EMAILS before using the admin panel.</p></main>
  }

  const session = await getAdminSession()
  if (!session) redirect('/sign-in?next=/admin')

  let data
  try {
    data = await getAdminData()
  } catch {
    return <main className="min-h-screen bg-background p-8"><h1 className="text-3xl font-bold">Database schema required</h1><p className="mt-3 text-muted-foreground">Run the database schema setup before opening the admin panel.</p></main>
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-background">
        <div className="mx-auto flex max-w-375 items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3"><Link href="/" className="flex items-center gap-2"><Image src="/IMG_5999.png" alt="KOCHU" width={40} height={40} className="object-contain" priority /><span className="text-2xl font-bold tracking-[0.25em]">KOCHU</span></Link><span className="ml-2 text-xs uppercase tracking-widest text-muted-foreground">Admin studio</span></div>
          <div className="flex items-center gap-4 text-sm"><span className="hidden text-muted-foreground sm:inline">{session.user.email}</span><Link href="/" className="font-semibold hover:text-accent">View store</Link></div>
        </div>
      </header>
      <div className="mx-auto max-w-375 px-6 py-10">
        <div className="mb-10"><p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent">Operations overview</p><h1 className="mt-2 text-4xl font-bold tracking-tight">Good morning, {session.user.name || 'Admin'}</h1><p className="mt-2 text-muted-foreground">A clear view of what needs attention across your store.</p></div>
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ['Gross revenue', `$${Number(data.stats.grossRevenue).toFixed(2)}`, 'All recorded orders'],
            ['Open orders', data.stats.openOrders, 'Needs fulfillment'],
            ['Completed orders', data.stats.completedOrders, 'Successfully delivered'],
            ['All orders', data.stats.totalOrders, 'Lifetime order volume'],
          ].map(([label, value, detail]) => <div key={label} className="border border-border bg-background p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-3 text-3xl font-bold">{value}</p><p className="mt-2 text-xs text-muted-foreground">{detail}</p></div>)}
        </section>
        <section className="mt-10 border border-border bg-background"><div className="border-b border-border px-5 py-4"><h2 className="text-xl font-bold">Present orders</h2><p className="mt-1 text-sm text-muted-foreground">Orders currently moving through fulfillment.</p></div><OrderTable orders={data.currentOrders} emptyText="No open orders right now." /></section>
        <section className="mt-10 border border-border bg-background"><div className="border-b border-border px-5 py-4"><h2 className="text-xl font-bold">Order history</h2><p className="mt-1 text-sm text-muted-foreground">Completed and closed orders.</p></div><OrderTable orders={data.historyOrders} emptyText="No completed orders yet." /></section>
        <div className="mt-10 grid gap-10 xl:grid-cols-2">
          <section className="border border-border bg-background">
            <div className="border-b border-border px-5 py-4"><h2 className="text-xl font-bold">Add product</h2><p className="mt-1 text-sm text-muted-foreground">Publish a new piece to the storefront.</p></div>
            <form action={createProduct} className="grid gap-4 p-5">
              <input name="name" required placeholder="Product name" className="border border-border bg-background px-3 py-2" />
              <div className="grid gap-4 sm:grid-cols-2"><input name="category" required placeholder="Category" className="border border-border bg-background px-3 py-2" /><input name="price" required placeholder="Price, e.g. 180.00" className="border border-border bg-background px-3 py-2" /></div>
              <div className="grid gap-4 sm:grid-cols-2"><input name="stock" required type="number" min="0" placeholder="Stock" className="border border-border bg-background px-3 py-2" /><input name="collectionName" required placeholder="Collection name" className="border border-border bg-background px-3 py-2" /></div>
              <input name="image" required type="file" accept="image/jpeg,image/png,image/webp,image/gif" className="border border-border bg-background px-3 py-2" />
              <textarea name="description" required placeholder="Description" rows={3} className="border border-border bg-background px-3 py-2" />
              <button className="bg-primary px-4 py-3 font-semibold text-primary-foreground hover:opacity-90">Add product</button>
            </form>
            <div className="border-t border-border"><div className="px-5 py-4 font-semibold">Catalog</div>{data.products.map((product) => <div key={product.id} className="border-t border-border px-5 py-4 text-sm"><div className="grid gap-2 sm:grid-cols-6"><form action={updateProduct} className="contents"><input type="hidden" name="id" value={product.id} /><input name="name" required defaultValue={product.name} className="border border-border bg-background px-2 py-1 sm:col-span-2" /><input name="category" required defaultValue={product.category} className="border border-border bg-background px-2 py-1" /><input name="price" required defaultValue={product.price} className="border border-border bg-background px-2 py-1" /><input name="stock" required type="number" min="0" defaultValue={product.stock ?? 0} className="border border-border bg-background px-2 py-1" /><input name="collectionName" required defaultValue={product.collectiontitle ?? ''} placeholder="Collection name" className="border border-border bg-background px-2 py-1" /><textarea name="description" required defaultValue={product.description ?? ''} rows={2} className="border border-border bg-background px-2 py-1 sm:col-span-5" /><button className="text-xs font-semibold text-accent hover:underline">Save</button></form><AdminDeleteButton action={deleteProduct} id={product.id} label={product.name} /></div></div>)}</div>
          </section>
          <section className="border border-border bg-background"><div className="border-b border-border px-5 py-4"><h2 className="text-xl font-bold">Add article</h2><p className="mt-1 text-sm text-muted-foreground">Share editorial content with your audience.</p></div><form action={createArticle} className="grid gap-4 p-5"><input name="title" required placeholder="Article title" className="border border-border bg-background px-3 py-2" /><input name="abstract" required placeholder="Short abstract" className="border border-border bg-background px-3 py-2" /><input name="featured_image" required placeholder="Featured image path or URL" className="border border-border bg-background px-3 py-2" /><textarea name="content" required placeholder="Article content" rows={7} className="border border-border bg-background px-3 py-2" /><button className="bg-primary px-4 py-3 font-semibold text-primary-foreground hover:opacity-90">Publish article</button></form><div className="border-t border-border"><div className="px-5 py-4 font-semibold">Published articles</div>{data.articles.map((article) => <div key={article.id} className="flex items-center justify-between border-t border-border px-5 py-3 text-sm"><div><p className="font-medium">{article.title}</p><p className="line-clamp-1 text-muted-foreground">{article.abstract}</p></div><AdminDeleteButton action={deleteArticle} id={article.id} label={article.title} /></div>)}</div></section>
        </div>
      </div>
    </main>
  )
}