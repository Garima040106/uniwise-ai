import { useState } from 'react';
import { askQuestion } from '../services/api';

export default function AskAI() {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    const q = question;
    setQuestion('');

    try {
      const res = await askQuestion({ question: q });
      const entry = {
        question: q,
        answer: res.data.answer,
        sources: res.data.sources,
        found: res.data.found_in_docs,
      };
      setHistory([entry, ...history]);
      setResponse(entry);
    } catch (err) {
      setResponse({
        question: q,
        answer: 'Error: Could not get a response. Make sure you are affiliated with a university.',
        sources: [],
        found: false,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: '8px', color: '#6c63ff' }}>🤖 Ask Uniwise AI</h2>
      <p style={{ color: '#8888aa', marginBottom: '24px' }}>
        Ask anything — I'll answer only from your university's uploaded documents.
      </p>

      {/* Question Input */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <textarea
          className="input"
          rows={3}
          placeholder="Ask a question about your course material..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAsk()}
          style={{ resize: 'vertical' }}
        />
        <button className="btn btn-primary" onClick={handleAsk}
          disabled={loading || !question.trim()} style={{ width: '100%' }}>
          {loading ? '🤔 Thinking...' : '🚀 Ask AI'}
        </button>
      </div>

      {/* Response */}
      {history.map((entry, idx) => (
        <div key={idx} className="card" style={{ marginBottom: '16px' }}>
          <div style={{ marginBottom: '16px' }}>
            <p style={{ color: '#8888aa', fontSize: '12px', marginBottom: '4px' }}>YOUR QUESTION</p>
            <p style={{ fontWeight: '600' }}>{entry.question}</p>
          </div>

          <div style={{
            background: '#0f0f1a', borderRadius: '8px', padding: '16px',
            borderLeft: `4px solid ${entry.found ? '#6c63ff' : '#ff6584'}`
          }}>
            <p style={{ color: '#8888aa', fontSize: '12px', marginBottom: '8px' }}>
              {entry.found ? '✅ ANSWER FROM UNIVERSITY DOCS' : '⚠️ NOT FOUND IN DOCS'}
            </p>
            <p style={{ lineHeight: '1.6' }}>{entry.answer}</p>
          </div>

          {entry.sources.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <p style={{ color: '#8888aa', fontSize: '12px', marginBottom: '8px' }}>📚 SOURCES</p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {entry.sources.map((source, i) => (
                  <span key={i} style={{
                    background: '#1a1a3a', padding: '4px 10px',
                    borderRadius: '20px', fontSize: '12px', color: '#6c63ff'
                  }}>{source}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
