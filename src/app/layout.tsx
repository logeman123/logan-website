import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Cinzel_Decorative } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });
const cinzelDecorative = Cinzel_Decorative({ 
  weight: ['400', '700'],
  subsets: ['latin'],
  variable: '--font-cinzel-decorative',
});

export const metadata: Metadata = {
  title: "Logan Schwappach - Personal Website",
  description: "Personal website and portfolio of Logan Schwappach",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} ${cinzelDecorative.variable} pt-20`}>
        {/* Navigation */}
        <nav className="nav-bar">
          <div className="container mx-auto">
            <div className="flex justify-between items-center h-20 px-8">
              <Link href="/" className="text-xl font-light tracking-wide hover-line">
                Logan.
              </Link>
              <div className="flex gap-12">
                <Link href="/" className="hover-line text-text-primary">Home</Link>
                <Link href="/resume" className="hover-line text-text-primary">Resume</Link>
                <Link href="#projects" className="hover-line text-text-primary">Projects</Link>
                <Link href="#contact" className="hover-line text-text-primary">Contact</Link>
              </div>
            </div>
          </div>
        </nav>

        <main>
          {children}
        </main>
      </body>
    </html>
  );
}
