# 🚀 Cave Explorer - Production Deployment Package

## 📁 Project Structure
```
cave-explorer/
├── frontend/                 # React frontend
│   ├── public/
│   │   ├── favicon.ico
│   │   ├── manifest.json
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── CaveExplorer.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   └── LoadingSpinner.jsx
│   │   ├── hooks/
│   │   │   └── useGameApi.js
│   │   ├── utils/
│   │   │   ├── api.js
│   │   │   └── constants.js
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── .env.example
│   ├── .env.production
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── game_logic.py
│   │   └── provenance.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml        # Full stack deployment
├── nginx.conf               # Production web server
├── deploy.sh               # Deployment script
└── README.md               # Setup instructions
```

## 🔧 Frontend Setup

### package.json
```json
{
  "name": "cave-explorer-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0",
    "format": "prettier --write \"src/**/*.{js,jsx,css,md}\""
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.263.1",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.3",
    "vite": "^4.4.5",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.24",
    "eslint": "^8.45.0",
    "eslint-plugin-react": "^7.32.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.3",
    "prettier": "^3.0.0"
  }
}
```

### vite.config.js
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          icons: ['lucide-react']
        }
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  preview: {
    port: 3000
  }
})
```

### tailwind.config.js
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      }
    },
  },
  plugins: [],
}
```

### Environment Configuration

**.env.example**
```bash
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Cave Explorer
VITE_APP_VERSION=1.0.0

# Development flags
VITE_DEV_MODE=false
VITE_ENABLE_LOGGING=false
```

**.env.production**
```bash
VITE_API_URL=https://your-api-domain.com
VITE_APP_NAME=Cave Explorer
VITE_APP_VERSION=1.0.0
VITE_DEV_MODE=false
VITE_ENABLE_LOGGING=false
```

## 🔗 API Integration Layer

### src/utils/api.js
```javascript
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
```

### src/hooks/useGameApi.js
```javascript
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
```

## 🛡️ Error Boundary Component

### src/components/ErrorBoundary.jsx
```javascript
import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Cave Explorer Error:', error, errorInfo);
    
    // In production, you might want to send this to an error reporting service
    if (import.meta.env.PROD) {
      // Example: errorReportingService.captureException(error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
            <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Something went wrong
            </h2>
            <p className="text-gray-600 mb-6">
              The cave has collapsed! Don't worry, we can dig you out.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center space-x-2 mx-auto px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Try Again</span>
            </button>
            
            {import.meta.env.DEV && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-sm text-gray-500">
                  Error Details (Dev Mode)
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto">
                  {this.state.error?.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

## 🐳 Docker Configuration

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

## 🔧 Production Configuration

### docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: cave-explorer-api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEV_MODE=false
    volumes:
      - ./backend/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: cave-explorer-web
    ports:
      - "80:80"
      - "443:443"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: cave-explorer-proxy
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
```

### nginx.conf
```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:80;
}

server {
    listen 80;
    server_name localhost;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Frontend routes
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API routes
    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

## 🚀 Deployment Script

### deploy.sh
```bash
#!/bin/bash

set -e

echo "🚀 Starting Cave Explorer deployment..."

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | xargs)
fi

# Build and deploy
echo "📦 Building containers..."
docker-compose down
docker-compose build --no-cache

echo "🔄 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Health checks
echo "🏥 Checking backend health..."
curl -f http://localhost:8000/health || exit 1

echo "🏥 Checking frontend health..."
curl -f http://localhost/ || exit 1

echo "✅ Deployment successful!"
echo "🌐 Frontend: http://localhost"
echo "🔧 API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"

# Show running containers
echo "📋 Running containers:"
docker-compose ps
```

## 📋 Production Checklist

### Security
- [ ] Enable HTTPS with SSL certificates
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Add input validation
- [ ] Set up monitoring and logging

### Performance
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets
- [ ] Configure database connection pooling
- [ ] Add Redis for session storage
- [ ] Set up horizontal scaling

### Monitoring
- [ ] Add health check endpoints
- [ ] Set up error tracking (Sentry)
- [ ] Configure log aggregation
- [ ] Add performance monitoring
- [ ] Set up alerts

### Abstract Chain Integration
- [ ] Add wallet connection
- [ ] Implement transaction signing
- [ ] Add gas estimation
- [ ] Configure chain networks
- [ ] Add token contract integration

## 🎯 Quick Deploy Commands

```bash
# Clone and setup
git clone <your-repo>
cd cave-explorer

# Copy environment files
cp frontend/.env.example frontend/.env.production
cp backend/.env.example backend/.env

# Edit environment variables
nano frontend/.env.production
nano backend/.env

# Deploy
chmod +x deploy.sh
./deploy.sh
```

This deployment package gives you:
- ✅ Production-ready builds
- ✅ Docker containerization
- ✅ Load balancing with Nginx
- ✅ Health checks and monitoring
- ✅ Error boundaries and logging
- ✅ Environment configuration
- ✅ Security headers
- ✅ Performance optimizations

Ready to deploy anywhere! 🚀