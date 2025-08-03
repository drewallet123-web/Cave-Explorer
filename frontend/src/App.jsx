import React, { useState } from 'react';

function App() {
  const [message, setMessage] = useState('');

  const testAPI = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      const data = await response.json();
      setMessage(`API Connected: ${data.status}`);
    } catch (error) {
      setMessage(`API Error: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
        <h1 className="text-3xl font-bold text-gray-800 mb-4">🕳️ Cave Explorer</h1>
        <p className="text-gray-600 mb-6">Game is starting up...</p>
        
        <button
          onClick={testAPI}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
        >
          Test API Connection
        </button>
        
        {message && (
          <div className="mt-4 p-3 bg-gray-100 rounded">
            {message}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;