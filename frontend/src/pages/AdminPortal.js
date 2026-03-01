import { useEffect, useMemo, useState } from 'react';
import AskAI from './AskAI';
import Documents from './Documents';
import Flashcards from './Flashcards';
import Quiz from './Quiz';
import {
  getAdminActivityLog,
  getAdminOverview,
  getAdminReports,
  getAdminStudentInsights,
} from '../services/api';
import './AdminPortal.css';

const ADMIN_TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'ai', label: 'Admin AI Copilot' },
  { id: 'content', label: 'Content Management' },
  { id: 'analytics', label: 'Student Analytics' },
  { id: 'assessments', label: 'Assessments' },
  { id: 'university', label: 'University Data' },
  { id: 'system', label: 'System Admin' },
  { id: 'reports', label: 'Reports' },
];

const FACULTY_SUPPORT_PROMPTS = [
  'How do I upload documents for a course?',
  'How do I create a quiz from uploaded content?',
  'How can I view student analytics quickly?',
  'Show platform usage tutorials for professors',
];

const CONTENT_MANAGEMENT_PROMPTS = [
  'How do I update admission requirements?',
  'How can I modify course catalog details?',
  'What is the process to edit campus policies?',
  'How do I update the event calendar?',
];

const TECHNICAL_PROMPTS = [
  'Troubleshoot failed flashcard generation',
  'Where can I access API documentation?',
  'How do I report a bug with logs?',
  'How do I submit a feature request?',
];

function formatPercentage(value) {
  const num = Number(value || 0);
  return `${Number.isFinite(num) ? num.toFixed(1) : '0.0'}%`;
}

export default function AdminPortal({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [workspaceView, setWorkspaceView] = useState('');
  const [quickPrompt, setQuickPrompt] = useState('');
  const [quickPromptVersion, setQuickPromptVersion] = useState(0);

  const [overview, setOverview] = useState(null);
  const [insights, setInsights] = useState(null);
  const [reports, setReports] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    const fetchAdminData = async () => {
      setLoadError('');
      const [overviewRes, insightsRes, reportsRes, logRes] = await Promise.allSettled([
        getAdminOverview(),
        getAdminStudentInsights(),
        getAdminReports(),
        getAdminActivityLog(),
      ]);

      if (overviewRes.status === 'fulfilled') {
        setOverview(overviewRes.value.data || {});
      } else {
        setLoadError('Unable to load complete admin overview data.');
      }

      if (insightsRes.status === 'fulfilled') {
        setInsights(insightsRes.value.data || {});
      }

      if (reportsRes.status === 'fulfilled') {
        setReports(reportsRes.value.data || {});
      }

      if (logRes.status === 'fulfilled') {
        setActivityLog(logRes.value.data?.recent_activity_log || []);
      } else if (overviewRes.status === 'fulfilled') {
        setActivityLog(overviewRes.value.data?.recent_activity || []);
      }

      setLoading(false);
    };

    fetchAdminData();
  }, []);

  const overviewStats = overview?.university_overview || {};
  const systemHealth = overview?.system_health || {};
  const classLevel = insights?.class_level || {};
  const individualStudents = insights?.individual_student_analytics || [];
  const atRiskStudents = insights?.at_risk_student_alerts || [];
  const reportUsage = reports?.platform_usage_reports || {};
  const reportEngagement = reports?.student_engagement_reports || {};
  const reportContent = reports?.content_effectiveness_reports || {};
  const reportAI = reports?.ai_performance_metrics || {};

  const roleLabel = useMemo(() => {
    if (user?.role === 'admin') return 'Super Admin / IT Admin';
    if (user?.role === 'professor') return 'Professor';
    return user?.role || 'Admin';
  }, [user]);

  const applyPrompt = (prompt) => {
    setQuickPrompt(prompt);
    setQuickPromptVersion((current) => current + 1);
  };

  if (loading) return <div className="loading">Loading administration portal...</div>;

  return (
    <div className="admin-portal-shell">
      <header className="admin-portal-header">
        <div>
          <h1>Administration Portal</h1>
          <p>
            Manage university knowledge, monitor student learning outcomes, and operate the Uniwise AI
            platform from one workspace.
          </p>
        </div>
        <div className="admin-header-actions">
          <span className="admin-role-pill">{roleLabel}</span>
          <button type="button" className="btn btn-secondary" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      <nav className="admin-tabs">
        {ADMIN_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`admin-tab-btn ${activeTab === tab.id ? 'admin-tab-btn-active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {loadError && (
        <div className="card">
          <p className="error">{loadError}</p>
        </div>
      )}

      {activeTab === 'dashboard' && (
        <section className="admin-section">
          <div className="admin-metric-grid">
            <article className="admin-metric-card">
              <p>Total students</p>
              <strong>{overviewStats.total_students ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Total documents</p>
              <strong>{overviewStats.total_documents_uploaded ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Total AI requests</p>
              <strong>{overviewStats.total_ai_requests ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Completed quizzes</p>
              <strong>{overviewStats.total_quizzes_completed ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Active students (7d)</p>
              <strong>{overviewStats.active_students_last_7_days ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Class avg score</p>
              <strong>{formatPercentage(overviewStats.class_average_quiz_score)}</strong>
            </article>
          </div>

          <div className="admin-grid-two">
            <article className="card">
              <h3>System Health Status</h3>
              <p className="admin-muted">
                Status: <strong>{systemHealth.status || 'unknown'}</strong>
              </p>
              <p className="admin-muted">
                Model: <strong>{systemHealth.model || 'not reported'}</strong>
              </p>
              <p className="admin-muted">{systemHealth.message || 'No additional status message.'}</p>
            </article>

            <article className="card">
              <h3>Most Asked Questions</h3>
              <ul className="admin-list">
                {(overview?.most_asked_questions || []).map((item) => (
                  <li key={`${item.question}-${item.count}`}>
                    <span>{item.question}</span>
                    <strong>{item.count}</strong>
                  </li>
                ))}
                {(overview?.most_asked_questions || []).length === 0 && (
                  <li>
                    <span>No question trend data yet.</span>
                  </li>
                )}
              </ul>
            </article>
          </div>

          <article className="card">
            <h3>Recent Activity Log</h3>
            <ul className="admin-activity-list">
              {activityLog.slice(0, 12).map((item, idx) => (
                <li key={`${item.type}-${idx}`}>
                  <span>{item.message}</span>
                  <small>{new Date(item.timestamp).toLocaleString()}</small>
                </li>
              ))}
              {activityLog.length === 0 && <li>No recent activity available.</li>}
            </ul>
          </article>
        </section>
      )}

      {activeTab === 'ai' && (
        <section className="admin-section">
          <div className="admin-grid-three">
            <article className="card">
              <h3>Faculty Support</h3>
              <div className="admin-chip-wrap">
                {FACULTY_SUPPORT_PROMPTS.map((prompt) => (
                  <button key={prompt} type="button" className="admin-chip" onClick={() => applyPrompt(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </article>

            <article className="card">
              <h3>University Content</h3>
              <div className="admin-chip-wrap">
                {CONTENT_MANAGEMENT_PROMPTS.map((prompt) => (
                  <button key={prompt} type="button" className="admin-chip" onClick={() => applyPrompt(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </article>

            <article className="card">
              <h3>Technical Queries</h3>
              <div className="admin-chip-wrap">
                {TECHNICAL_PROMPTS.map((prompt) => (
                  <button key={prompt} type="button" className="admin-chip" onClick={() => applyPrompt(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </article>
          </div>

          <div className="card">
            <AskAI presetQuestion={quickPrompt} presetVersion={quickPromptVersion} />
          </div>
        </section>
      )}

      {activeTab === 'content' && (
        <section className="admin-section">
          <div className="admin-grid-two">
            <article className="card">
              <h3>Document Management</h3>
              <ul className="admin-bullet-list">
                <li>Upload and organize course materials by course/subject/topic</li>
                <li>Metadata updates, visibility settings, and RAG-safe deletion</li>
                <li>Bulk upload, version replacement, and pre-publish review workflows</li>
              </ul>
              <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('documents')}>
                Open Document Workspace
              </button>
            </article>

            <article className="card">
              <h3>AI Content Generation</h3>
              <ul className="admin-bullet-list">
                <li>Generate flashcards, quizzes, study guides, and practice questions</li>
                <li>Review/edit AI content before publishing to students</li>
                <li>Regenerate when quality is unsatisfactory</li>
              </ul>
              <div className="admin-action-row">
                <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('flashcards')}>
                  Open Flashcards
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('quiz')}>
                  Open Quiz Builder
                </button>
              </div>
            </article>
          </div>

          <article className="card">
            <h3>Course Setup</h3>
            <div className="admin-grid-three">
              <div className="admin-mini-card">
                <strong>Create new courses</strong>
                <p>Define course identity, academic term, and ownership.</p>
              </div>
              <div className="admin-mini-card">
                <strong>Roster management</strong>
                <p>Add/remove students, map cohorts, and assign course access.</p>
              </div>
              <div className="admin-mini-card">
                <strong>Learning objectives</strong>
                <p>Set outcomes, upload syllabus, and align assessments.</p>
              </div>
            </div>
          </article>

          {workspaceView === 'documents' && (
            <div className="card">
              <Documents />
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
        </section>
      )}

      {activeTab === 'analytics' && (
        <section className="admin-section">
          <div className="admin-grid-two">
            <article className="card">
              <h3>Class-Level Analytics</h3>
              <ul className="admin-bullet-list">
                <li>Class average quiz score: {formatPercentage(classLevel.class_average_quiz_scores)}</li>
                <li>
                  Study hours logged: {classLevel.engagement_metrics?.study_hours_logged || 0}h
                </li>
                <li>
                  Questions asked: {classLevel.engagement_metrics?.total_questions_asked || 0}
                </li>
                <li>
                  Active students (30d): {classLevel.engagement_metrics?.active_students_last_30_days || 0}
                </li>
              </ul>
            </article>

            <article className="card">
              <h3>Topic Difficulty Heatmap</h3>
              <div className="admin-heatmap">
                {(classLevel.topic_difficulty_heatmap || []).map((item) => (
                  <div key={item.topic}>
                    <div className="admin-heatmap-head">
                      <span>{item.topic}</span>
                      <strong>{item.difficulty_index}%</strong>
                    </div>
                    <div className="admin-progress-bar">
                      <div style={{ width: `${Math.min(100, item.difficulty_index)}%` }} />
                    </div>
                  </div>
                ))}
                {(classLevel.topic_difficulty_heatmap || []).length === 0 && (
                  <p className="admin-muted">No topic heatmap data yet.</p>
                )}
              </div>
            </article>
          </div>

          <div className="admin-grid-two">
            <article className="card">
              <h3>Document Usage Statistics</h3>
              <ul className="admin-list">
                {(classLevel.document_usage_statistics || []).map((item) => (
                  <li key={item.document_id}>
                    <span>{item.title}</span>
                    <strong>{item.usage_score}</strong>
                  </li>
                ))}
                {(classLevel.document_usage_statistics || []).length === 0 && (
                  <li>
                    <span>No usage data available yet.</span>
                  </li>
                )}
              </ul>
            </article>

            <article className="card">
              <h3>Intervention Tools</h3>
              <div className="admin-action-row">
                <button type="button" className="btn btn-secondary">Send class announcement</button>
                <button type="button" className="btn btn-secondary">Message individual student</button>
                <button type="button" className="btn btn-secondary">Recommend resources</button>
                <button type="button" className="btn btn-secondary">Export analytics CSV</button>
              </div>
            </article>
          </div>

          <article className="card">
            <h3>Individual Student Analytics</h3>
            <div className="admin-student-table">
              <div className="admin-student-head">
                <span>Student</span>
                <span>Avg Score</span>
                <span>Study Hours</span>
                <span>Weak Area</span>
                <span>Engagement</span>
              </div>
              {individualStudents.slice(0, 20).map((student) => (
                <div key={`${student.student_id}-${student.username}`} className="admin-student-row">
                  <span>{student.username}</span>
                  <span>{formatPercentage(student.quiz_scores_average)}</span>
                  <span>{student.study_hours_logged}</span>
                  <span>{student.weak_area}</span>
                  <span>{student.engagement_score}</span>
                </div>
              ))}
              {individualStudents.length === 0 && (
                <p className="admin-muted">No student analytics available yet.</p>
              )}
            </div>
          </article>

          <article className="card">
            <h3>At-Risk Student Alerts</h3>
            <ul className="admin-list">
              {atRiskStudents.map((item) => (
                <li key={`${item.student_id}-${item.username}`}>
                  <span>
                    {item.username} ({item.student_id}) - {item.reason}
                  </span>
                </li>
              ))}
              {atRiskStudents.length === 0 && (
                <li>
                  <span>No at-risk alerts right now.</span>
                </li>
              )}
            </ul>
          </article>
        </section>
      )}

      {activeTab === 'assessments' && (
        <section className="admin-section">
          <div className="admin-grid-two">
            <article className="card">
              <h3>Quiz & Assessment Management</h3>
              <ul className="admin-bullet-list">
                <li>Create manual or AI-assisted quizzes</li>
                <li>Set time limits, due dates, and course assignments</li>
                <li>Review submissions and support short-answer grading workflows</li>
                <li>Export quiz results for accreditation and audits</li>
              </ul>
              <button type="button" className="btn btn-secondary" onClick={() => setWorkspaceView('quiz')}>
                Open Quiz Workspace
              </button>
            </article>

            <article className="card">
              <h3>Assessment Controls</h3>
              <div className="admin-grid-three">
                <div className="admin-mini-card">
                  <strong>Assignment targeting</strong>
                  <p>Assign assessments by course, section, or cohort.</p>
                </div>
                <div className="admin-mini-card">
                  <strong>Time & due policy</strong>
                  <p>Configure window rules and late submission behavior.</p>
                </div>
                <div className="admin-mini-card">
                  <strong>Result exports</strong>
                  <p>Download submissions for Excel/PDF workflows.</p>
                </div>
              </div>
            </article>
          </div>

          {workspaceView === 'quiz' && (
            <div className="card">
              <Quiz />
            </div>
          )}
        </section>
      )}

      {activeTab === 'university' && (
        <section className="admin-section">
          <div className="admin-grid-two">
            <article className="card">
              <h3>University Information Management</h3>
              <ul className="admin-bullet-list">
                <li>Admission info, faculty directory, and facilities data</li>
                <li>Academic calendar, event listings, FAQ, and policy database</li>
                <li>Centralized updates for student-facing assistant responses</li>
              </ul>
            </article>

            <article className="card">
              <h3>Chatbot Training Controls</h3>
              <ul className="admin-bullet-list">
                <li>Upload policy and compliance documents</li>
                <li>Add FAQ pairs and default fallback responses</li>
                <li>Review and flag low-quality answers for retraining queue</li>
              </ul>
            </article>
          </div>
        </section>
      )}

      {activeTab === 'system' && (
        <section className="admin-section">
          <div className="admin-grid-two">
            <article className="card">
              <h3>System Administration</h3>
              <ul className="admin-bullet-list">
                <li>User management and role assignment workflows</li>
                <li>Security policy controls: password policy and 2FA defaults</li>
                <li>Rate limits, model settings, API key management</li>
                <li>Backup/restore, logs, and server monitoring</li>
              </ul>
            </article>

            <article className="card">
              <h3>Recent Technical Activity</h3>
              <ul className="admin-activity-list">
                {activityLog.slice(0, 10).map((item, idx) => (
                  <li key={`sys-${idx}`}>
                    <span>{item.message}</span>
                    <small>{new Date(item.timestamp).toLocaleString()}</small>
                  </li>
                ))}
                {activityLog.length === 0 && <li>No system activity found.</li>}
              </ul>
            </article>
          </div>
        </section>
      )}

      {activeTab === 'reports' && (
        <section className="admin-section">
          <div className="admin-grid-three">
            <article className="admin-metric-card">
              <p>Daily active students</p>
              <strong>{reportUsage.daily_active_students ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Weekly active students</p>
              <strong>{reportUsage.weekly_active_students ?? 0}</strong>
            </article>
            <article className="admin-metric-card">
              <p>Monthly active students</p>
              <strong>{reportUsage.monthly_active_students ?? 0}</strong>
            </article>
          </div>

          <div className="admin-grid-two">
            <article className="card">
              <h3>Student Engagement Report</h3>
              <ul className="admin-bullet-list">
                <li>Avg study hours/student: {reportEngagement.average_study_hours_per_student ?? 0}</li>
                <li>Quiz completions (30d): {reportEngagement.quiz_completion_count_30_days ?? 0}</li>
                <li>Questions asked (30d): {reportEngagement.questions_asked_30_days ?? 0}</li>
              </ul>
            </article>

            <article className="card">
              <h3>AI Performance Metrics</h3>
              <ul className="admin-bullet-list">
                <li>Request success rate: {formatPercentage(reportAI.request_success_rate)}</li>
                <li>Avg processing time: {reportAI.average_processing_time_seconds ?? 0}s</li>
                <li>Total requests: {reportAI.total_requests ?? 0}</li>
              </ul>
            </article>
          </div>

          <article className="card">
            <h3>Content Effectiveness</h3>
            <ul className="admin-list">
              {(reportContent.top_helpful_documents || []).map((doc) => (
                <li key={`${doc.title}-${doc.usage_count}`}>
                  <span>{doc.title}</span>
                  <strong>{doc.usage_count}</strong>
                </li>
              ))}
              {(reportContent.top_helpful_documents || []).length === 0 && (
                <li>
                  <span>No content effectiveness data yet.</span>
                </li>
              )}
            </ul>
            <div className="admin-action-row">
              <button type="button" className="btn btn-secondary">Export PDF report</button>
              <button type="button" className="btn btn-secondary">Export Excel report</button>
            </div>
          </article>
        </section>
      )}
    </div>
  );
}
