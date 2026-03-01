import { useState, useEffect } from 'react';
import { getProfile, logout } from './services/api';
import PreAuthHub from './pages/PreAuthHub';
import HomePage from './pages/HomePage';
import StudentLogin from './pages/StudentLogin';
import AdminLogin from './pages/AdminLogin';
import StudentPortal from './pages/StudentPortal';
import AdminPortal from './pages/AdminPortal';

const PREAUTH_VIEWS = ['hub', 'custom', 'student-login', 'admin-login'];

const getPreAuthViewFromHash = () => {
  const hashValue = window.location.hash.replace('#', '').trim();
  return PREAUTH_VIEWS.includes(hashValue) ? hashValue : 'hub';
};

export default function App() {
  const [user, setUser] = useState(null);
  const [preAuthView, setPreAuthView] = useState(getPreAuthViewFromHash);
  const [portalMode, setPortalMode] = useState('admin');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProfile()
      .then((res) => {
        const profile = res.data;
        setUser(profile);
        const role = profile?.role;
        setPortalMode(role === 'student' ? 'student' : 'admin');
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const handleHashChange = () => {
      if (!user) {
        setPreAuthView(getPreAuthViewFromHash());
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [user]);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      const current = window.location.hash.replace('#', '').trim();
      if (current !== preAuthView) {
        window.history.pushState({}, '', `#${preAuthView}`);
      }
    } else if (window.location.hash) {
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [loading, user, preAuthView]);

  const goToHub = () => {
    setPreAuthView('hub');
  };

  const openPreAuthView = (view) => {
    if (PREAUTH_VIEWS.includes(view)) {
      setPreAuthView(view);
    }
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setPortalMode('admin');
    goToHub();
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '48px' }}>🎓</div>
        <p style={{ color: '#6c63ff', marginTop: '16px' }}>Loading Uniwise AI...</p>
      </div>
    </div>
  );

  if (!user) {
    if (preAuthView === 'custom') {
      return (
        <HomePage
          onBack={goToHub}
          onStudentLogin={() => openPreAuthView('student-login')}
          onAdminLogin={() => openPreAuthView('admin-login')}
        />
      );
    }
    if (preAuthView === 'student-login') {
      return (
        <StudentLogin
          onBack={goToHub}
          onLogin={(data) => {
            setPortalMode('student');
            setUser(data);
          }}
        />
      );
    }
    if (preAuthView === 'admin-login') {
      return (
        <AdminLogin
          onBack={goToHub}
          onLogin={(data) => {
            setPortalMode('admin');
            setUser(data);
          }}
        />
      );
    }
    return (
      <PreAuthHub
        onCustomUni={() => openPreAuthView('custom')}
        onStudentLogin={() => openPreAuthView('student-login')}
        onAdminLogin={() => openPreAuthView('admin-login')}
      />
    );
  }

  if (portalMode === 'student') {
    return <StudentPortal user={user} onLogout={handleLogout} />;
  }

  return <AdminPortal user={user} onLogout={handleLogout} />;
}
