import { ArrowRight, BookOpen, BrainCircuit, FlaskConical, Globe2, PenSquare, Sparkles, Trophy } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AuthStore } from '../store/auth';

const subjectCards = [
  {
    title: 'Mathematics',
    subtitle: 'Algebra • Geometry • Calculus Preview',
    icon: Sparkles,
    className: 'subject-gradient-math',
  },
  {
    title: 'Science',
    subtitle: 'Physics • Chemistry • Biology',
    icon: FlaskConical,
    className: 'subject-gradient-science',
  },
  {
    title: 'Social Science',
    subtitle: 'History • Geography • Civics',
    icon: Globe2,
    className: 'subject-gradient-history',
  },
];

const featureCards = [
  {
    icon: Sparkles,
    title: 'AI-Powered Explanations',
    text: 'Get instant, clear explanations tailored to your class level. Complex concepts made simple.',
    accent: 'accent-math',
  },
  {
    icon: BookOpen,
    title: 'CBSE Aligned Curriculum',
    text: 'Complete syllabus coverage across classes with chapter-first learning and revision support.',
    accent: 'accent-science',
  },
  {
    icon: BrainCircuit,
    title: 'Interactive Chat Tutor',
    text: 'Ask any question and get step-by-step solutions, examples, and follow-up help.',
    accent: 'accent-english',
  },
  {
    icon: Trophy,
    title: 'Practice and Quizzes',
    text: 'Test understanding with AI-generated quizzes and quick practice before exams.',
    accent: 'accent-history',
  },
  {
    icon: PenSquare,
    title: 'Writing and Revision',
    text: 'Summaries, concept notes, and answer support that help students revise faster.',
    accent: 'accent-civics',
  },
  {
    icon: ArrowRight,
    title: 'Progressive Learning Flow',
    text: 'Move naturally from subject to chapter to topic to AI support without clutter.',
    accent: 'accent-geography',
  },
];

export default function Landing() {
  const token = AuthStore((state) => state.token);

  return (
    <div className="marketing-page">
      <div className="marketing-shell">
        <header className="marketing-topbar">
          <Link to="/" className="student-brand">
            <span className="student-brand-mark">
              <Sparkles size={18} />
            </span>
            <strong>VidyaAI</strong>
          </Link>

          <div className="marketing-actions">
            <Link to={token ? '/app' : '/login'} className="ghost-link">Sign In</Link>
            <Link to={token ? '/app' : '/register'} className="primary-button">Start Learning</Link>
          </div>
        </header>

        <section className="hero-reference-card">
          <div className="hero-reference-copy">
            <span className="hero-badge">AI-Powered CBSE Learning Platform</span>
            <h1>
              Your Personal
              <br />
              <span className="gradient-text">AI Tutor</span>
              <br />
              for CBSE
            </h1>
            <p>
              Master every subject with step-by-step help, chapter summaries, quizzes, and calm learning support built around the way students actually study.
            </p>
            <div className="hero-actions">
              <Link to={token ? '/app' : '/register'} className="primary-button">Get Started Free</Link>
              <Link to={token ? '/app' : '/login'} className="ghost-link">I already have an account</Link>
            </div>
          </div>
          <div className="hero-reference-art">
            <div className="hero-reference-orb" />
            <div className="hero-reference-panel">
              <span className="mini-tag">Today&apos;s flow</span>
              <h3>Read the chapter, understand the topic, then practise instantly.</h3>
              <div className="preview-pill-row">
                <span>Concept Explanation</span>
                <span>Step-by-Step Solution</span>
                <span>Quiz Me</span>
              </div>
            </div>
          </div>
        </section>

        <section className="metrics-reference-grid">
          <div><strong>9 Classes</strong><span>Class 4 to Class 12</span></div>
          <div><strong>7+ Subjects</strong><span>CBSE Curriculum</span></div>
          <div><strong>100+ Topics</strong><span>Chapters & Subtopics</span></div>
          <div><strong>24/7</strong><span>AI Tutor Available</span></div>
        </section>

        <section className="landing-band">
          <div className="landing-band-head">
            <h2>All CBSE Subjects Covered</h2>
            <p>Clean navigation across the whole learning journey.</p>
          </div>
          <div className="subject-showcase-grid">
            {subjectCards.map((subject) => {
              const Icon = subject.icon;
              return (
                <article key={subject.title} className={`subject-showcase-card ${subject.className}`}>
                  <Icon size={28} />
                  <h3>{subject.title}</h3>
                  <p>{subject.subtitle}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="landing-band feature-reference-band">
          <div className="feature-reference-grid">
            {featureCards.map((feature) => {
              const Icon = feature.icon;
              return (
                <article key={feature.title} className="feature-reference-card">
                  <span className={`feature-icon-wrap ${feature.accent}`}>
                    <Icon size={22} />
                  </span>
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
