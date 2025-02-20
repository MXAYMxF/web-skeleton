# Development Guide

## Overview

This guide provides detailed instructions for setting up and developing with our web application skeleton.

## Prerequisites

- Python 3.8+
- Node.js 16+
- Docker and Docker Compose
- PostgreSQL 13+ (if running locally)
- Redis 6+ (if running locally)

## Initial Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd web-skeleton
   ```

2. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your settings
   nano .env
   ```

3. **Backend Setup**
   ```bash
   # Create virtual environment
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   
   # Install dependencies
   pip install -r requirements.txt
   ```

4. **Database Setup**
   ```bash
   # Using Docker
   docker-compose up -d db redis
   
   # Run migrations
   cd backend
   alembic upgrade head
   ```

## Development Workflow

### Running the Application

1. **Start Dependencies**
   ```bash
   docker-compose up -d db redis
   ```

2. **Start Backend (Development Mode)**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

3. **Start Frontend (Development Mode)**
   ```bash
   cd frontend
   npm run dev
   ```

### Testing

1. **Running Backend Tests**
   ```bash
   cd backend
   pytest
   
   # With coverage
   pytest --cov=app
   
   # Generate coverage report
   pytest --cov=app --cov-report=html
   ```

2. **Running Frontend Tests**
   ```bash
   cd frontend
   npm test
   ```

### Code Quality

1. **Backend Linting**
   ```bash
   # Run flake8
   flake8 app
   
   # Run black
   black app
   
   # Run isort
   isort app
   ```

2. **Type Checking**
   ```bash
   mypy app
   ```

## Project Structure

### Backend Structure
```
backend/
├── app/
│   ├── api/           # API routes
│   │   ├── v1/        # API version 1
│   │   └── ws/        # WebSocket endpoints
│   ├── core/          # Core functionality
│   ├── crud/          # CRUD operations
│   ├── db/            # Database
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   └── tests/         # Tests
├── migrations/        # Alembic migrations
└── scripts/          # Utility scripts
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/    # React components
│   ├── hooks/        # Custom React hooks
│   ├── pages/        # Next.js pages
│   ├── services/     # API clients
│   ├── styles/       # CSS/SCSS files
│   └── tests/        # Tests
└── public/           # Static files
```

## Best Practices

### Code Style

1. **Python**
   - Follow PEP 8 guidelines
   - Use type hints
   - Write docstrings for all public functions and classes
   - Keep functions small and focused

2. **TypeScript/JavaScript**
   - Use ESLint configuration
   - Write JSDoc comments for components and functions
   - Use TypeScript interfaces for prop types

### Testing

1. **Backend Testing**
   - Write unit tests for all CRUD operations
   - Write integration tests for API endpoints
   - Maintain test coverage above 80%
   - Use fixtures for test data

2. **Frontend Testing**
   - Write unit tests for components
   - Write integration tests for pages
   - Test hooks independently
   - Use mock service workers for API calls

### Git Workflow

1. **Branching**
   - main: Production-ready code
   - develop: Development branch
   - feature/*: New features
   - bugfix/*: Bug fixes
   - release/*: Release preparation

2. **Commits**
   - Use conventional commits format
   - Include ticket numbers in commit messages
   - Keep commits focused and atomic

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check if PostgreSQL is running
   - Verify database credentials in .env
   - Ensure migrations are up to date

2. **Redis Connection Issues**
   - Check if Redis is running
   - Verify Redis connection settings

3. **Test Failures**
   - Ensure test database is configured
   - Check if all dependencies are installed
   - Verify test environment variables

## Deployment

See [deployment.md](../deployment/deployment.md) for detailed deployment instructions.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
