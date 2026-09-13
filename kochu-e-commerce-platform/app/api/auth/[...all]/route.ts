import { auth } from '@/lib/auth'
import { databaseConfigured } from '@/lib/db'
import { toNextJsHandler } from 'better-auth/next-js'

const unavailable = () =>
	new Response('Authentication is unavailable until the database is configured.', {
		status: 503,
		headers: { 'Content-Type': 'text/plain' },
	})

const handlers = databaseConfigured ? toNextJsHandler(auth!.handler) : null

export const GET = handlers?.GET ?? unavailable
export const POST = handlers?.POST ?? unavailable
