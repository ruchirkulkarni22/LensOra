import axios from 'axios';

export async function uploadKnowledge(file) {
  const formData = new FormData();
  formData.append('file', file);
  return axios.post('/api/upload-knowledge', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
}

export async function uploadRag(file) {
  const formData = new FormData();
  formData.append('file', file);
  return axios.post('/api/upload-solved-tickets', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
}
