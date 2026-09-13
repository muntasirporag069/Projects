import { Navbar } from '@/components/navbar'
import { ShopGrid } from '@/components/shop-grid'
import { getCollectionById, getProductsByCollection } from '@/app/actions/product'
import Link from 'next/link'
import Image from 'next/image'
import { notFound } from 'next/navigation'

interface CollectionPageProps { params: Promise<{ id: string }> }

export default async function CollectionPage({ params }: CollectionPageProps) {
  const { id } = await params
  const collectionId = Number.parseInt(id, 10)
  if (!Number.isInteger(collectionId) || collectionId < 1) notFound()
  const collection = await getCollectionById(collectionId)
  if (!collection) notFound()
  const products = await getProductsByCollection(collectionId)

  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <section className="pb-12 pt-32"><div className="relative h-96 w-full md:h-125"><Image src={collection.coverImage || '/placeholder.png'} alt={collection.title} fill className="object-cover" /><div className="absolute inset-0 flex flex-col justify-end bg-black/40 p-8"><h1 className="mb-2 text-5xl font-bold text-white">{collection.title}</h1><p className="text-xl text-white/80">{collection.season}</p></div></div></section>
      <section className="px-4 py-20"><div className="mx-auto max-w-7xl"><Link href="/" className="mb-8 inline-block font-semibold text-accent hover:underline">Back to Home</Link><div className="mb-20 grid grid-cols-1 gap-12 md:grid-cols-3"><div className="md:col-span-2"><h2 className="mb-4 text-3xl font-bold text-foreground">About This Collection</h2><p className="text-lg leading-relaxed text-muted-foreground">{collection.description || 'Explore the pieces in this collection.'}</p></div><div className="h-fit border border-border bg-card p-8"><h3 className="mb-4 text-xl font-bold text-foreground">Collection Info</h3><p className="text-sm text-muted-foreground">Season</p><p className="font-semibold text-foreground">{collection.season}</p><p className="mt-4 text-sm text-muted-foreground">Items</p><p className="font-semibold text-foreground">{products.length} Pieces</p></div></div><h2 className="mb-12 text-4xl font-bold text-foreground">Collection Pieces</h2>{products.length ? <ShopGrid products={products.map((product) => ({ id: product.id, name: product.name, category: product.category, price: String(product.price), image: product.image || '/placeholder.png' }))} /> : <p className="text-muted-foreground">This collection has no products yet.</p>}</div></section>
    </main>
  )
}
