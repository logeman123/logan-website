import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      {/* Hero Section */}
      <section className="container mx-auto px-8 pt-32 pb-24">
        <div className="swiss-grid">
          <div className="col-span-12 md:col-span-7 space-y-8">
            <h1 className="display-large">
              Logan
              <br />
              Schwappach
            </h1>
            <p className="body-large text-text-secondary tracking-wide">
              DEVELOPER<span className="mx-4">·</span>2025
            </p>
            <Link 
              href="/resume"
              className="hover-line inline-block mt-8 text-lg tracking-wide"
            >
              VIEW DETAILS
            </Link>
          </div>
          <div className="col-span-12 md:col-span-5 mt-12 md:mt-0">
            <div className="image-container aspect-[4/5]">
              {/* Placeholder for hero image */}
              <div className="absolute inset-0 flex items-center justify-center text-text-secondary">
                Image
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Projects Section */}
      <section className="bg-[#f8f8f8] py-32">
        <div className="container mx-auto px-8">
          <h2 className="display-medium mb-16">Featured Projects</h2>
          <div className="swiss-grid">
            {/* Project 1 */}
            <div className="col-span-12 md:col-span-6 group">
              <div className="image-container aspect-square mb-6">
                <div className="absolute inset-0 flex items-center justify-center text-text-secondary">
                  01
                </div>
              </div>
              <h3 className="text-2xl font-light tracking-wide group-hover:text-accent transition-swiss">Project Name</h3>
              <p className="mt-2 text-text-secondary tracking-wide">2024</p>
            </div>
            {/* Project 2 */}
            <div className="col-span-12 md:col-span-6 group mt-16 md:mt-0">
              <div className="image-container aspect-square mb-6">
                <div className="absolute inset-0 flex items-center justify-center text-text-secondary">
                  02
                </div>
              </div>
              <h3 className="text-2xl font-light tracking-wide group-hover:text-accent transition-swiss">Project Name</h3>
              <p className="mt-2 text-text-secondary tracking-wide">2024</p>
            </div>
          </div>
        </div>
      </section>

      {/* Experience Section */}
      <section className="container mx-auto px-8 py-32">
        <div className="swiss-grid">
          <div className="col-span-12 md:col-span-7">
            <h2 className="display-medium mb-8">20+ Years of Practical Experience</h2>
            <p className="body-large text-text-secondary">
              Full stack developer with expertise in modern web technologies and a passion for creating elegant, efficient solutions.
            </p>
          </div>
          <div className="col-span-12 md:col-span-5 flex md:justify-end items-start mt-8 md:mt-0">
            <Link 
              href="/resume"
              className="hover-line text-lg tracking-wide"
            >
              VIEW MORE
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

