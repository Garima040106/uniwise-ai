import { useState } from 'react';
import { login } from '../services/api';

export default function Login({ onLogin }) {
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await login(form);
      onLogin(res.data);
    } catch (err) {
      setError('Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%)'
    }}>
      <div style={{ width: '100%', maxWidth: '400px', padding: '20px' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '8px' }}>🎓</div>
          <h1 style={{ color: '#6c63ff', fontSize: '28px', marginBottom: '4px' }}>Uniwise AI</h1>
          <p style={{ color: '#8888aa', marginBottom: '32px' }}>Your University AI Learning Assistant</p>

          <form onSubmit={handleSubmit}>
            <input
              className="input"
              placeholder="Username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
            />
            <input
              className="input"
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
            {error && <p className="error">{error}</p>}
            <button className="btn btn-primary" type="submit"
              style={{ width: '100%', padding: '12px', marginTop: '8px' }}
              disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
