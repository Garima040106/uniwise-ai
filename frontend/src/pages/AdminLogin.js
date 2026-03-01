import { useState } from 'react';
import { loginAdmin } from '../services/api';

export default function AdminLogin({ onLogin, onBack }) {
  const [form, setForm] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await loginAdmin(form);
      onLogin(res.data);
    } catch (err) {
      const apiError = err?.response?.data?.error || 'Invalid administration credentials.';
      setError(apiError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#0f0f1a' }}>
      <div style={{ width: '100%', maxWidth: '420px', padding: '16px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#6c63ff' }}>Administration Login</h1>
            {onBack && (
              <button type="button" className="btn btn-secondary" onClick={onBack}>
                Back
              </button>
            )}
          </div>
          <p style={{ color: '#8f97b6', marginBottom: '14px' }}>
            Access university-level controls, configuration, and system analytics.
          </p>

          <form onSubmit={handleSubmit}>
            <input
              className="input"
              placeholder="Admin username"
              value={form.username}
              onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
              required
            />
            <input
              className="input"
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
              required
            />
            {error && <p className="error">{error}</p>}
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In to Admin Workspace'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
