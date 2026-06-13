import axios from 'axios';

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('huayue_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('huayue_token');
      localStorage.removeItem('huayue_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default request;
