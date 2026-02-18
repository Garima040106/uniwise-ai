import { useState, useEffect } from 'react';
import {
  listQuizzes,
  getQuiz,
  submitQuiz,
  generateQuiz,
  listDocuments,
  deleteQuiz,
} from '../services/api';

export default function Quiz() {
  const [quizzes, setQuizzes] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const [difficulty, setDifficulty] = useState('medium');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [quizRes, docsRes] = await Promise.all([listQuizzes(), listDocuments()]);
      setQuizzes(quizRes.data);
      setDocuments(docsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedDoc) return setMessage('Please select a document');
    setGenerating(true);
    setMessage('');
    try {
      await generateQuiz({ document_id: selectedDoc, num_questions: numQuestions, difficulty, title: `Quiz - ${difficulty}` });
      setMessage('✅ Quiz generated!');
      fetchData();
    } catch (err) {
      const backendError = err?.response?.data?.error;
      const timeoutMsg = err?.code === 'ECONNABORTED'
        ? ' Request timed out. Try 3 questions first on CPU-only mode.'
        : '';
      setMessage(`❌ Failed to generate quiz.${backendError ? ` ${backendError}` : ''}${timeoutMsg}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleStartQuiz = async (quizId) => {
    const res = await getQuiz(quizId);
    setActiveQuiz(res.data);
    setAnswers({});
    setResult(null);
  };

  const handleDeleteQuiz = async (quizId) => {
    if (!window.confirm('Delete this quiz?')) return;
    try {
      await deleteQuiz(quizId);
      setQuizzes((prev) => prev.filter((q) => q.id !== quizId));
    } catch (err) {
      console.error(err);
      setMessage('❌ Failed to delete quiz.');
    }
  };

  const handleSubmit = async () => {
    const res = await submitQuiz(activeQuiz.id, { answers });
    setQuizzes((prev) => prev.map((q) => (
      q.id === activeQuiz.id ? { ...q, completed: true } : q
    )));
    setResult(res.data);
  };

  if (loading) return <div className="loading">Loading quizzes...</div>;

  if (result) return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>📊 Quiz Results</h2>
      <div className="card" style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{ fontSize: '64px', marginBottom: '16px' }}>
          {result.percentage >= 70 ? '🎉' : result.percentage >= 50 ? '👍' : '📚'}
        </div>
        <h3 style={{ fontSize: '48px', color: '#6c63ff' }}>{result.percentage}%</h3>
        <p style={{ color: '#8888aa' }}>{result.score}/{result.total_marks} marks</p>
        <button className="btn btn-primary" style={{ marginTop: '16px' }}
          onClick={() => { setResult(null); setActiveQuiz(null); fetchData(); }}>
          Back to Quizzes
        </button>
      </div>
      {result.analysis && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '12px', color: '#6c63ff' }}>📈 Performance Analysis</h3>
          <p style={{ color: '#d5d5ff', marginBottom: '8px' }}>{result.analysis.summary}</p>
          <p style={{ color: '#8888aa', fontSize: '13px', marginBottom: '6px' }}>
            Accuracy: <strong style={{ color: '#6c63ff' }}>{result.analysis.accuracy}%</strong>
          </p>
          <p style={{ color: '#8888aa', fontSize: '13px', marginBottom: '6px' }}>
            Correct: {result.analysis.correct_count} • Incorrect: {result.analysis.incorrect_count} • Unanswered: {result.analysis.unanswered_count}
          </p>
          {Array.isArray(result.analysis.focus_topics) && result.analysis.focus_topics.length > 0 && (
            <p style={{ color: '#ffb3c3', fontSize: '13px', marginBottom: '6px' }}>
              Focus on: {result.analysis.focus_topics.join(' | ')}
            </p>
          )}
          <p style={{ color: '#43e97b', fontSize: '13px' }}>
            Next step: {result.analysis.recommendation}
          </p>
        </div>
      )}
      {result.results.map((r, i) => (
        <div key={i} className="card" style={{
          borderColor: r.is_correct ? '#43e97b' : '#ff6584'
        }}>
          <p style={{ fontWeight: '600', marginBottom: '8px' }}>{i + 1}. {r.question}</p>
          <p style={{ color: r.is_correct ? '#43e97b' : '#ff6584' }}>
            Your answer: {r.your_answer} {r.is_correct ? '✅' : '❌'}
          </p>
          {!r.is_correct && <p style={{ color: '#43e97b' }}>Correct: {r.correct_answer}</p>}
          {r.explanation && <p style={{ color: '#8888aa', fontSize: '13px', marginTop: '8px' }}>{r.explanation}</p>}
        </div>
      ))}
    </div>
  );

  if (activeQuiz) return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>{activeQuiz.title}</h2>
      {activeQuiz.questions.map((q, i) => (
        <div key={q.id} className="card">
          <p style={{ fontWeight: '600', marginBottom: '16px' }}>{i + 1}. {q.question}</p>
          {['A', 'B', 'C', 'D'].map(opt => (
            <div key={opt}
              onClick={() => setAnswers({ ...answers, [q.id]: opt })}
              style={{
                padding: '10px 14px', marginBottom: '8px', borderRadius: '8px',
                cursor: 'pointer', border: '1px solid',
                borderColor: answers[q.id] === opt ? '#6c63ff' : '#2a2a4a',
                background: answers[q.id] === opt ? '#1a1a3a' : '#0f0f1a',
              }}>
              <strong>{opt}.</strong> {q.options[opt]}
            </div>
          ))}
        </div>
      ))}
      <button className="btn btn-primary" style={{ width: '100%', padding: '14px' }}
        onClick={handleSubmit}>Submit Quiz</button>
    </div>
  );

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>📝 Quizzes</h2>

      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>Generate New Quiz</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '12px', alignItems: 'end' }}>
          <div>
            <label style={{ color: '#8888aa', fontSize: '13px' }}>Document</label>
            <select className="input" style={{ marginTop: '4px' }}
              value={selectedDoc} onChange={(e) => setSelectedDoc(e.target.value)}>
              <option value="">-- Choose document --</option>
              {documents.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
            </select>
          </div>
          <div>
            <label style={{ color: '#8888aa', fontSize: '13px' }}>Questions</label>
            <input className="input" style={{ marginTop: '4px' }} type="number"
              min="1" max="20" value={numQuestions}
              onChange={(e) => setNumQuestions(e.target.value)} />
          </div>
          <div>
            <label style={{ color: '#8888aa', fontSize: '13px' }}>Difficulty</label>
            <select className="input" style={{ marginTop: '4px' }}
              value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleGenerate}
            disabled={generating} style={{ marginBottom: '12px' }}>
            {generating ? '⏳...' : '✨ Generate'}
          </button>
        </div>
        {message && <p className={message.includes('✅') ? 'success' : 'error'}>{message}</p>}
      </div>

      {quizzes.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: '#8888aa' }}>
          <p style={{ fontSize: '48px' }}>📝</p>
          <p>No quizzes yet. Generate one from your documents!</p>
        </div>
      ) : quizzes.map(quiz => (
        <div key={quiz.id} className="card" style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div>
            <p style={{ fontWeight: '600' }}>{quiz.title}</p>
            <p style={{ color: '#8888aa', fontSize: '13px' }}>
              {quiz.question_count} questions • <span className={`badge badge-${quiz.difficulty}`}>{quiz.difficulty}</span>
              {quiz.completed ? ' • ✅ Completed' : ' • ⏳ Pending'}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-primary" onClick={() => handleStartQuiz(quiz.id)}>Start Quiz</button>
            <button
              className="btn"
              style={{
                background: '#2a1a25',
                color: '#ff6584',
                border: '1px solid #ff6584',
                padding: '8px 12px',
              }}
              onClick={() => handleDeleteQuiz(quiz.id)}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
