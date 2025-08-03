import { useState, useCallback } from 'react';
import { gameAPI } from '../utils/api';

export const useGameApi = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const apiCall = useCallback(async (apiFunction, ...args) => {
    setLoading(true);
    setError('');
    
    try {
      const result = await apiFunction(...args);
      
      if (result.error) {
        setError(result.error);
        return null;
      }
      
      return result;
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    clearError: () => setError(''),
    startGame: (playerName, clientSeed) => 
      apiCall(gameAPI.startGame, playerName, clientSeed),
    takeTurn: (sessionId, playerName, pathId, insurance) => 
      apiCall(gameAPI.takeTurn, sessionId, playerName, pathId, insurance),
    getGameState: (sessionId) => 
      apiCall(gameAPI.getGameState, sessionId),
    revealProvenance: (sessionId) => 
      apiCall(gameAPI.revealProvenance, sessionId),
    endSession: (sessionId) => 
      apiCall(gameAPI.endSession, sessionId),
    healthCheck: () => 
      apiCall(gameAPI.healthCheck)
  };
};