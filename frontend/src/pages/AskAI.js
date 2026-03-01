import { useEffect, useRef, useState } from 'react';
import { askQuestion } from '../services/api';
import './AskAI.css';

export default function AskAI({ presetQuestion = '', presetVersion = 0 }) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!presetQuestion) return;
    setQuestion(presetQuestion);
    if (textareaRef.current) textareaRef.current.focus();
  }, [presetQuestion, presetVersion]);

  const handleAsk = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    setLoading(true);
    const q = trimmedQuestion;
    setQuestion('');

    try {
      const res = await askQuestion({ question: q });
      const entry = {
        question: q,
        answer: res.data.answer,
        sources: res.data.sources || [],
        found: res.data.found_in_docs,
      };
      setHistory((current) => [entry, ...current]);
    } catch (err) {
      const entry = {
        question: q,
        answer: 'Error: Could not get a response. Make sure you are affiliated with a university.',
        sources: [],
        found: false,
      };
      setHistory((current) => [entry, ...current]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ask-ai">
      <header className="ask-ai-head">
        <h2>Ask Uniwise AI</h2>
        <p>Ask directly about academics, admin tasks, campus services, or your learning progress.</p>
      </header>

      <div className="ask-ai-input-wrap">
        <textarea
          ref={textareaRef}
          className="input"
          rows={3}
          placeholder="Type your question..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleAsk();
            }
          }}
        />
        <button
          className="btn btn-primary ask-ai-submit"
          onClick={handleAsk}
          disabled={loading || !question.trim()}
        >
          {loading ? 'Thinking...' : 'Ask AI'}
        </button>
      </div>

      <section className="ask-ai-history">
        {history.length === 0 && (
          <p className="ask-ai-empty">No messages yet. Ask your first question.</p>
        )}
        {history.map((entry, idx) => (
          <article key={`${entry.question}-${idx}`} className="ask-ai-item">
            <div className="ask-ai-question">
              <p>Question</p>
              <strong>{entry.question}</strong>
            </div>

            <div className={`ask-ai-answer ${entry.found ? 'ask-ai-answer-doc' : 'ask-ai-answer-generic'}`}>
              <p className="ask-ai-source-note">
                {entry.found ? 'Answer from university documents' : 'General answer (no direct doc match)'}
              </p>
              <p>{entry.answer}</p>
            </div>

            {entry.sources.length > 0 && (
              <div className="ask-ai-sources">
                {entry.sources.map((source, i) => (
                  <span key={`${source}-${i}`}>{source}</span>
                ))}
              </div>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
