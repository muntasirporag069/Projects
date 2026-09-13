import { get } from '@vercel/blob'

export async function GET(request: Request) {
  const url = new URL(request.url).searchParams.get('url')
  if (!url) return new Response('Missing image URL.', { status: 400 })

  let blobUrl: URL
  try {
    blobUrl = new URL(url)
  } catch {
    return new Response('Invalid image URL.', { status: 400 })
  }

  if (!blobUrl.hostname.endsWith('.blob.vercel-storage.com')) {
    return new Response('Invalid image host.', { status: 400 })
  }

  try {
    const blob = await get(blobUrl.toString(), { access: 'private' })
    if (!blob) return new Response('Image not found.', { status: 404 })
    return new Response(blob.stream, {
      headers: {
        'Content-Type': blob.blob.contentType || 'application/octet-stream',
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    })
  } catch {
    return new Response('Unable to load image.', { status: 502 })
  }
}