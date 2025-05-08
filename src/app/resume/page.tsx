import TransformingHeader from '@/components/resume/TransformingHeader';
import '@/styles/resume.css';

export default function ResumePage() {
  return (
    <div className="resume-page">
      <div className="resume-container p-8 my-8 relative">
        {/* Decorative corners */}
        <div className="decorative-corner corner-top-left" />
        <div className="decorative-corner corner-top-right" />
        <div className="decorative-corner corner-bottom-left" />
        <div className="decorative-corner corner-bottom-right" />

        {/* Header with Name and Contact */}
        <header className="text-center py-8 mb-8 relative resume-section">
          <h1 className="resume-title text-4xl md:text-5xl mb-4">Logan Schwappach</h1>
          <div className="resume-location">San Fransisco, CA</div>
          <div className="space-y-1 contact-info">
            <div>lmschwappach.hws@gmail.com</div>
            <div className="flex justify-center gap-4 mt-2">
              <a 
                href="https://github.com/logeman123/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="social-link inline-block"
              >
                GitHub
              </a>
              <div>(612) 964-8300</div>
              <a 
                href="https://www.linkedin.com/in/logan-schwappach-9b57221b4/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="social-link inline-block"
              >
                LinkedIn
              </a>
            </div>
          </div>
        </header>

        {/* Education */}
        <section id="education" className="resume-section p-6 mb-8">
          <TransformingHeader className="text-2xl mb-4">Education</TransformingHeader>
          <div className="flex flex-col md:flex-row md:justify-between md:items-center">
            <div>
              <div className="font-bold text-lg">Hobart and William Smith Colleges, Geneva, NY</div>
              <div className="italic date-text">May 2023</div>
            </div>
            <div className="text-right mt-2 md:mt-0">
              <div>Double Major, BA: Economics, International Relations <span className="font-mono text-xs">GPA 3.16</span></div>
              <div>Minor: Computer Science</div>
            </div>
          </div>
        </section>

        {/* Honors */}
        <section id="honors" className="resume-section p-6 mb-8">
          <TransformingHeader className="text-2xl mb-4">Honors</TransformingHeader>
          <ul className="resume-list space-y-2">
            <li>Dean&apos;s List (2020-2023)</li>
            <li>National Merit Scholar (2019)</li>
          </ul>
        </section>

        {/* Experience */}
        <section id="experience" className="resume-section p-6 mb-8">
          <TransformingHeader className="text-2xl mb-4">Experience</TransformingHeader>
          <div className="space-y-6">
            <div>
              <div className="font-bold">Hoban Korean BBQ, Server</div>
              <div className="italic date-text">Aug 2023 - Present</div>
              <ul className="resume-list mt-2 space-y-2">
                <li>Main server since February 2024, competent ability in bartending</li>
                <li>Skillful knowledge in Korean cuisine, regular attendance and covers working an average of 5 days a week</li>
                <li>Additionally built up skills in both the food running positions and hosting positions, helped prepare new hires for hosting, serving and more</li>
              </ul>
            </div>
            <div>
              <div className="font-bold">Anne McGilvray and Company Inc, Sales</div>
              <div className="italic date-text">Jun – Aug 2022</div>
              <ul className="resume-list mt-2 space-y-2">
                <li>Attended the Atlanta and Las Vegas Gift Market representing vendors of AMCI, creating connections between buyers and vendors, trained new sales reps</li>
                <li>Personally oversaw the sale of more than $75,000 worth of wholesale gifts</li>
              </ul>
            </div>
            <div>
              <div className="font-bold">SeaBay (Summer Sandbox), Co-Founder, Geneva, NY</div>
              <div className="italic date-text">May – Aug 2021</div>
              <ul className="resume-list mt-2 space-y-2">
                <li>Designed and coded front end for a functional market website to sell and trade Coral products using wordpress.org</li>
                <li>Interviewed 120+ prospective customers, synthesized and presented information in a concise 6-minute presentation to coaches, startup accelerator teammates, and investors</li>
              </ul>
            </div>
            <div>
              <div className="font-bold">VSCO, Intern, San Francisco, CA</div>
              <div className="italic date-text">Apr – May 2019</div>
              <ul className="resume-list mt-2 space-y-2">
                <li>Conducted 50+ interviews of local high school students for market research focusing on changing trends in membership among younger demographics</li>
                <li>Compiled extensive survey data using excel, created a detailed and engaging marketing presentation for high level executive and company employees</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Projects */}
        <section id="projects" className="resume-section p-6 mb-8">
          <TransformingHeader className="text-2xl mb-4">Projects</TransformingHeader>
          <ul className="resume-list space-y-2">
            <li>Organizer For HWS: International Debate Round Robin (2021)</li>
            <li>Volunteer Building Cat Houses for St. Gabriel the Archangel Church (2019)</li>
            <li>Volunteer Animal Humane Society as Animal Technician (2017)</li>
          </ul>
        </section>

        {/* Activities & Skills */}
        <section id="skills" className="resume-section p-6">
          <TransformingHeader className="text-2xl mb-4">Activities & Skills</TransformingHeader>
          <div className="flex flex-col md:flex-row md:justify-between gap-8">
            <div>
              <div className="font-bold mb-2 section-title">Activities</div>
              <ul className="resume-list space-y-2">
                <li>(Varsity) Debate and Speech</li>
                <li>(VP) Chess Club</li>
                <li>Pre-Orientation Adventure Program (POAP)</li>
              </ul>
            </div>
            <div>
              <div className="font-bold mb-2 section-title">Skills</div>
              <ul className="resume-list space-y-2">
                <li>Language: Intermediate Spanish, Basic Korean</li>
                <li>Computer: Microsoft Office Suite, Java, Python</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
} 