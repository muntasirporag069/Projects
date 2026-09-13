import { headers } from 'next/headers'
import { auth } from '@/lib/auth'

const adminEmails = new Set(
  (process.env.ADMIN_EMAILS ?? '')
    .split(',')
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean),
)

export async function getAdminSession() {
  if (!auth || adminEmails.size === 0) return null

  const session = await auth.api.getSession({ headers: await headers() })
  if (!session?.user?.email || !adminEmails.has(session.user.email.toLowerCase())) return null

  return session
}