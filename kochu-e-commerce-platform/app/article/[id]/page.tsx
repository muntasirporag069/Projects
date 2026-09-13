import { Navbar } from '@/components/navbar'
import { getArticleById } from '@/app/actions/product'
import Link from 'next/link'
import Image from 'next/image'
import { notFound } from 'next/navigation'

interface ArticlePageProps { params: Promise<{ id: string }> }

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { id } = await params
  const articleId = Number.parseInt(id, 10)
  if (!Number.isInteger(articleId) || articleId < 1) notFound()
  const article = await getArticleById(articleId)
  if (!article) notFound()

  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <section className="pt-32"><div className="relative h-64 w-full md:h-100"><Image src={article.featured_image || '/placeholder.png'} alt={article.title} fill className="object-cover" /></div></section>
      <section className="px-4 py-16"><article className="mx-auto max-w-3xl"><Link href="/#articles" className="mb-8 inline-block font-semibold text-accent hover:underline">Back to Articles</Link><h1 className="mb-4 text-5xl font-bold text-foreground">{article.title}</h1><p className="mb-8 border-b border-border pb-8 text-lg text-muted-foreground">{article.abstract}</p><div className="whitespace-pre-line text-lg leading-relaxed text-foreground">{article.content}</div></article></section>
    </main>
  )
}
