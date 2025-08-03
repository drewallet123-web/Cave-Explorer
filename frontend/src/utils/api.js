import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.VITE_ENABLE_LOGGING === 'true') {
      console.log('API Request:', config);
    }
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    if (import.meta.env.VITE_ENABLE_LOGGING === 'true') {
      console.log('API Response:', response);
    }
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    
    // Handle common error cases
    if (error.response?.status === 404) {
      throw new Error('Game session not found');
    } else if (error.response?.status >= 500) {
      throw new Error('Server error - please try again later');
    } else if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - please check your connection');
    }
    
    throw error;
  }
);

export const gameAPI = {
  startGame: async (playerName, clientSeed = null) => {
    const response = await api.post('/start_game', {
      player_name: playerName,
      seed: clientSeed
    });
    return response.data;
  },

  takeTurn: async (sessionId, playerName, pathId, insurance = false) => {
    const response = await api.post('/take_turn', {
      session_id: sessionId,
      player_name: playerName,
      chosen_path_id: pathId,
      insurance
    });
    return response.data;
  },

  getGameState: async (sessionId) => {
    const response = await api.get(`/game_state/${sessionId}`);
    return response.data;
  },

  revealProvenance: async (sessionId) => {
    const response = await api.get(`/reveal_game/${sessionId}`);
    return response.data;
  },

  endSession: async (sessionId) => {
    const response = await api.delete(`/session/${sessionId}`);
    return response.data;
  },

  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  }
};

export default api;