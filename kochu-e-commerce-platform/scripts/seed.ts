import { db } from '@/lib/db'
import { collections, products, articles } from '@/lib/db/schema'

async function seed() {
  try {
    console.log('Seeding database...')

    // Insert collections
    const collectionResults = await db
      .insert(collections)
      .values([
        {
          title: 'Summer Elegance 2024',
          season: 'Summer 2024',
          description: 'Ethereal summer collection featuring flowing silhouettes and light fabrics',
          coverImage: '/collections/summer-2024.png',
          isActive: true,
        },
      ])
      .returning()

    const collectionId = collectionResults[0]?.id

    // Insert products
    await db.insert(products).values([
      {
        name: 'Tailored Pants',
        category: 'Pants',
        description: 'Elegant high-waisted tailored pants with cream silk lining',
        price: '180.00',
        image: '/products/kochu-pants-1.png',
        stock: 15,
        collectionId,
      },
      {
        name: 'Silk Button-Up Shirt',
        category: 'Shirts',
        description: 'Oversized cream silk button-up with gold embroidery details',
        price: '220.00',
        image: '/products/kochu-shirt-1.png',
        stock: 10,
        collectionId,
      },
      {
        name: 'Midi Skirt',
        category: 'Skirts',
        description: 'Flowing A-line black midi skirt with gold pleating details',
        price: '200.00',
        image: '/products/kochu-skirt-1.png',
        stock: 12,
        collectionId,
      },
      {
        name: 'Structured Corset',
        category: 'Corsets',
        description: 'Structured black satin corset with gold lacing details',
        price: '280.00',
        image: '/products/kochu-corset-1.png',
        stock: 8,
        collectionId,
      },
    ])

    // Insert articles
    await db.insert(articles).values([
      {
        title: 'The Art of Luxury Minimalism',
        abstract: 'Discover how less can be more in luxury fashion. Explore the philosophy behind minimalist design.',
        content:
          'Luxury minimalism is more than just a style—it\'s a philosophy. In this article, we explore how the restraint of materials and color palettes can create powerful fashion statements...',
        featured_image: '/collections/summer-2024.png',
        collectionId,
      },
      {
        title: 'Sustainable Fashion Forward',
        abstract: 'Learn about our commitment to sustainable and ethical fashion practices.',
        content:
          'At KOCHU, sustainability is not just a buzzword. We\'re committed to creating beautiful pieces while respecting our planet and the artisans who craft them...',
        featured_image: '/collections/summer-2024.png',
        collectionId,
      },
      {
        title: 'The Power of Tailoring',
        abstract: 'How perfect tailoring transforms a piece from good to exceptional.',
        content:
          'The difference between ordinary and extraordinary fashion lies in the details. Perfect tailoring can elevate any garment, making it uniquely yours...',
        featured_image: '/collections/summer-2024.png',
        collectionId,
      },
    ])

    console.log('Database seeded successfully!')
  } catch (error) {
    console.error('Error seeding database:', error)
    process.exit(1)
  }
}

seed()
