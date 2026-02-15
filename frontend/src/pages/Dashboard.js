import { useState, useEffect } from 'react';
import { getDashboard, getAIStatus } from '../services/api';

export default function Dashboard({ user }) {
  const [stats, setStats] = useState(null);
  const [aiStatus, setAiStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashRes, aiRes] = await Promise.all([
          getDashboard(),
          getAIStatus(),
        ]);
        setStats(dashRes.data);
        setAiStatus(aiRes.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="loading">Loading dashboard...</div>;

  const skillLevel = stats?.overall_skill_level || 0;

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>
        👋 Welcome back, {user?.username}!
      </h2>

      {/* AI Status Banner */}
      <div className="card" style={{
        background: aiStatus?.status === 'online'
          ? 'linear-gradient(135deg, #1a3a2a, #1a1a2e)'
          : 'linear-gradient(135deg, #3a1a2a, #1a1a2e)',
        borderColor: aiStatus?.status === 'online' ? '#43e97b' : '#ff6584',
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>🤖</span>
          <div>
            <strong>AI Engine: </strong>
            <span style={{ color: aiStatus?.status === 'online' ? '#43e97b' : '#ff6584' }}>
              {aiStatus?.status === 'online' ? '● Online' : '● Offline'}
            </span>
            <span style={{ color: '#8888aa', marginLeft: '12px', fontSize: '13px' }}>
              Model: {aiStatus?.model || 'llama3.2:3b'}
            </span>
          </div>
        </div>
      </div>

      {/* Overall Skill Bar */}
      <div className="card" style={{ marginBottom: '24px' }}>
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
        <p style={{ color: '#8888aa', fontSize: '12px', marginTop: '8px' }}>
          Keep studying to increase your skill level!
        </p>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        {[
          { label: 'Flashcards Reviewed', value: stats?.total_flashcards_reviewed || 0, icon: '🃏' },
          { label: 'Quizzes Completed', value: stats?.total_quizzes_completed || 0, icon: '✅' },
          { label: 'Average Score', value: `${stats?.average_quiz_score || 0}%`, icon: '🎯' },
          { label: 'Study Hours', value: stats?.total_study_hours || 0, icon: '⏱️' },
        ].map((stat) => (
          <div key={stat.label} className="card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>{stat.icon}</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#6c63ff' }}>{stat.value}</div>
            <div style={{ color: '#8888aa', fontSize: '13px' }}>{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
