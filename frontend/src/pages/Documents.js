import { useState, useEffect } from 'react';
import { listDocuments, uploadDocument, deleteDocument } from '../services/api';

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchDocs(); }, []);

  const fetchDocs = async () => {
    try {
      const res = await listDocuments();
      setDocuments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name);

    try {
      const res = await uploadDocument(formData);
      setMessage(`✅ ${res.data.message}`);
      fetchDocs();
    } catch (err) {
      setMessage('❌ Upload failed. Check file type and size.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await deleteDocument(id);
      setDocuments(documents.filter(d => d.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="loading">Loading documents...</div>;

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#6c63ff' }}>📄 Documents</h2>

      {/* Upload Card */}
      <div className="card" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <p style={{ color: '#8888aa', marginBottom: '16px' }}>
          Upload university documents (PDF, DOCX, TXT) — they will be indexed for AI learning
        </p>
        <label style={{
          display: 'inline-block', padding: '12px 24px',
          background: '#6c63ff', borderRadius: '8px',
          cursor: 'pointer', fontWeight: '600'
        }}>
          {uploading ? '⏳ Uploading...' : '📤 Upload Document'}
          <input type="file" accept=".pdf,.docx,.txt,.pptx"
            onChange={handleUpload} style={{ display: 'none' }} disabled={uploading} />
        </label>
        {message && <p className={message.includes('✅') ? 'success' : 'error'}
          style={{ marginTop: '12px' }}>{message}</p>}
      </div>

      {/* Documents List */}
      {documents.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: '#8888aa' }}>
          <p style={{ fontSize: '48px' }}>📂</p>
          <p>No documents uploaded yet.</p>
        </div>
      ) : (
        documents.map(doc => (
          <div key={doc.id} className="card" style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ fontSize: '32px' }}>
                {doc.file_type === 'pdf' ? '📕' : doc.file_type === 'docx' ? '📘' : '📄'}
              </span>
              <div>
                <p style={{ fontWeight: '600' }}>{doc.title}</p>
                <p style={{ color: '#8888aa', fontSize: '13px' }}>
                  {doc.file_type?.toUpperCase()} • Uploaded by {doc.uploaded_by} •{' '}
                  <span style={{ color: doc.is_processed ? '#43e97b' : '#f9a825' }}>
                    {doc.is_processed ? '✅ Indexed in RAG' : '⏳ Processing...'}
                  </span>
                </p>
              </div>
            </div>
            <button className="btn btn-danger" style={{ padding: '6px 14px' }}
              onClick={() => handleDelete(doc.id)}>Delete</button>
          </div>
        ))
      )}
    </div>
  );
}
