import { Navbar } from '@/components/navbar'
import { CollectionCarousel } from '@/components/collection-carousel'
import { CountdownTimer } from '@/components/countdown-timer'
import { ShopGrid } from '@/components/shop-grid'
import { ArticlesSection } from '@/components/articles-section'
import { AboutSection } from '@/components/about-section'
import { getAllCollections, getAllProducts, getAllArticles } from '@/app/actions/product'
import Link from 'next/link'

export default async function Home() {
  const [collections, products, articles] = await Promise.all([
    getAllCollections(),
    getAllProducts(),
    getAllArticles(),
  ])

  // Format products for display
  const formattedProducts = products.map((p) => ({
    id: p.id,
    name: p.name,
    category: p.category,
    price: p.price as string,
    image: p.image || '/placeholder.png',
  }))

  // Format articles for display
  const formattedArticles = articles.map((a) => ({
    id: a.id,
    title: a.title,
    abstract: a.abstract,
    featured_image: a.featured_image || '/placeholder.png',
  }))

  // Format collections for carousel
  const formattedCollections = collections.map((c) => ({
    id: c.id,
    title: c.title,
    season: c.season,
    coverImage: c.coverImage,
    description: c.description || '',
  }))

  return (
    <main className="min-h-screen bg-background">
      <Navbar />

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-6xl md:text-7xl font-bold text-foreground mb-6 tracking-widest">KOCHU</h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Luxury fashion collective celebrating individuality, craftsmanship, and timeless elegance
          </p>
          <Link
            href="/#shop"
            className="inline-block px-8 py-4 bg-primary text-primary-foreground font-semibold hover:opacity-90 transition"
          >
            Explore Collections
          </Link>
        </div>
      </section>

      {/* Countdown Timer for Product Drop */}
      <CountdownTimer
        dropTime={new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()}
        title="New Collection Dropping Soon"
      />

      {/* Early Access Section */}
      <section className="py-20 bg-card">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-4">Early Access Registration</h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Be the first to know about new collections and exclusive drops. Register now for early access.
          </p>
          <Link
            href="/early-access"
            className="inline-block px-8 py-4 bg-accent text-accent-foreground font-semibold hover:opacity-90 transition"
          >
            Register Now
          </Link>
        </div>
      </section>

      {/* Collections Carousel */}
      <CollectionCarousel collections={formattedCollections} />

      {/* Shop Grid */}
      <ShopGrid products={formattedProducts} />

      {/* Articles Section */}
      <ArticlesSection articles={formattedArticles} />

      {/* About Section */}
      <AboutSection />

      {/* Footer */}
      <footer className="bg-foreground text-background py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <h3 className="font-bold mb-4">KOCHU</h3>
              <p className="text-sm opacity-80">Luxury fashion collective celebrating individuality and craftsmanship.</p>
            </div>
            <div>
              <h4 className="font-bold mb-4">Quick Links</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/#collections" className="hover:underline">
                    Collections
                  </Link>
                </li>
                <li>
                  <Link href="/#shop" className="hover:underline">
                    Shop
                  </Link>
                </li>
                <li>
                  <Link href="/#articles" className="hover:underline">
                    Articles
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Support</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/contact" className="hover:underline">
                    Contact
                  </Link>
                </li>
                <li>
                  <Link href="/faq" className="hover:underline">
                    FAQ
                  </Link>
                </li>
                <li>
                  <Link href="/shipping" className="hover:underline">
                    Shipping
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Follow</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="https://instagram.com/kochu.bd" target="_blank" rel="noopener noreferrer" className="hover:underline">
                    Instagram
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-background/20 pt-8 text-center text-sm opacity-80">
            <p>&copy; 2026 KOCHU. All rights reserved by Muntasir Hasan Porag.</p>
          </div>
        </div>
      </footer>
    </main>
  )
}
