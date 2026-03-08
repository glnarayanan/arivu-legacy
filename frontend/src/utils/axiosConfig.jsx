import axios from 'axios';

const API = '/api';

// Create axios instance
const axiosInstance = axios.create({
  baseURL: API,
  withCredentials: true,  // Important: send cookies with requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track if we're currently refreshing to avoid multiple refresh requests
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Request interceptor - cookies are sent automatically, no manual token needed
axiosInstance.interceptors.request.use(
  (config) => {
    // Cookies are sent automatically via withCredentials: true
    // No need to manually add Authorization header
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => axiosInstance(originalRequest))
          .catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Try to refresh token - cookies are sent automatically
        const response = await axios.post(`${API}/auth/refresh`, {}, {
          withCredentials: true,
        });

        processQueue(null, null); // Cookies are updated automatically
        isRefreshing = false;

        // Retry original request
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        isRefreshing = false;

        // Refresh failed - logout
        // Call logout endpoint to clear cookies
        await axios.post(`${API}/auth/logout`, {}, { withCredentials: true })
          .catch(() => {}); // Ignore logout errors

        // Redirect to auth page
        window.location.href = '/auth';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;
