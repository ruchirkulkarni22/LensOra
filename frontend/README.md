# LensOra Admin UI

This is the frontend React application for the LensOra AI Admin Dashboard, which provides a human-in-the-loop interface for resolving JIRA tickets.

## Features

- View complete tickets that are ready for resolution
- Generate AI-powered solution alternatives using LLM and RAG
- Review, edit, and submit solutions to JIRA
- Track resolution history and status

## Getting Started

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm start
```

The application will start on http://localhost:3000.

## Requirements

- Node.js 14+ and npm
- Backend API running on http://localhost:8000

## Structure

- `src/App.js` - Main application component
- `src/App.css` - Styling for the application
- `public/index.html` - HTML template