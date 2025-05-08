export default function Home() {
  return (
    <div className="fantasy-container p-8 my-8 relative">
      {/* Decorative corners */}
      <div className="corner-decoration corner-top-left" />
      <div className="corner-decoration corner-top-right" />
      <div className="corner-decoration corner-bottom-left" />
      <div className="corner-decoration corner-bottom-right" />

      {/* Education */}
      <section id="education" className="fantasy-block p-6 mb-8">
        <h2 className="fantasy-heading text-2xl mb-4">Education</h2>
        <div className="flex flex-col md:flex-row md:justify-between md:items-center">
          <div>
            <div className="font-bold text-lg">Hobart and William Smith Colleges, Geneva, NY</div>
            <div className="italic text-gold">Anticipated May 2023</div>
          </div>
          <div className="text-right mt-2 md:mt-0">
            <div>Double Major, BA: Economics, International Relations <span className="font-mono text-xs">Major GPA 3.39</span></div>
            <div>Minor: Computer Science <span className="font-mono text-xs">Overall GPA 3.18</span></div>
          </div>
        </div>
      </section>

      {/* Honors */}
      <section id="honors" className="fantasy-block p-6 mb-8">
        <h2 className="fantasy-heading text-2xl mb-4">Honors</h2>
        <ul className="fantasy-list space-y-2">
          <li>Dean&apos;s List (2020-2022)</li>
          <li>National Merit Scholar (2019)</li>
        </ul>
      </section>

      {/* Experience */}
      <section id="experience" className="fantasy-block p-6 mb-8">
        <h2 className="fantasy-heading text-2xl mb-4">Experience</h2>
        <div className="space-y-6">
          <div>
            <div className="font-bold">Anne McGilvray and Company Inc, Sales</div>
            <div className="italic text-gold">Jun – Aug 2022</div>
            <ul className="fantasy-list mt-2 space-y-2">
              <li>Attended the Atlanta and Las Vegas Gift Market representing vendors of AMCI, creating connections between buyers and vendors, trained new sales reps</li>
              <li>Personally oversaw the sale of more than $75,000 worth of wholesale gifts</li>
            </ul>
          </div>
          <div>
            <div className="font-bold">SeaBay (Summer Sandbox), Co-Founder, Geneva, NY</div>
            <div className="italic text-gold">May – Aug 2021</div>
            <ul className="fantasy-list mt-2 space-y-2">
              <li>Designed and coded front end for a functional market website to sell and trade Coral products using wordpress.org</li>
              <li>Interviewed 120+ prospective customers, synthesized and presented information in a concise 6-minute presentation to coaches, startup accelerator teammates, and investors</li>
            </ul>
          </div>
          <div>
            <div className="font-bold">W. P. Carey, Summer Business Analyst, New York, NY</div>
            <div className="italic text-gold">May – Aug 2020</div>
            <ul className="fantasy-list mt-2">
              <li>Cancelled due to COVID</li>
            </ul>
          </div>
          <div>
            <div className="font-bold">VSCO, Intern, San Francisco, CA</div>
            <div className="italic text-gold">Apr – May 2019</div>
            <ul className="fantasy-list mt-2 space-y-2">
              <li>Conducted 50+ interviews of local high school students for market research focusing on changing trends in membership among younger demographics</li>
              <li>Compiled extensive survey data using excel, created a detailed and engaging marketing presentation for high level executive and company employees</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Projects */}
      <section id="projects" className="fantasy-block p-6 mb-8">
        <h2 className="fantasy-heading text-2xl mb-4">Projects</h2>
        <ul className="fantasy-list space-y-2">
          <li>Organizer For HWS: International Debate Round Robin (2021)</li>
          <li>Volunteer Building Cat Houses for St. Gabriel the Archangel Church (2019)</li>
          <li>Volunteer Animal Humane Society as Animal Technician (2017)</li>
        </ul>
      </section>

      {/* Activities & Skills */}
      <section id="skills" className="fantasy-block p-6">
        <h2 className="fantasy-heading text-2xl mb-4">Activities & Skills</h2>
        <div className="flex flex-col md:flex-row md:justify-between gap-8">
          <div>
            <div className="font-bold mb-2 text-gold">Activities</div>
            <ul className="fantasy-list space-y-2">
              <li>Debate and Speech Club</li>
              <li>Pre-Orientation Adventure Program (POAP)</li>
              <li>HWS Day of Service</li>
            </ul>
          </div>
          <div>
            <div className="font-bold mb-2 text-gold">Skills</div>
            <ul className="fantasy-list space-y-2">
              <li>Language: Intermediate Spanish, Basic Korean</li>
              <li>Computer: Microsoft Office Suite, Java, Python</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
