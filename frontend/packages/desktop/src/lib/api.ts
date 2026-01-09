import axios from 'axios';

// Get API base URL from environment variable
// In Vite, environment variables must be prefixed with VITE_ to be exposed to the client
// Default to localhost:17890 if not set
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:17890';

// Log API base URL in development for debugging
if (import.meta.env.DEV) {
  console.log('API Base URL:', API_BASE_URL);
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNREFUSED') {
      throw new Error('Backend service is not running. Please start the Python service.');
    }
    throw error;
  }
);

