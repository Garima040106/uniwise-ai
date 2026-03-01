import { useEffect, useMemo, useState } from 'react';
import { getAIStatus, getDashboard, getDocumentProgress } from '../services/api';
import AskAI from './AskAI';
import Flashcards from './Flashcards';
import Quiz from './Quiz';
import Documents from './Documents';
import './StudentPortal.css';

const STUDENT_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'ai', label: 'AI Chatbot' },
  { id: 'learning', label: 'Learning Tools' },
  { id: 'progress', label: 'Progress Tracking' },
  { id: 'extras', label: 'More Features' },
];

const UPCOMING_DEADLINES = [
  { title: 'Add/Drop deadline', date: 'Sept 12' },
  { title: 'Mid-sem exam registration', date: 'Sept 18' },
  { title: 'Financial aid update window', date: 'Sept 23' },
];

const QUICK_AI_PROMPTS = [
  'Summarize this unit in simple points',
  'What should I focus on for my next quiz?',
  'How do I complete course registration?',
  'Show upcoming deadlines for this month',
  'How can I request my transcript?',
  'Give me a revision plan for this week',
];

export default function StudentPortal({ user, onLogout }) {
  const [activeSection, setActiveSection] = useState('dashboard');
  const [workspaceView, setWorkspaceView] = useState('');
  const [quickPrompt, setQuickPrompt] = useState('');
  const [quickPromptVersion, setQuickPromptVersion] = useState(0);
  const [stats, setStats] = useState(null);
  const [aiStatus, setAiStatus] = useState({ status: 'checking' });
  const [docProgress, setDocProgress] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const [dashRes, aiRes, docRes] = await Promise.allSettled([
        getDashboard(),
        getAIStatus(),
        getDocumentProgress(),
      ]);

      if (dashRes.status === 'fulfilled') {
        setStats(dashRes.value.data);
      }
      if (aiRes.status === 'fulfilled') {
        setAiStatus(aiRes.value.data || { status: 'unknown' });
      } else {
        setAiStatus({ status: 'unknown', message: 'Unable to fetch AI status.' });
      }
      if (docRes.status === 'fulfilled') {
        setDocProgress(docRes.value.data || []);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  const skillLevel = stats?.overall_skill_level || 0;
  const studyHours = stats?.total_study_hours || 0;
  const quizzesCompleted = stats?.total_quizzes_completed || 0;
  const averageScore = stats?.average_quiz_score || 0;
  const retentionRate = useMemo(
    () => Math.min(100, Math.max(42, Math.round(skillLevel * 0.75 + 20))),
    [skillLevel]
  );
  const streakDays = useMemo(
    () => Math.max(1, Math.round((studyHours + quizzesCompleted) / 3)),
    [studyHours, quizzesCompleted]
  );

  const recentActivity = [
    `Completed ${quizzesCompleted} quizzes so far`,
    `Current average quiz score is ${averageScore}%`,
    `Reviewed ${stats?.total_flashcards_reviewed || 0} flashcards`,
  ];

  if (loading) return <div className="loading">Loading student portal...</div>;

  return (
    <div className="student-portal-shell">
      <header className="student-portal-top">
        <div>
          <h1>Student Portal</h1>
          <p>
            Welcome, {user?.username}. Access AI study support, learning tools, and progress insights in
            one place.
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={onLogout}>
          Logout
        </button>
      </header>

      <nav className="student-portal-nav">
        {STUDENT_SECTIONS.map((section) => (
          <button
            key={section.id}
            type="button"
            className={`student-nav-btn ${activeSection === section.id ? 'student-nav-btn-active' : ''}`}
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
          </button>
        ))}
      </nav>

      {activeSection === 'dashboard' && (
        <section className="student-portal-section">
          <div className="card">
            <h2>Welcome back, {user?.username}</h2>
            <p className="student-muted">
              AI model status: {aiStatus?.status || 'unknown'} | {aiStatus?.model || 'not reported'}
            </p>
            <div className="student-stats-grid">
              <div className="student-stat">
                <strong>{studyHours}</strong>
                <span>Study hours</span>
              </div>
              <div className="student-stat">
                <strong>{quizzesCompleted}</strong>
                <span>Quizzes completed</span>
              </div>
              <div className="student-stat">
                <strong>{skillLevel}%</strong>
                <span>Skill level</span>
              </div>
            </div>
          </div>

          <div className="student-grid-two">
            <article className="card">
              <h3>Upcoming deadlines</h3>
              <ul className="student-list">
                {UPCOMING_DEADLINES.map((item) => (
                  <li key={item.title}>
                    <span>{item.title}</span>
                    <strong>{item.date}</strong>
                  </li>
                ))}
              </ul>
            </article>

            <article className="card">
              <h3>Recent activity feed</h3>
              <ul className="student-feed">
                {recentActivity.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>

          <article className="card">
            <h3>Quick actions</h3>
            <div className="student-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setActiveSection('ai');
                }}
              >
                Ask AI
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setActiveSection('learning');
                  setWorkspaceView('flashcards');
                }}
              >
                Review Flashcards
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setActiveSection('learning');
                  setWorkspaceView('quiz');
                }}
              >
                Take Quiz
              </button>
            </div>
          </article>
        </section>
      )}

      {activeSection === 'ai' && (
        <section className="student-portal-section">
          <article className="card student-ai-intro">
            <div>
              <h3>Ask once, get support across academics and campus tasks</h3>
              <p className="student-muted">
                Use one assistant for study help, university services, admin requests, and your personal
                learning progress.
              </p>
              <p className="student-muted">
                Status: {aiStatus?.status || 'unknown'} {aiStatus?.model ? `| ${aiStatus.model}` : ''}
              </p>
            </div>
            <div className="student-prompt-chips">
              {QUICK_AI_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="student-prompt-chip"
                  onClick={() => {
                    setQuickPrompt(prompt);
                    setQuickPromptVersion((current) => current + 1);
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </article>
          <div className="card">
            <AskAI presetQuestion={quickPrompt} presetVersion={quickPromptVersion} />
          </div>
        </section>
      )}

      {activeSection === 'learning' && (
        <section className="student-portal-section">
          <div className="student-grid-two">
            <article className="card">
              <h3>Flashcards</h3>
              <p className="student-muted">
                Generate cards from your docs, revise with spaced repetition, and keep sets organized by
                course.
              </p>
              <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('flashcards')}>
                Open Flashcards Workspace
              </button>
            </article>

            <article className="card">
              <h3>Quizzes</h3>
              <p className="student-muted">
                Practice or exam mode quizzes with adaptive difficulty, score history, and retake support.
              </p>
              <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('quiz')}>
                Open Quiz Workspace
              </button>
            </article>
          </div>

          <div className="student-grid-two">
            <article className="card">
              <h3>Study Materials</h3>
              <p className="student-muted">
                Access uploaded course files quickly and open focused document search when needed.
              </p>
              <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('documents')}>
                Open Documents Workspace
              </button>
            </article>

            <article className="card">
              <h3>Exam Prep</h3>
              <p className="student-muted">
                Use AI to build a short prep plan, surface weak topics, and create targeted practice.
              </p>
              <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('ask')}>
                Open AI Prep Assistant
              </button>
            </article>
          </div>

          {workspaceView === 'ask' && (
            <div className="card">
              <AskAI />
            </div>
          )}
          {workspaceView === 'flashcards' && (
            <div className="card">
              <Flashcards />
            </div>
          )}
          {workspaceView === 'quiz' && (
            <div className="card">
              <Quiz />
            </div>
          )}
          {workspaceView === 'documents' && (
            <div className="card">
              <Documents />
            </div>
          )}
        </section>
      )}

      {activeSection === 'progress' && (
        <section className="student-portal-section">
          <article className="card">
            <h3>Overall skill development</h3>
            <div className="student-progress-head">
              <span>Skill level</span>
              <strong>{skillLevel}%</strong>
            </div>
            <div className="student-progress-bar">
              <div style={{ width: `${skillLevel}%` }} />
            </div>
          </article>

          <article className="card">
            <h3>Course-wise progress breakdown</h3>
            <div className="student-course-progress">
              {docProgress.length === 0 && <p className="student-muted">No course progress data yet.</p>}
              {docProgress.map((item) => (
                <div key={item.document_id} className="student-course-item">
                  <div className="student-progress-head">
                    <span>{item.title}</span>
                    <strong>{item.progress_score}%</strong>
                  </div>
                  <div className="student-progress-bar">
                    <div style={{ width: `${item.progress_score}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <div className="student-grid-three">
            <article className="card">
              <h3>Learning curve</h3>
              <p className="student-muted">Performance trend improves with consistent quiz and review sessions.</p>
              <div className="student-curve">
                <span style={{ height: '20%' }} />
                <span style={{ height: '40%' }} />
                <span style={{ height: '56%' }} />
                <span style={{ height: '68%' }} />
                <span style={{ height: '80%' }} />
              </div>
            </article>

            <article className="card">
              <h3>Core metrics</h3>
              <ul className="student-feature-list">
                <li>Study hours: {studyHours} (daily/weekly/monthly view)</li>
                <li>Quiz score trend: {averageScore}% average</li>
                <li>Flashcard retention rate: {retentionRate}%</li>
                <li>Study streak counter: {streakDays} days</li>
              </ul>
            </article>

            <article className="card">
              <h3>Achievements and badges</h3>
              <ul className="student-feature-list">
                <li>Consistency badge: Study streak maintained</li>
                <li>Quiz mastery badge: Above 80% score trend</li>
                <li>Coverage badge: High document completion</li>
              </ul>
            </article>
          </div>
        </section>
      )}

      {activeSection === 'extras' && (
        <section className="student-portal-section">
          <div className="student-grid-two">
            <article className="card">
              <h3>Calendar</h3>
              <p className="student-muted">Assignments, exams, and events in a single academic timeline.</p>
            </article>
            <article className="card">
              <h3>Notifications</h3>
              <p className="student-muted">
                Due flashcards, new quizzes, professor announcements, and critical reminders.
              </p>
            </article>
            <article className="card">
              <h3>Profile Settings</h3>
              <p className="student-muted">
                Update profile, learning pace, and notification preferences with role-based controls.
              </p>
            </article>
            <article className="card">
              <h3>Help Center</h3>
              <p className="student-muted">
                FAQs, tutorials, and support contacts for platform guidance and issue resolution.
              </p>
            </article>
          </div>
        </section>
      )}
    </div>
  );
}
