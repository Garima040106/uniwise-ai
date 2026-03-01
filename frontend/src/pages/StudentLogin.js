import { useEffect, useState } from 'react';
import {
  forgotPassword,
  getSSOProviders,
  getUniversities,
  loginStudent,
  register,
  startSSO,
  verifyTwoFactor,
} from '../services/api';
import './StudentLogin.css';

export default function StudentLogin({ onLogin, onBack }) {
  const [form, setForm] = useState({ studentId: '', password: '', twoFactorCode: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [twoFactorRequired, setTwoFactorRequired] = useState(false);
  const [twoFactorChallengeId, setTwoFactorChallengeId] = useState('');

  const [showRegister, setShowRegister] = useState(false);
  const [universities, setUniversities] = useState([]);
  const [registering, setRegistering] = useState(false);
  const [registerForm, setRegisterForm] = useState({
    student_id: '',
    username: '',
    email: '',
    password: '',
    university_id: '',
    year_of_study: 1,
    field_of_study: '',
    two_factor_enabled: false,
  });

  const [ssoProviders, setSsoProviders] = useState([]);
  const [selectedSsoProvider, setSelectedSsoProvider] = useState('university-sso');

  useEffect(() => {
    getUniversities()
      .then((res) => setUniversities(res.data || []))
      .catch(() => setUniversities([]));

    getSSOProviders()
      .then((res) => {
        const providers = res.data?.providers || [];
        setSsoProviders(providers);
        if (providers.length > 0) {
          setSelectedSsoProvider(providers[0].id);
        }
      })
      .catch(() => setSsoProviders([]));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setInfo('');

    try {
      if (twoFactorRequired) {
        if (!form.twoFactorCode.trim()) {
          setLoading(false);
          setError('Enter the 2FA code sent to your registered email.');
          return;
        }
        const verifyRes = await verifyTwoFactor({
          challenge_id: twoFactorChallengeId,
          two_factor_code: form.twoFactorCode.trim(),
        });
        onLogin(verifyRes.data);
        return;
      }

      const res = await loginStudent({
        student_id: form.studentId.trim(),
        password: form.password,
      });

      if (res.data?.two_factor_required) {
        setTwoFactorRequired(true);
        setTwoFactorChallengeId(res.data.challenge_id || '');
        setInfo(
          res.data.debug_code
            ? `2FA required. Debug code: ${res.data.debug_code}`
            : '2FA required. A verification code was sent to your registered email.'
        );
        return;
      }

      onLogin(res.data);
    } catch (err) {
      const apiError = err?.response?.data?.error || 'Invalid student ID or password.';
      setError(Array.isArray(apiError) ? apiError.join(' ') : apiError);
    } finally {
      setLoading(false);
    }
  };

  const handleStudentRegistration = async (e) => {
    e.preventDefault();
    setRegistering(true);
    setError('');
    setInfo('');
    try {
      await register({
        ...registerForm,
        username: registerForm.username || registerForm.student_id,
      });
      setInfo('Registration successful. You can now login with your Student ID and password.');
      setForm((prev) => ({ ...prev, studentId: registerForm.student_id }));
      setShowRegister(false);
    } catch (err) {
      const apiError = err?.response?.data?.error || 'Registration failed. Please verify details and retry.';
      setError(Array.isArray(apiError) ? apiError.join(' ') : apiError);
    } finally {
      setRegistering(false);
    }
  };

  const handleForgotPassword = async () => {
    setError('');
    setInfo('');
    const identifier = form.studentId.trim();
    if (!identifier) {
      setError('Enter student ID or email first, then click Forgot Password.');
      return;
    }
    try {
      const res = await forgotPassword({ identifier });
      const debugLink = res.data?.debug_reset_link;
      setInfo(
        debugLink
          ? `Password reset initiated. Debug reset link: ${debugLink}`
          : 'If your account exists, reset instructions were sent.'
      );
    } catch (err) {
      setError('Could not start password recovery right now.');
    }
  };

  const handleSSO = async () => {
    setError('');
    setInfo('');
    try {
      const res = await startSSO({
        provider: selectedSsoProvider || 'university-sso',
        redirect_uri: window.location.origin,
      });
      setInfo(
        `${res.data?.message || 'SSO scaffold started.'} Auth URL: ${res.data?.auth_url || 'N/A'}`
      );
    } catch (err) {
      const apiError = err?.response?.data?.error || 'Unable to start SSO flow.';
      setError(apiError);
    }
  };

  const ssoButtonLabel =
    selectedSsoProvider === 'google'
      ? 'Continue with Google'
      : selectedSsoProvider === 'microsoft'
        ? 'Continue with Microsoft'
        : 'Continue with University SSO';

  return (
    <div className="student-auth-shell">
      <div className="student-auth-overlay" aria-hidden="true" />
      <main className="student-auth-content">
        <section className="card student-auth-panel">
          <div className="student-auth-head">
            {onBack && (
              <button type="button" className="btn btn-secondary" onClick={onBack}>
                Back
              </button>
            )}
            <h1>Student Login</h1>
            <p>Sign in to access your AI learning workspace and progress dashboard.</p>
          </div>

          <form onSubmit={handleSubmit}>
            <label className="student-auth-label" htmlFor="student-id">
              Student ID
            </label>
            <input
              id="student-id"
              className="input"
              value={form.studentId}
              onChange={(e) => setForm((prev) => ({ ...prev, studentId: e.target.value }))}
              placeholder="Enter student ID"
              required
            />

            {!twoFactorRequired && (
              <>
                <label className="student-auth-label" htmlFor="student-password">
                  Password
                </label>
                <input
                  id="student-password"
                  type="password"
                  className="input"
                  value={form.password}
                  onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter password"
                  required
                />
              </>
            )}

            {twoFactorRequired && (
              <>
                <label className="student-auth-label" htmlFor="two-factor-code">
                  Two-factor code
                </label>
                <input
                  id="two-factor-code"
                  className="input"
                  value={form.twoFactorCode}
                  onChange={(e) => setForm((prev) => ({ ...prev, twoFactorCode: e.target.value }))}
                  placeholder="Enter 2FA code"
                  required
                />
              </>
            )}

            <div className="student-auth-row">
              <button type="button" className="student-link-btn" onClick={handleForgotPassword}>
                Forgot Password?
              </button>
            </div>

            {error && <p className="error">{error}</p>}
            {info && <p className="success">{info}</p>}

            <button type="submit" className="btn btn-primary student-auth-submit" disabled={loading}>
              {loading ? 'Processing...' : twoFactorRequired ? 'Verify and Sign In' : 'Student Sign In'}
            </button>

            <div className="student-sso-row">
              <select
                className="input"
                value={selectedSsoProvider}
                onChange={(e) => setSelectedSsoProvider(e.target.value)}
              >
                {ssoProviders.length === 0 && <option value="university-sso">University SSO</option>}
                {ssoProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
              <button type="button" className="btn btn-secondary student-auth-submit" onClick={handleSSO}>
                {ssoButtonLabel}
              </button>
            </div>
          </form>

          <div className="student-auth-divider" />

          <div className="student-register-head">
            <h2>New student?</h2>
            <button
              type="button"
              className="student-link-btn"
              onClick={() => setShowRegister((prev) => !prev)}
            >
              {showRegister ? 'Hide registration' : 'Register now'}
            </button>
          </div>

          {showRegister && (
            <form className="student-register-form" onSubmit={handleStudentRegistration}>
              <input
                className="input"
                placeholder="Student ID"
                value={registerForm.student_id}
                onChange={(e) => setRegisterForm((prev) => ({ ...prev, student_id: e.target.value }))}
                required
              />
              <input
                className="input"
                placeholder="Username (optional)"
                value={registerForm.username}
                onChange={(e) => setRegisterForm((prev) => ({ ...prev, username: e.target.value }))}
              />
              <input
                className="input"
                type="email"
                placeholder="University email"
                value={registerForm.email}
                onChange={(e) => setRegisterForm((prev) => ({ ...prev, email: e.target.value }))}
                required
              />
              <input
                className="input"
                type="password"
                placeholder="Create password"
                value={registerForm.password}
                onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))}
                required
              />
              <select
                className="input"
                value={registerForm.university_id}
                onChange={(e) => setRegisterForm((prev) => ({ ...prev, university_id: e.target.value }))}
              >
                <option value="">Select university</option>
                {universities.map((university) => (
                  <option key={university.id} value={university.id}>
                    {university.name}
                  </option>
                ))}
              </select>
              <input
                className="input"
                placeholder="Field of study"
                value={registerForm.field_of_study}
                onChange={(e) => setRegisterForm((prev) => ({ ...prev, field_of_study: e.target.value }))}
              />
              <select
                className="input"
                value={registerForm.year_of_study}
                onChange={(e) =>
                  setRegisterForm((prev) => ({ ...prev, year_of_study: Number(e.target.value) }))
                }
              >
                {[1, 2, 3, 4, 5].map((year) => (
                  <option key={year} value={year}>
                    Year {year}
                  </option>
                ))}
              </select>
              <label className="student-auth-check">
                <input
                  type="checkbox"
                  checked={registerForm.two_factor_enabled}
                  onChange={(e) =>
                    setRegisterForm((prev) => ({ ...prev, two_factor_enabled: e.target.checked }))
                  }
                />
                Enable two-factor authentication for this account
              </label>
              <button className="btn btn-primary student-auth-submit" type="submit" disabled={registering}>
                {registering ? 'Creating account...' : 'Create Student Account'}
              </button>
            </form>
          )}
        </section>
      </main>
    </div>
  );
}
