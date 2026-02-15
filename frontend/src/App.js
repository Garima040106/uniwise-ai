import { useState, useEffect } from 'react';
import { getProfile, logout } from './services/api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Flashcards from './pages/Flashcards';
import Quiz from './pages/Quiz';
import Documents from './pages/Documents';
import AskAI from './pages/AskAI';

const navItems = [
  { id: 'dashboard', label: '🏠 Dashboard' },
  { id: 'askai', label: '🤖 Ask AI' },
  { id: 'flashcards', label: '🃏 Flashcards' },
  { id: 'quizzes', label: '📝 Quizzes' },
  { id: 'documents', label: '📄 Documents' },
];

export default function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('dashboard');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProfile()
      .then(res => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = async () => {
    await logout();
    setUser(null);
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '48px' }}>🎓</div>
        <p style={{ color: '#6c63ff', marginTop: '16px' }}>Loading Uniwise AI...</p>
      </div>
    </div>
  );

  if (!user) return <Login onLogin={(data) => setUser(data)} />;

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <div style={{
        width: '240px', background: '#1a1a2e', borderRight: '1px solid #2a2a4a',
        padding: '24px 0', display: 'flex', flexDirection: 'column',
        position: 'fixed', height: '100vh',
      }}>
        <div style={{ padding: '0 24px 24px', borderBottom: '1px solid #2a2a4a' }}>
          <h1 style={{ color: '#6c63ff', fontSize: '20px' }}>🎓 Uniwise AI</h1>
          <p style={{ color: '#8888aa', fontSize: '12px', marginTop: '4px' }}>
            {user.university || 'No university set'}
          </p>
        </div>

        <nav style={{ flex: 1, padding: '16px 0' }}>
          {navItems.map(item => (
            <button key={item.id}
              onClick={() => setPage(item.id)}
              style={{
                width: '100%', padding: '12px 24px', textAlign: 'left',
                background: page === item.id ? '#16213e' : 'transparent',
                border: 'none', color: page === item.id ? '#6c63ff' : '#8888aa',
                cursor: 'pointer', fontSize: '14px', fontWeight: page === item.id ? '600' : '400',
                borderLeft: page === item.id ? '3px solid #6c63ff' : '3px solid transparent',
                transition: 'all 0.2s',
              }}>
              {item.label}
            </button>
          ))}
        </nav>

        <div style={{ padding: '16px 24px', borderTop: '1px solid #2a2a4a' }}>
          <p style={{ color: '#8888aa', fontSize: '12px', marginBottom: '8px' }}>
            👤 {user.username}
          </p>
          <button className="btn btn-secondary" style={{ width: '100%' }}
            onClick={handleLogout}>Logout</button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ marginLeft: '240px', flex: 1, padding: '32px' }}>
        {page === 'dashboard' && <Dashboard user={user} />}
        {page === 'askai' && <AskAI />}
        {page === 'flashcards' && <Flashcards />}
        {page === 'quizzes' && <Quiz />}
        {page === 'documents' && <Documents />}
      </div>
    </div>
  );
}
