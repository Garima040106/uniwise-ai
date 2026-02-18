import { useState, useEffect } from 'react';
import { listFlashcards, getFlashcardsDueToday, reviewFlashcard, generateFlashcards, listDocuments, deleteFlashcard } from '../services/api';

export default function Flashcards() {
  const [flashcards, setFlashcards] = useState([]);
  const [dueToday, setDueToday] = useState(0);
  const [documents, setDocuments] = useState([]);
  const [flipped, setFlipped] = useState({});
  const [generating, setGenerating] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState('');
  const [numCards, setNumCards] = useState(5);
  const [difficulty, setDifficulty] = useState('medium');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [cardsRes, dueRes, docsRes] = await Promise.all([
        listFlashcards(),
        getFlashcardsDueToday(),
        listDocuments(),
      ]);
      setFlashcards(cardsRes.data);
      setDueToday(dueRes.data.due_today);
      setDocuments(docsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedDoc) return setMessage('Please select a document first');
    setGenerating(true);
    setMessage('');
    try {
      const res = await generateFlashcards({
        document_id: selectedDoc,
        num_cards: numCards,
        difficulty,
      });
      setMessage(`✅ Generated ${res.data.flashcards.length} flashcards!`);
      fetchData();
    } catch (err) {
      const backendError = err?.response?.data?.error;
      const timeoutMsg = err?.code === 'ECONNABORTED'
        ? ' Request timed out. Try 3 cards first on CPU-only mode.'
        : '';
      setMessage(`❌ Failed to generate flashcards.${backendError ? ` ${backendError}` : ''}${timeoutMsg}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleReview = async (cardId, rating) => {
    try {
      await reviewFlashcard(cardId, { rating });
      setFlashcards(flashcards.filter(f => f.id !== cardId));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteCard = async (cardId) => {
    try {
      await deleteFlashcard(cardId);
      setFlashcards(flashcards.filter((f) => f.id !== cardId));
      setDueToday((prev) => Math.max((prev || 0) - 1, 0));
    } catch (err) {
      console.error(err);
      setMessage('❌ Failed to delete flashcard');
    }
  };

  if (loading) return <div className="loading">Loading flashcards...</div>;

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>🃏 Flashcards</h2>

      {/* Generate Panel */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>Generate New Flashcards</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '12px', alignItems: 'end' }}>
          <div>
            <label style={{ color: '#8888aa', fontSize: '13px' }}>Select Document</label>
            <select className="input" style={{ marginTop: '4px' }}
              value={selectedDoc} onChange={(e) => setSelectedDoc(e.target.value)}>
              <option value="">-- Choose a document --</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>{d.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ color: '#8888aa', fontSize: '13px' }}>Number of Cards</label>
            <input className="input" style={{ marginTop: '4px' }} type="number"
              min="1" max="20" value={numCards}
              onChange={(e) => setNumCards(e.target.value)} />
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
            {generating ? '⏳ Generating...' : '✨ Generate'}
          </button>
        </div>
        {message && <p className={message.includes('✅') ? 'success' : 'error'}>{message}</p>}
      </div>

      {/* Due Today Banner */}
      {dueToday > 0 && (
        <div className="card" style={{ background: '#1a2a3a', borderColor: '#6c63ff', marginBottom: '24px' }}>
          <p>📅 You have <strong style={{ color: '#6c63ff' }}>{dueToday} flashcards</strong> due for review today!</p>
        </div>
      )}

      {/* Flashcards Grid */}
      {flashcards.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: '#8888aa' }}>
          <p style={{ fontSize: '48px' }}>🃏</p>
          <p>No flashcards yet. Generate some from your documents!</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
          {flashcards.map(card => (
            <div key={card.id} className="card"
              style={{ cursor: 'pointer', transition: 'all 0.2s' }}
              onClick={() => setFlipped({ ...flipped, [card.id]: !flipped[card.id] })}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span className={`badge badge-${card.difficulty}`}>{card.difficulty}</span>
                <span style={{ color: '#8888aa', fontSize: '12px' }}>Click to flip</span>
              </div>

              <div style={{ minHeight: '80px' }}>
                {!flipped[card.id] ? (
                  <div>
                    <p style={{ color: '#8888aa', fontSize: '12px', marginBottom: '8px' }}>QUESTION</p>
                    <p>{card.question}</p>
                  </div>
                ) : (
                  <div>
                    <p style={{ color: '#43e97b', fontSize: '12px', marginBottom: '8px' }}>ANSWER</p>
                    <p>{card.answer}</p>
                  </div>
                )}
              </div>

              {flipped[card.id] && (
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}
                  onClick={(e) => e.stopPropagation()}>
                  <button className="btn btn-danger" style={{ flex: 1, padding: '6px' }}
                    onClick={() => handleDeleteCard(card.id)}>Delete</button>
                  <button className="btn btn-secondary" style={{ flex: 1, padding: '6px' }}
                    onClick={() => handleReview(card.id, 2)}>Hard</button>
                  <button className="btn btn-secondary" style={{ flex: 1, padding: '6px' }}
                    onClick={() => handleReview(card.id, 3)}>Good</button>
                  <button className="btn btn-success" style={{ flex: 1, padding: '6px' }}
                    onClick={() => handleReview(card.id, 4)}>Easy</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
