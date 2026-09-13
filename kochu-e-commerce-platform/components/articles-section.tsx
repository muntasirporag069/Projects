'use client'

import Link from 'next/link'
import Image from 'next/image'

interface Article {
  id: number
  title: string
  abstract: string
  featured_image: string
}

interface ArticlesSectionProps {
  articles: Article[]
}

export function ArticlesSection({ articles }: ArticlesSectionProps) {
  return (
    <section id="articles" className="py-20 bg-card">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-5xl font-bold text-foreground mb-4 text-center">Fashion Articles</h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Dive into our latest insights on fashion, style trends, and the art of dressing well.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {articles.map((article) => (
            <Link
              key={article.id}
              href={`/article/${article.id}`}
              className="group"
            >
              <div className="relative h-64 overflow-hidden bg-muted mb-4">
                <Image
                  src={article.featured_image || 'https://via.placeholder.com/400x300'}
                  alt={article.title}
                  fill
                  className="object-cover group-hover:scale-105 transition duration-300"
                />
              </div>
              <h3 className="text-xl font-bold text-foreground group-hover:text-accent transition mb-2">
                {article.title}
              </h3>
              <p className="text-muted-foreground mb-4 line-clamp-2">{article.abstract}</p>
              <span className="text-accent font-semibold">Read More →</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
