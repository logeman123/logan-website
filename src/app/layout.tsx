import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Cinzel_Decorative } from "next/font/google";
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
      <body className={`${inter.className} ${cinzelDecorative.variable}`}>
        {/* Navigation */}
        <nav className="fixed w-full z-50 py-4 px-6 bg-white/90 backdrop-blur-sm transition-colors duration-300">
          <div className="container mx-auto">
            <div className="flex justify-between items-center">
              <a href="/" className="text-xl font-light">
                Logan.
              </a>
              <div className="flex gap-8">
                <a href="/" className="hover:text-pink-500 transition-colors duration-300">Home</a>
                <a href="/resume" className="hover:text-pink-500 transition-colors duration-300">Resume</a>
                <a href="#projects" className="hover:text-pink-500 transition-colors duration-300">Project</a>
                <a href="#contact" className="hover:text-pink-500 transition-colors duration-300">Contact</a>
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
