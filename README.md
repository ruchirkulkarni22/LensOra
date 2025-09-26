# LensOra Setup Guide

This document provides comprehensive setup instructions for the LensOra application, covering all components from Docker containers to frontend and backend services.

## 1. Prerequisites

Ensure you have the following installed on your system:

- Docker and Docker Compose
- Python 3.10+
- Node.js and npm
- DBeaver (optional, for database management)

## 2. Docker Container Setup

The LensOra application uses Docker to manage its database and Temporal service dependencies.

### Start Docker Containers

1. Navigate to the project root directory:

   ```bash
   cd /path/to/LensOra
   ```

2. Start the Docker containers:

   ```bash
   docker-compose up -d
   ```

3. Verify that containers are running:

   ```bash
   docker ps
   ```

   You should see three containers running:
   - `lensora-temporal-1` (Temporal workflow engine) - Port 7233, 8089
   - `lensora-lensora_db-1` (PostgreSQL with pgvector for the application) - Port 5433
   - `lensora-temporal-db-1` (PostgreSQL for Temporal service) - Port 5432

## 3. Database Setup

### Database Configuration

The application uses PostgreSQL with pgvector extension for vector operations. Configuration details:

- **Application Database**:
  - Host: localhost
  - Port: 5433
  - Database: lensora
  - Username: lensora
  - Password: lensora

- **Temporal Database**:
  - Host: localhost
  - Port: 5432
  - Database: temporal
  - Username: temporal
  - Password: temporal

### Initialize the Database

1. From the project root directory, seed the database with initial data:

   ```bash
   python -m backend.seed_db
   ```

2. This will create necessary tables and populate them with initial data for:
   - Module taxonomies (AP.Invoice, PO.Creation, General.Inquiry)
   - Mandatory field templates

### Database Connection(Optional)

1. Open DBeaver and create a new PostgreSQL connection
2. Enter the connection details for the application database:
   - Host: localhost
   - Port: 5433
   - Database: lensora
   - Username: lensora
   - Password: lensora
3. Test the connection and click "Finish"

## 4. Backend Setup

### Environment Configuration

The application uses a `.env` file for configuration. Key settings include:

- Database connection details
- Temporal configuration
- JIRA credentials
- AI API keys (Gemini, OpenAI)

Ensure your `.env` file is properly configured with all necessary credentials.

### Install Python Dependencies

1. From the project root directory:

   ```bash
   pip install -r requirements.txt
   ```

### Start the Backend Server

1. From the project root directory:

   ```bash
   python run.py
   ```

   This will start the FastAPI server, typically on port 8000.

### Start the Worker Process

The worker process handles Temporal workflows.

1. From a new terminal, run:

   ```bash
   python -m backend.worker
   ```

## 5. Frontend Setup

### Install Node.js Dependencies

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

### Start the Frontend Development Server

1. From the frontend directory:

   ```bash
   npm start
   ```

   This will start the React development server, typically on port 3000.

## 6. Verifying the Setup

### Check Backend API

1. Open a web browser and navigate to: `http://localhost:8000/docs`
2. You should see the Swagger UI with API endpoints

### Check Frontend

1. Open a web browser and navigate to: `http://localhost:3000`
2. The LensOra application interface should appear

### Check Temporal UI

1. Open a web browser and navigate to: `http://localhost:8089`
2. The Temporal Web UI should be available for monitoring workflows

## 7. Common Issues and Troubleshooting

### Database Connection Issues

- Verify Docker containers are running with `docker ps`
- Check port mappings in `docker-compose.yml`
- Ensure the `.env` file has the correct database connection details

### Python Import Errors

- Always run Python commands from the project root directory
- Use module syntax: `python -m backend.module_name`
- Set PYTHONPATH if needed: `PYTHONPATH=. python backend/module_name.py`

### Docker Container Issues

- Reset containers with:

  ```bash
  docker-compose down
  docker-compose up -d
  ```

## 8. Additional Resources

- For workflow operations, see the Temporal documentation
- For API development, refer to the FastAPI documentation
- For database migrations, use Alembic commands as needed

## 9. Project Structure

```text
LensOra/
├── alembic.ini               # Alembic configuration for database migrations
├── docker-compose.yml        # Docker configuration for services
├── requirements.txt          # Python dependencies
├── run.py                    # Main entry point for the backend server
├── backend/
│   ├── config.py             # Application configuration
│   ├── seed_db.py            # Database seeding script
│   ├── worker.py             # Temporal worker process
│   ├── api/                  # API endpoints and schemas
│   ├── db/                   # Database models and migrations
│   ├── services/             # Service layer components
│   └── workflows/            # Temporal workflow definitions
├── data/                     # Data files for application
└── frontend/                 # React frontend application
```

---

This setup guide covers the basic requirements to get the LensOra application up and running locally. For production deployment, additional considerations for security, scalability, and monitoring would be needed.
