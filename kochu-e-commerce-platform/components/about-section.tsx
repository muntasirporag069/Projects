import Link from 'next/link'
import QRCode from 'qrcode'

export async function AboutSection() {
  let qrImage = ''
  try {
    qrImage = await QRCode.toDataURL('https://www.instagram.com/kochu.bd/')
  } catch (err) {
    console.log('[v0] QR code generation error:', err)
  }

  return (
    <section id="about" className="py-20 bg-primary text-primary-foreground">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-5xl font-bold mb-12 text-center">About KOCHU</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-16">
          {/* Mission & Values */}
          <div>
            <h3 className="text-2xl font-bold mb-6">Our Mission</h3>
            <p className="text-lg leading-relaxed mb-6">
              KOCHU is a luxury fashion collective dedicated to creating timeless pieces that celebrate individuality and craftsmanship. 
              We believe in sustainable luxury and ethical production practices.
            </p>
            
            <h3 className="text-2xl font-bold mb-6">Our Values</h3>
            <ul className="space-y-4 text-lg">
              <li className="flex items-start">
                <span className="text-accent mr-4">✓</span>
                <span>Craftsmanship: Every piece is meticulously crafted with attention to detail</span>
              </li>
              <li className="flex items-start">
                <span className="text-accent mr-4">✓</span>
                <span>Quality: We use only the finest materials and sustainable practices</span>
              </li>
              <li className="flex items-start">
                <span className="text-accent mr-4">✓</span>
                <span>Innovation: Pushing boundaries in fashion while respecting tradition</span>
              </li>
              <li className="flex items-start">
                <span className="text-accent mr-4">✓</span>
                <span>Inclusivity: Fashion for everyone, regardless of background or style</span>
              </li>
            </ul>
          </div>

          {/* Instagram & Contact */}
          <div className="flex flex-col items-center justify-center">
            <div className="bg-white p-6 rounded-lg mb-8">
              {qrImage ? (
                <img src={qrImage} alt="KOCHU Instagram QR Code" className="w-48 h-48" />
              ) : (
                <div className="w-48 h-48 bg-gray-200 flex items-center justify-center">
                  <span>QR Code</span>
                </div>
              )}
            </div>
            <p className="text-center mb-4">Follow us on Instagram</p>
            <Link
              href="https://www.instagram.com/kochu.bd/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent font-bold text-lg hover:underline"
            >
              @kochu.bd
            </Link>
            
            <div className="mt-12 pt-8 border-t border-primary-foreground/20">
              <h4 className="text-xl font-bold mb-4">Contact Us</h4>
              <div className="space-y-2 text-lg">
                <p>Email: info@kochu.fashion</p>
                <p>Phone: +880 1700 000000</p>
                <p>Location: Dhaka, Bangladesh</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
