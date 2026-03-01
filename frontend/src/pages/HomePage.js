import { useEffect, useMemo, useRef, useState } from 'react';
import { getAIStatus } from '../services/api';
import './HomePage.css';

const PREAUTH_QUESTIONS = [
  {
    id: 'admissions',
    label: 'Admission requirements and deadlines',
    answer:
      'Students can view requirements by program, upcoming deadlines, and document checklists directly in the widget before logging in.',
  },
  {
    id: 'application_process',
    label: 'Application process step-by-step',
    answer:
      'The assistant guides prospects from program selection to final submission, then routes them to your ERP portal at the right step.',
  },
  {
    id: 'tuition',
    label: 'Tuition fees and payment options',
    answer:
      'Fee structures, installment options, and payment windows are surfaced instantly, reducing repetitive finance calls and email volume.',
  },
  {
    id: 'scholarships',
    label: 'Scholarship opportunities',
    answer:
      'Scholarship categories, eligibility rules, and timelines can be delivered in plain language based on your institution rules.',
  },
  {
    id: 'campus_tour',
    label: 'Campus tour information',
    answer:
      'The bot can direct students to in-person and virtual tour schedules and trigger registrations via your event workflow.',
  },
  {
    id: 'contact_admissions',
    label: 'Contact admissions office',
    answer:
      'Prospects receive office hours, contact routes, and escalation options if they need a human response.',
  },
  {
    id: 'departments',
    label: 'Department information',
    answer:
      'Department summaries, major pathways, and faculty highlights are provided with links to deeper program pages.',
  },
  {
    id: 'ug_vs_pg',
    label: 'Undergraduate vs Graduate programs',
    answer:
      'The assistant clarifies differences in entry criteria, curriculum depth, and expected outcomes for each level.',
  },
  {
    id: 'international_students',
    label: 'International student requirements',
    answer:
      'Visa, language proof, credential evaluation, and compliance steps are organized in one pre-login guidance flow.',
  },
  {
    id: 'housing',
    label: 'Housing availability',
    answer:
      'Students can check housing windows, room categories, and application timelines without waiting for email support.',
  },
];

const BRAND_THEMES = [
  { id: 'classic', name: 'Classic Navy', primary: '#2563eb', accent: '#14b8a6' },
  { id: 'sunrise', name: 'Sunrise Coral', primary: '#ea580c', accent: '#f59e0b' },
  { id: 'emerald', name: 'Emerald Green', primary: '#059669', accent: '#84cc16' },
];

const UNIVERSITY_PROFILES = [
  {
    id: 'dayananda-sagar-university',
    name: 'Dayananda Sagar University',
    logo: 'DSU',
    themeId: 'classic',
    note: 'Dedicated tenant for engineering, management, and undergraduate policy guidance.',
  },
  {
    id: 'bmsce',
    name: 'BMSCE',
    logo: 'BMS',
    themeId: 'sunrise',
    note: 'Dedicated tenant for branch-level academic workflows and student support routing.',
  },
  {
    id: 'rvce',
    name: 'RV College of Engineering',
    logo: 'RVC',
    themeId: 'emerald',
    note: 'Dedicated tenant for curriculum assistance, placement preparation, and progress tracking.',
  },
  {
    id: 'pes-university',
    name: 'PES University',
    logo: 'PES',
    themeId: 'classic',
    note: 'Dedicated tenant for program advising, assessments, and student success analytics.',
  },
  {
    id: 'jain-university',
    name: 'Jain University',
    logo: 'JAIN',
    themeId: 'sunrise',
    note: 'Dedicated tenant for admissions, interdisciplinary programs, and learning support.',
  },
];

const SIGNATURE_TRAITS = [
  'Campus-grounded answers',
  'Role-aware responses',
  'Workflow handoffs',
  'Learning intelligence',
];

const VALUE_PILLARS = [
  {
    title: 'Institution-tuned model behavior',
    detail: 'Grounded on your approved policies, documents, and academic context, not public internet noise.',
  },
  {
    title: 'End-to-end student intelligence',
    detail: 'Starts with public Q&A and continues after login with study generation and guided learning flows.',
  },
  {
    title: 'Actionable progress signals',
    detail: 'Tracks quiz trends, skill development, and topic coverage so staff can identify gaps early.',
  },
];

const INTEGRATION_STEPS = [
  {
    title: 'Ground the model on campus knowledge',
    detail:
      'Connect institutional documents, policy rules, and academic catalogs to the retrieval layer.',
  },
  {
    title: 'Connect workflows and permissions',
    detail:
      'Link your ERP, role access, and escalation paths so answers can trigger the correct next action.',
  },
  {
    title: 'Launch and continuously tune',
    detail:
      'Deploy across website and student portal, then improve accuracy using real usage analytics.',
  },
];

const PLATFORM_FEATURES = [
  'Grounded responses from university-approved knowledge sources',
  'Pre-login public assistant plus post-login personal learning copilot',
  'Document Q&A, flashcards, quizzes, and summary generation',
  'Student progress tracking with skill and coverage signals',
  'Human escalation routing for high-risk or unresolved queries',
  'University branding with logo, tone, and colors',
  'Offline-safe behavior with graceful fallback messaging',
  'Multi-language support roadmap for Phase 2',
];

export default function HomePage({ onStudentLogin, onAdminLogin, onBack }) {
  const [widgetOpen, setWidgetOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'This is the public campus assistant preview. After login, it shifts into a personalized learning copilot.',
    },
  ]);
  const [selectedUniversityId, setSelectedUniversityId] = useState(UNIVERSITY_PROFILES[0].id);
  const [selectedThemeId, setSelectedThemeId] = useState(UNIVERSITY_PROFILES[0].themeId);
  const [universityName, setUniversityName] = useState(UNIVERSITY_PROFILES[0].name);
  const [logoText, setLogoText] = useState(UNIVERSITY_PROFILES[0].logo);
  const [aiStatus, setAiStatus] = useState({
    status: 'checking',
    model: '',
    message: 'Checking AI availability...',
  });
  const transcriptRef = useRef(null);

  const selectedUniversity = useMemo(
    () => UNIVERSITY_PROFILES.find((item) => item.id === selectedUniversityId) || UNIVERSITY_PROFILES[0],
    [selectedUniversityId]
  );

  const selectedTheme = useMemo(
    () => BRAND_THEMES.find((theme) => theme.id === selectedThemeId) || BRAND_THEMES[0],
    [selectedThemeId]
  );

  useEffect(() => {
    let active = true;

    getAIStatus()
      .then((res) => {
        if (!active) return;
        const payload = res.data || {};
        setAiStatus({
          status: payload.status || 'unknown',
          model: payload.model || '',
          message: payload.message || '',
        });
      })
      .catch(() => {
        if (!active) return;
        setAiStatus({
          status: 'offline',
          model: '',
          message: 'Campus LLM is currently unavailable. Users will see a safe fallback notice.',
        });
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const node = transcriptRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages, widgetOpen]);

  useEffect(() => {
    setUniversityName(selectedUniversity.name);
    setLogoText(selectedUniversity.logo);
    setSelectedThemeId(selectedUniversity.themeId);
    setMessages([
      {
        role: 'assistant',
        text: `This is ${selectedUniversity.name}'s public assistant. After login, it unlocks personalized learning and progress tracking.`,
      },
    ]);
  }, [selectedUniversity]);

  const isOffline = aiStatus.status === 'offline';
  const statusLabel =
    aiStatus.status === 'online'
      ? 'AI Online'
      : aiStatus.status === 'checking'
        ? 'Checking AI'
        : 'AI Offline';

  const handleQuestionClick = (question) => {
    setWidgetOpen(true);
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: question.label },
      {
        role: 'assistant',
        text: `${question.answer} This answer is scoped to ${universityName}'s configured knowledge base.`,
      },
    ]);
  };

  const scrollToIntegration = () => {
    const integrationSection = document.getElementById('integration');
    if (integrationSection) {
      integrationSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div
      className="home-shell"
      style={{
        '--brand-primary': selectedTheme.primary,
        '--brand-accent': selectedTheme.accent,
      }}
    >
      <div className="home-gradient" aria-hidden="true" />

      <main className="home-content">
        <section className="card home-hero">
          <p className="home-kicker">CUSTOM CAMPUS LLM PLATFORM</p>
          <h1>Your students already use AI. Give them one trained for your university.</h1>
          <p className="home-subtitle">
            Uniwise is a university-specific intelligence layer: grounded answers, guided workflows,
            learning support, and progress tracking integrated with your existing systems. Each campus
            runs in a separate workspace with dedicated knowledge and analytics.
          </p>

          <div className="home-cta-row">
            {onBack && (
              <button type="button" className="btn btn-secondary home-cta" onClick={onBack}>
                Back to options
              </button>
            )}
            <button type="button" className="btn btn-primary home-cta" onClick={scrollToIntegration}>
              See deployment model
            </button>
            <button type="button" className="btn btn-secondary home-cta" onClick={() => setWidgetOpen(true)}>
              Open widget preview
            </button>
            <button type="button" className="btn btn-secondary home-cta" onClick={onStudentLogin}>
              Student Login
            </button>
            <button type="button" className="btn btn-secondary home-cta" onClick={onAdminLogin}>
              Admin Login
            </button>
          </div>

          <div className="integration-strip">
            {SIGNATURE_TRAITS.map((item) => (
              <span key={item} className="integration-pill">
                {item}
              </span>
            ))}
          </div>
        </section>

        <section className="home-grid home-grid-three">
          {VALUE_PILLARS.map((pillar) => (
            <article key={pillar.title} className="card stat-card">
              <p className="stat-value">{pillar.title}</p>
              <p className="stat-label">{pillar.detail}</p>
            </article>
          ))}
        </section>

        <section id="integration" className="card home-card integration-card">
          <h2>How the custom LLM fits your stack</h2>
          <div className="integration-layout">
            <ol className="step-list">
              {INTEGRATION_STEPS.map((step) => (
                <li key={step.title}>
                  <h3>{step.title}</h3>
                  <p>{step.detail}</p>
                </li>
              ))}
            </ol>

            <div className="integration-side">
              <h3>Grounding sources and system hooks</h3>
              <ul className="integration-data-list">
                <li>Program handbooks and policy documents</li>
                <li>Course catalogs and department knowledge</li>
                <li>Admissions, tuition, and scholarship rules</li>
                <li>Student profile context and role permissions</li>
                <li>Assessment results and progress indicators</li>
                <li>ERP and portal routing endpoints</li>
                <li>University-specific tenant isolation and analytics</li>
              </ul>
              <p className="phase-note">
                Multi-language support is in Phase 2 and can be enabled after base rollout.
              </p>
            </div>
          </div>
        </section>

        <section className="home-grid">
          <article className="card home-card">
            <h2>What makes this different from a generic ERP bot</h2>
            <ul className="feature-list">
              {PLATFORM_FEATURES.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="card home-card">
            <h2>University profile setup</h2>
            <p className="profile-note">
              Each university is configured separately with isolated knowledge, policies, and analytics.
            </p>
            <div className="profile-switcher">
              {UNIVERSITY_PROFILES.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  className={`profile-btn ${selectedUniversityId === profile.id ? 'profile-btn-active' : ''}`}
                  onClick={() => setSelectedUniversityId(profile.id)}
                >
                  {profile.name}
                </button>
              ))}
            </div>
            <p className="phase-note">{selectedUniversity.note}</p>
            <label className="home-label" htmlFor="university-name">
              University Name
            </label>
            <input
              id="university-name"
              className="input"
              value={universityName}
              maxLength={40}
              onChange={(e) => setUniversityName(e.target.value || 'Northbridge University')}
            />

            <label className="home-label" htmlFor="university-logo">
              Logo Text
            </label>
            <input
              id="university-logo"
              className="input"
              value={logoText}
              maxLength={4}
              onChange={(e) => {
                const nextValue = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
                setLogoText(nextValue || 'NU');
              }}
            />

            <p className="home-label">Color Theme</p>
            <div className="theme-pills">
              {BRAND_THEMES.map((theme) => (
                <button
                  key={theme.id}
                  type="button"
                  className={`theme-pill ${selectedThemeId === theme.id ? 'theme-pill-active' : ''}`}
                  onClick={() => setSelectedThemeId(theme.id)}
                >
                  <span style={{ background: theme.primary }} />
                  <span style={{ background: theme.accent }} />
                  {theme.name}
                </button>
              ))}
            </div>
          </article>
        </section>

        <section className="card home-card">
          <h2>Public assistant preview</h2>
          <p className="home-subtitle">
            Click any question to preview public responses. Logged-in users then continue into personal
            learning tools and progress tracking.
          </p>
          <div className="question-grid">
            {PREAUTH_QUESTIONS.map((question) => (
              <button
                key={question.id}
                type="button"
                className="question-pill"
                onClick={() => handleQuestionClick(question)}
              >
                {question.label}
              </button>
            ))}
          </div>
        </section>
      </main>

      {!widgetOpen && (
        <button
          className="chat-bubble"
          type="button"
          aria-label="Open custom campus assistant preview"
          onClick={() => setWidgetOpen(true)}
        >
          <span>Open</span>
          <small>Campus LLM</small>
        </button>
      )}

      {widgetOpen && (
        <aside className="chat-widget" aria-label="Custom campus assistant widget preview">
          <header className="chat-header">
            <div className="chat-branding">
              <span className="chat-logo">{logoText || 'NU'}</span>
              <div>
                <h3>{universityName}</h3>
                <p>
                  {statusLabel}
                  {aiStatus.model ? ` | ${aiStatus.model}` : ''}
                </p>
              </div>
            </div>
            <button type="button" className="chat-close" onClick={() => setWidgetOpen(false)}>
              X
            </button>
          </header>

          {isOffline && (
            <div className="chat-offline-banner">
              {aiStatus.message || 'AI is currently unavailable. Offline guidance is still shown below.'}
            </div>
          )}

          <div className="chat-transcript" ref={transcriptRef}>
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`chat-message chat-${message.role}`}>
                {message.text}
              </div>
            ))}
          </div>

          <div className="chat-actions">
            {PREAUTH_QUESTIONS.map((question) => (
              <button
                key={question.id}
                type="button"
                className="chat-chip"
                onClick={() => handleQuestionClick(question)}
              >
                {question.label}
              </button>
            ))}
          </div>

          <div className="chat-footer">
            <button type="button" className="btn btn-primary" onClick={onStudentLogin}>
              Student Login to access full features
            </button>
          </div>
        </aside>
      )}
    </div>
  );
}
