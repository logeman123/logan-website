import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={inter.className}>
        {/* Fantasy Nav Bar */}
        <nav className="fantasy-nav p-4">
          <div className="max-w-4xl mx-auto flex flex-wrap justify-center gap-8">
            <a href="#education" className="fantasy-link">Education</a>
            <a href="#honors" className="fantasy-link">Honors</a>
            <a href="#experience" className="fantasy-link">Experience</a>
            <a href="#projects" className="fantasy-link">Projects</a>
            <a href="#skills" className="fantasy-link">Skills</a>
          </div>
        </nav>
        
        {/* Header with Name and Contact */}
        <header className="text-center py-12 relative">
          <div className="max-w-4xl mx-auto px-4">
            <h1 className="fantasy-heading text-4xl md:text-5xl mb-4">Logan Schwappach</h1>
            <div className="text-gold text-lg mb-2">Minneapolis, MN</div>
            <div className="space-y-1 text-light-gold">
              <div>lmschwappach.hws@gmail.com</div>
              <div>(612) 964-8300</div>
              <a 
                href="https://www.linkedin.com/in/logan-schwappach-9b57221b4/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="fantasy-link inline-block mt-2"
              >
                LinkedIn
              </a>
            </div>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4">
          {children}
        </main>
      </body>
    </html>
  );
}
