'use client'

import { useState } from 'react'
import { Navbar } from '@/components/navbar'
import { registerForEarlyAccess } from '@/app/actions/product'
import Link from 'next/link'

export default function EarlyAccessPage() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')

    try {
      const result = await registerForEarlyAccess(email)
      if (result.success) {
        setStatus('success')
        setMessage(result.message)
        setEmail('')
      } else {
        setStatus('error')
        setMessage(result.message)
      }
    } catch (error) {
      setStatus('error')
      setMessage('An error occurred. Please try again.')
    }

    setTimeout(() => setStatus('idle'), 5000)
  }

  return (
    <main className="min-h-screen bg-background">
      <Navbar />

      <section className="pt-40 pb-20 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-foreground mb-4">Early Access Registration</h1>
            <p className="text-lg text-muted-foreground">
              Be among the first to experience KOCHU&apos;s exclusive new collections and limited drops.
            </p>
          </div>

          <div className="bg-card border border-border p-8 md:p-12">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-foreground mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-border bg-background text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="your@email.com"
                />
              </div>

              <button
                type="submit"
                disabled={status === 'loading'}
                className="w-full px-6 py-3 bg-primary text-primary-foreground font-semibold hover:opacity-90 transition disabled:opacity-50"
              >
                {status === 'loading' ? 'Registering...' : 'Register for Early Access'}
              </button>

              {status === 'success' && (
                <div className="p-4 bg-green-100 border border-green-300 text-green-800 rounded">
                  {message}
                </div>
              )}

              {status === 'error' && (
                <div className="p-4 bg-red-100 border border-red-300 text-red-800 rounded">
                  {message}
                </div>
              )}
            </form>

            <div className="mt-8 pt-8 border-t border-border">
              <h3 className="text-lg font-semibold text-foreground mb-4">What You&apos;ll Get:</h3>
              <ul className="space-y-2 text-muted-foreground">
                <li className="flex items-start">
                  <span className="text-accent mr-3">✓</span>
                  <span>Early access to new collections before public release</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent mr-3">✓</span>
                  <span>Exclusive discount codes and special offers</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent mr-3">✓</span>
                  <span>Invitations to private KOCHU events</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent mr-3">✓</span>
                  <span>Priority customer support and styling consultations</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="text-center mt-8">
            <Link href="/" className="text-accent font-semibold hover:underline">
              ← Back to Home
            </Link>
          </div>
        </div>
      </section>
    </main>
  )
}
