import { useState, useEffect } from 'react';
import { getDashboard, getAIStatus, getDocumentProgress } from '../services/api';

export default function Dashboard({ user }) {
  const [stats, setStats] = useState(null);
  const [aiStatus, setAiStatus] = useState({ status: 'checking' });
  const [docProgress, setDocProgress] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
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
      } else {
        console.error('Failed to fetch dashboard stats:', dashRes.reason);
      }

      if (aiRes.status === 'fulfilled') {
        setAiStatus(aiRes.value.data);
      } else {
        console.error('Failed to fetch AI status:', aiRes.reason);
        setAiStatus({
          status: 'unknown',
          message: 'Unable to fetch AI status.',
        });
      }

      if (docRes.status === 'fulfilled') {
        const docs = docRes.value.data || [];
        setDocProgress(docs);
        if (docs.length > 0) {
          setSelectedDocId(String(docs[0].document_id));
        }
      } else {
        console.error('Failed to fetch document progress:', docRes.reason);
      }

      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) return <div className="loading">Loading dashboard...</div>;

  const skillLevel = stats?.overall_skill_level || 0;
  const aiState = aiStatus?.status;
  const isOnline = aiState === 'online';
  const isOffline = aiState === 'offline';
  const statusColor = isOnline ? '#43e97b' : isOffline ? '#ff6584' : '#f5c542';
  const statusLabel = isOnline ? '● Online' : isOffline ? '● Offline' : '● Unknown';
  const selectedDoc = docProgress.find((d) => String(d.document_id) === String(selectedDocId)) || null;

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>
        👋 Welcome back, {user?.username}!
      </h2>

      {/* AI Status Banner */}
      <div className="card" style={{
        background: isOnline
          ? 'linear-gradient(135deg, #1a3a2a, #1a1a2e)'
          : isOffline
            ? 'linear-gradient(135deg, #3a1a2a, #1a1a2e)'
            : 'linear-gradient(135deg, #3a321a, #1a1a2e)',
        borderColor: statusColor,
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>🤖</span>
          <div>
            <strong>AI Engine: </strong>
            <span style={{ color: statusColor }}>
              {statusLabel}
            </span>
            <span style={{ color: '#8888aa', marginLeft: '12px', fontSize: '13px' }}>
              Model: {aiStatus?.model || 'Not reported'}
            </span>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <button
            className="btn"
            onClick={() => setActiveTab('overview')}
            style={{
              background: activeTab === 'overview' ? '#6c63ff' : '#1a1a2e',
              color: '#fff',
              border: activeTab === 'overview' ? 'none' : '1px solid #2f2f4d',
              padding: '8px 14px',
            }}
          >
            Overview
          </button>
          <button
            className="btn"
            onClick={() => setActiveTab('documents')}
            style={{
              background: activeTab === 'documents' ? '#6c63ff' : '#1a1a2e',
              color: '#fff',
              border: activeTab === 'documents' ? 'none' : '1px solid #2f2f4d',
              padding: '8px 14px',
            }}
          >
            Document Progress
          </button>
        </div>

        {activeTab === 'overview' && (
          <>
            <h3 style={{ marginBottom: '16px' }}>📊 Overall Skill Development</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ color: '#8888aa' }}>Academic Progress</span>
              <span style={{ color: '#6c63ff', fontWeight: 'bold' }}>{skillLevel}%</span>
            </div>
            <div style={{ background: '#0f0f1a', borderRadius: '8px', height: '16px', overflow: 'hidden' }}>
              <div style={{
                width: `${skillLevel}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #6c63ff, #43e97b)',
                borderRadius: '8px',
                transition: 'width 1s ease',
              }} />
            </div>
            <p style={{ color: '#8888aa', fontSize: '12px', marginTop: '8px', marginBottom: '16px' }}>
              Keep studying to increase your skill level!
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              {[
                { label: 'Flashcards Reviewed', value: stats?.total_flashcards_reviewed || 0, icon: '🃏' },
                { label: 'Quizzes Completed', value: stats?.total_quizzes_completed || 0, icon: '✅' },
                { label: 'Average Score', value: `${stats?.average_quiz_score || 0}%`, icon: '🎯' },
                { label: 'Study Hours', value: stats?.total_study_hours || 0, icon: '⏱️' },
              ].map((stat) => (
                <div key={stat.label} className="card" style={{ textAlign: 'center', marginBottom: 0 }}>
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>{stat.icon}</div>
                  <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#6c63ff' }}>{stat.value}</div>
                  <div style={{ color: '#8888aa', fontSize: '13px' }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </>
        )}

        {activeTab === 'documents' && (
          <div>
            <h3 style={{ marginBottom: '16px' }}>📚 Coverage by Document</h3>
            {docProgress.length === 0 ? (
              <p style={{ color: '#8888aa' }}>No documents available yet.</p>
            ) : (
              <>
                <label style={{ color: '#8888aa', fontSize: '13px' }}>Select Document</label>
                <select
                  className="input"
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  style={{ marginTop: '6px', marginBottom: '14px', maxWidth: '460px' }}
                >
                  {docProgress.map((doc) => (
                    <option key={doc.document_id} value={doc.document_id}>{doc.title}</option>
                  ))}
                </select>

                {selectedDoc && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ color: '#8888aa' }}>Estimated Content Coverage</span>
                      <span style={{ color: '#6c63ff', fontWeight: 'bold' }}>
                        {selectedDoc.progress_score}/100
                      </span>
                    </div>
                    <div style={{ background: '#0f0f1a', borderRadius: '8px', height: '16px', overflow: 'hidden' }}>
                      <div style={{
                        width: `${selectedDoc.progress_score}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #f5c542, #43e97b)',
                        borderRadius: '8px',
                        transition: 'width 1s ease',
                      }} />
                    </div>
                    <p style={{ color: '#8888aa', fontSize: '12px', marginTop: '10px' }}>
                      Question coverage: {selectedDoc.question_coverage.covered}/{selectedDoc.question_coverage.total}
                      {' '}• Flashcard coverage: {selectedDoc.flashcard_coverage.covered}/{selectedDoc.flashcard_coverage.total}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
