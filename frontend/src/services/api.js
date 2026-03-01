import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL
  || `${window.location.protocol}//${window.location.hostname}:8000/api`;

const API = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 240000,
  headers: { 'Content-Type': 'application/json' },
});

// Get CSRF token from cookies
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Attach CSRF token to every request
API.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// Auth
export const login = (data) => API.post('/accounts/login/', data);
export const loginStudent = (data) => API.post('/accounts/login/student/', data);
export const loginAdmin = (data) => API.post('/accounts/login/admin/', data);
export const register = (data) => API.post('/accounts/register/', data);
export const logout = () => API.post('/accounts/logout/');
export const getProfile = () => API.get('/accounts/profile/');
export const getUniversities = () => API.get('/accounts/universities/');
export const verifyTwoFactor = (data) => API.post('/accounts/two-factor/verify/', data);
export const forgotPassword = (data) => API.post('/accounts/password/forgot/', data);
export const resetPassword = (data) => API.post('/accounts/password/reset/', data);
export const getSSOProviders = () => API.get('/accounts/sso/providers/');
export const startSSO = (data) => API.post('/accounts/sso/start/', data);

// Documents
export const uploadDocument = (formData) => API.post('/documents/upload/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
});
export const listDocuments = () => API.get('/documents/list/');
export const deleteDocument = (id) => API.delete(`/documents/${id}/delete/`);

// AI Features
export const getAIStatus = () => API.get('/ai/status/');
export const generateFlashcards = (data) => API.post('/ai/flashcards/generate/', data);
export const generateQuiz = (data) => API.post('/ai/quiz/generate/', data);
export const generateExamPrep = (data) => API.post('/ai/exam-prep/generate/', data);
export const extractFacts = (data) => API.post('/ai/facts/extract/', data);
export const askQuestion = (data) => API.post('/ai/ask/', data);

// Flashcards
export const listFlashcards = () => API.get('/flashcards/list/');
export const getFlashcardsDueToday = () => API.get('/flashcards/due-today/');
export const reviewFlashcard = (id, data) => API.post(`/flashcards/${id}/review/`, data);
export const deleteFlashcard = (id) => API.delete(`/flashcards/${id}/delete/`);

// Quizzes
export const listQuizzes = () => API.get('/quizzes/list/');
export const getQuiz = (id) => API.get(`/quizzes/${id}/`);
export const submitQuiz = (id, data) => API.post(`/quizzes/${id}/submit/`, data);
export const deleteQuiz = (id) => API.delete(`/quizzes/${id}/delete/`);
export const getQuizHistory = () => API.get('/quizzes/history/');

// Analytics
export const getDashboard = () => API.get('/analytics/dashboard/');
export const getDocumentProgress = (documentId) =>
  API.get('/analytics/document-progress/', { params: documentId ? { document_id: documentId } : {} });
export const getLearningCurve = () => API.get('/analytics/learning-curve/');
export const getSkillBreakdown = () => API.get('/analytics/skill-breakdown/');

export default API;
