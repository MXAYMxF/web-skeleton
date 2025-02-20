# Web Application Skeleton

A modern, scalable, and well-documented web application skeleton designed for rapid development and easy maintenance. This skeleton provides a solid foundation for building web applications with comprehensive documentation and pre-configured development environment.

## Key Features
- REST APIs with OpenAPI documentation
- GraphQL APIs
- WebSocket support
- Authentication & Authorization
- Database integration
- Test-driven development
- Web3 integration readiness
- Mobile-first API design

## Features

- 🔐 Authentication & Authorization
  - JWT-based authentication
  - Role-based access control
  - OAuth2 support
  - Social login ready

- 📱 API Support
  - REST APIs with OpenAPI/Swagger documentation
  - GraphQL API
  - WebSocket support
  - Mobile-friendly endpoints
  - API versioning

- 💾 Database
  - PostgreSQL for persistent storage
  - Redis for caching
  - Database migrations
  - Audit logging

- 🧪 Testing
  - Unit tests
  - Integration tests
  - E2E tests
  - API tests
  - Performance tests

- 🔧 Development Tools
  - Docker development environment
  - Hot reload
  - Debug configurations
  - Code formatting and linting
  - Git hooks

- 📚 Documentation
  - API documentation (OpenAPI/Swagger)
  - WebSocket documentation (AsyncAPI)
  - Development guides
  - Deployment guides

## Documentation

This project includes comprehensive documentation:

- 📚 **Development Guide**: Detailed setup and development instructions in `docs/guides/development.md`
- 🔧 **Configuration Guide**: Environment variables and system configuration in `.env.example`
- 📐 **Architecture Documentation**: System design and decisions in `docs/architecture/`
- 🧪 **Testing Guide**: Testing strategies and examples in `docs/testing/`
- 📦 **Deployment Guide**: Production deployment instructions in `docs/deployment/`

## Quick Start

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd web-skeleton
   ```

2. **Configure Environment**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit environment variables
   nano .env
   ```

3. **Start Development Environment**
   ```bash
   # Start dependencies
   docker-compose up -d
   
   # Install backend dependencies
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Run migrations
   alembic upgrade head
   
   # Start backend server
   uvicorn app.main:app --reload
   ```

4. **Access the Application**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - GraphQL Playground: http://localhost:8000/graphql

## Project Structure

```
web-skeleton/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   │   ├── v1/         # API version 1
│   │   │   └── ws/         # WebSocket endpoints
│   │   ├── core/           # Core functionality
│   │   ├── crud/           # CRUD operations
│   │   ├── db/             # Database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── tests/          # Backend tests
│   ├── migrations/         # Alembic migrations
│   └── scripts/            # Utility scripts
│
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── pages/          # Next.js pages
│   │   ├── services/       # API clients
│   │   ├── styles/         # CSS/SCSS files
│   │   └── tests/          # Frontend tests
│   └── public/             # Static files
│
├── docs/                   # Documentation
│   ├── api/               # API documentation
│   ├── architecture/      # Architecture decisions
│   └── guides/            # Development guides
│
└── docker/                # Docker configurations

## Configuration

The application uses a hierarchical configuration system:

1. **Environment Variables**
   - `.env.example` provides a template for required variables
   - Variables are documented with descriptions and default values
   - Sensitive values are never committed to version control

2. **Configuration Modules**
   - `backend/app/core/config.py` handles backend configuration
   - All settings are validated using Pydantic
   - Type hints and documentation for all settings

3. **Docker Configuration**
   - `docker-compose.yml` for development environment
   - Separate production Docker configurations
   - Environment-specific overrides

## Development Practices

1. **Code Style**
   - Python: PEP 8 guidelines, type hints, docstrings
   - TypeScript: ESLint, Prettier configuration
   - Pre-commit hooks for formatting

2. **Testing**
   - Unit tests for all components
   - Integration tests for APIs
   - End-to-end tests for critical paths
   - Coverage reports and thresholds

3. **Documentation**
   - Inline comments for complex logic
   - Function and class docstrings
   - API documentation with examples
   - Architecture decision records

## Contributing

Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```

3. Set up the database:
   ```bash
   docker-compose up -d db redis
   cd backend
   alembic upgrade head
   ```

4. Start the development servers:
   ```bash
   # Backend
   cd backend
   uvicorn app.main:app --reload

   # Frontend
   cd frontend
   npm run dev
   ```

5. Access the applications:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - GraphQL Playground: http://localhost:8000/graphql

## Development

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Documentation
- API documentation is automatically generated and available at `/docs`
- WebSocket documentation is available at `/async-api`
- GraphQL documentation is available in the GraphQL Playground

## Deployment

Deployment guides for various platforms are available in the `docs/deployment` directory.

## License

MIT
