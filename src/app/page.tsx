import Link from 'next/link';
import Image from 'next/image';

export default function Home() {
  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="space-y-6">
            <h1 className="text-6xl font-light tracking-tight text-black">
              Logan
              <br />
              Schwappach
            </h1>
            <p className="text-xl text-gray-500">DEVELOPER 2024</p>
            <Link 
              href="/resume"
              className="inline-block mt-4 text-pink-500 hover:text-pink-600 transition-colors"
            >
              VIEW DETAILS →
            </Link>
          </div>
          <div className="relative aspect-[3/4] bg-gray-100">
            {/* Placeholder for hero image */}
            <div className="absolute inset-0 bg-gray-200 flex items-center justify-center text-gray-400">
              Image Placeholder
            </div>
          </div>
        </div>
      </div>

      {/* Featured Projects Section */}
      <div className="bg-gray-50 py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-light mb-12">Featured Projects</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Project 1 */}
            <div className="group cursor-pointer">
              <div className="relative aspect-square bg-gray-200 mb-4">
                <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                  Project Image 1
                </div>
              </div>
              <h3 className="text-2xl font-light group-hover:text-pink-500 transition-colors">Project Name</h3>
              <p className="text-gray-500">2024</p>
            </div>
            {/* Project 2 */}
            <div className="group cursor-pointer">
              <div className="relative aspect-square bg-gray-200 mb-4">
                <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                  Project Image 2
                </div>
              </div>
              <h3 className="text-2xl font-light group-hover:text-pink-500 transition-colors">Project Name</h3>
              <p className="text-gray-500">2024</p>
            </div>
          </div>
        </div>
      </div>

      {/* Experience Section */}
      <div className="container mx-auto px-4 py-20">
        <div className="flex justify-between items-start">
          <div className="max-w-lg">
            <h2 className="text-4xl font-light mb-6">We Have 20+ Years Practical Experience</h2>
            <p className="text-gray-500 leading-relaxed">
              Full stack developer with experience in modern web technologies and a passion for creating elegant, efficient solutions.
            </p>
          </div>
          <Link 
            href="/resume"
            className="text-pink-500 hover:text-pink-600 transition-colors"
          >
            VIEW MORE →
          </Link>
        </div>
      </div>
    </div>
  );
}
