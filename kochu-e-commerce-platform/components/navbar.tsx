'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useSession } from '@/lib/auth-client'
import { authClient } from '@/lib/auth-client'
import { useRouter } from 'next/navigation'
import { useCart } from '@/components/cart-provider'

export function Navbar() {
  const session = useSession()
  const router = useRouter()
  const { count } = useCart()

  const handleLogout = async () => {
    await authClient.signOut()
    router.refresh()
  }

  return (
    <nav className="fixed top-0 w-full bg-background border-b border-border z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <Image src="/IMG_5999.png" alt="KOCHU" width={48} height={48} className="h-12 w-12 object-contain" priority />
            <span className="ml-2 text-2xl font-bold tracking-widest text-foreground">KOCHU</span>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="/#collections" className="text-sm text-foreground hover:text-accent transition">
              Collections
            </Link>
            <Link href="/#shop" className="text-sm text-foreground hover:text-accent transition">
              Shop
            </Link>
            <Link href="/#articles" className="text-sm text-foreground hover:text-accent transition">
              Fashion Articles
            </Link>
            <Link href="/#about" className="text-sm text-foreground hover:text-accent transition">
              About KOCHU
            </Link>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            <Link href="/cart" className="text-foreground hover:text-accent transition">
              Cart ({count})
            </Link>
            {session?.data?.user ? (
              <>
                <Link href="/admin" className="hidden text-sm text-foreground hover:text-accent transition sm:inline">
                  Dashboard
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-sm px-4 py-2 bg-primary text-primary-foreground hover:opacity-90 transition"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link
                href="/sign-in"
                className="text-sm px-4 py-2 bg-primary text-primary-foreground hover:opacity-90 transition"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
