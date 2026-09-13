import { Navbar } from '@/components/navbar'
import { getProductById } from '@/app/actions/product'
import Link from 'next/link'
import Image from 'next/image'
import { notFound } from 'next/navigation'
import { AddToCartButton } from '@/components/add-to-cart-button'

interface ProductPageProps {
  params: Promise<{ id: string }>
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { id } = await params
  const productId = Number.parseInt(id, 10)
  if (!Number.isInteger(productId) || productId < 1) notFound()

  const product = await getProductById(productId)
  if (!product) notFound()

  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <section className="px-4 pb-20 pt-32">
        <div className="mx-auto max-w-6xl">
          <Link href="/#shop" className="mb-8 inline-block font-semibold text-accent hover:underline">Back to Shop</Link>
          <div className="grid grid-cols-1 gap-12 md:grid-cols-2">
            <div className="relative h-96 md:h-150"><Image src={product.image || '/placeholder.png'} alt={product.name} fill className="object-cover" /></div>
            <div>
              <h1 className="mb-2 text-4xl font-bold text-foreground">{product.name}</h1>
              <p className="mb-4 text-lg text-muted-foreground">{product.category}</p>
              <div className="mb-6 text-3xl font-bold text-accent">${Number(product.price).toFixed(2)}</div>
              <p className="mb-8 text-lg leading-relaxed text-foreground">{product.description || 'Product description unavailable.'}</p>
              <div className="flex gap-4"><AddToCartButton productId={product.id} /><button className="flex-1 border border-border px-6 py-4 font-semibold text-foreground transition hover:bg-muted">Wishlist</button></div>
              <p className="mt-8 border-t border-border pt-8 text-sm text-muted-foreground">Free shipping on orders over $300. Handcrafted with care. 30-day returns accepted.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
