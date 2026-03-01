import './PreAuthHub.css';

export default function PreAuthHub({ onCustomUni, onStudentLogin, onAdminLogin }) {
  return (
    <div className="hub-shell">
      <div className="hub-overlay" aria-hidden="true" />
      <main className="hub-content">
        <section className="hub-hero card">
          <p className="hub-kicker">UNIWISE AI PLATFORM</p>
          <h1>Choose your workspace</h1>
          <p>
            Configure a custom university assistant, sign in as a student, or access administration
            controls.
          </p>
        </section>

        <section className="hub-grid">
          <article className="card hub-card">
            <h2>Design Your Custom University</h2>
            <p>Set branding, tenant profile, and how your campus-specific LLM experience should look.</p>
            <button type="button" className="btn btn-primary" onClick={onCustomUni}>
              Open University Designer
            </button>
          </article>

          <article className="card hub-card">
            <h2>Student Login</h2>
            <p>Access personal learning tools, AI study support, and progress tracking dashboards.</p>
            <button type="button" className="btn btn-primary" onClick={onStudentLogin}>
              Go to Student Login
            </button>
          </article>

          <article className="card hub-card">
            <h2>Administration Login</h2>
            <p>Manage institutional settings, documents, and system-level controls for your campus.</p>
            <button type="button" className="btn btn-primary" onClick={onAdminLogin}>
              Go to Admin Login
            </button>
          </article>
        </section>
      </main>
    </div>
  );
}
