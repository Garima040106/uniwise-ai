# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added
- Cognitive load tracking system with real-time monitoring
- CognitiveMeter React component with circular progress visualization
- BreakMode component with timer enforcement and content blocking
- CognitiveLoadCalculator with circadian rhythm analysis
- REST endpoints for cognitive load and optimal study times
- BreakSession model for tracking break effectiveness

### Changed
- Improved Dashboard to show cognitive status prominently
- Enhanced API documentation with Mermaid diagrams

## [0.3.0] - 2026-03-03

### Added
- Multi-tenant administration portal
- Dual RAG system (academic + university_info knowledge bases)
- Public/private visibility controls for university information
- API audit logging for compliance tracking
- Integration registry for LMS, ERP, SSO providers
- Response caching and API throttling controls
- Database router for multi-tenant routing

### Changed
- Expanded RBAC with Professor, IT Admin, Super Admin roles
- Enhanced security defaults for production deployments
- Improved error handling in RAG pipeline

### Fixed
- Token expiration on page refresh
- Memory leaks in vector database queries

## [0.2.1] - 2026-02-20

### Added
- Document progress analytics
- Learning curve visualization
- Skill breakdown by course
- Quiz history tracking

### Fixed
- PDF extraction Unicode handling
- Flashcard difficulty level calculation

## [0.2.0] - 2026-02-10

### Added
- Student learning workspace with dashboard
- AI-powered flashcard generation
- Dynamic quiz creation with explanations
- Spaced repetition scheduling algorithm
- Progress tracking and analytics
- Course structure and subject management
- Two-factor authentication support
- Password reset functionality
- SSO provider scaffolding (Google, Microsoft)

### Changed
- Migrated to Django 4.2 LTS
- Refactored authentication middleware for multi-tenancy

## [0.1.0] - 2026-01-15

### Added
- Initial project structure (Django + React)
- Multi-university support with university selection
- Student authentication system
- Basic RAG pipeline with ChromaDB
- Document upload and processing
- Ollama LLM integration (llama3.2:3b)
- Docker setup for local development
- API documentation scaffolding
- Initial React component library

### Fixed
- CORS configuration for local development

---

## Migration Guides

### Upgrading from 0.2.x to 0.3.0

```bash
# No breaking API changes
# Run migrations
python manage.py migrate

# Update dependencies
pip install -r requirements.txt
```

### Upgrading from 0.1.0 to 0.2.0

Breaking changes:
- `/api/study/` endpoints consolidated into `/api/flashcards/` and `/api/quizzes/`
- Database schema: `Study_Session` table added, old data migration required

```bash
# Backup database
pg_dump -U postgres uniwise_db > backup_0.1.0.sql

# Run migrations
python manage.py migrate

# Test endpoints
curl http://localhost:8000/api/flashcards/list/
```

---

## How to Contribute

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Suggesting a Change

- Open an issue describing your proposal
- Discuss the change with maintainers
- Create a PR with implementation

### Reporting a Bug

- Check if the bug is already reported
- Include reproduction steps and version info
- Provide system information if relevant

---

## Release Schedule

- **Patch releases** (0.0.x): As needed for bug fixes
- **Minor releases** (0.x.0): Monthly with new features
- **Major releases** (x.0.0): Planned for Q3 2026

---

## Future Roadmap (Tentative)

- [ ] WebSocket support for real-time collaboration (v0.4.0)
- [ ] Advanced analytics dashboard with Plotly (v0.4.0)
- [ ] Mobile app (React Native) (v0.5.0)
- [ ] Multi-language support (v0.5.0)
- [ ] OpenAI GPT-4 integration (v0.6.0)
- [ ] Salesforce LMS integration (v0.6.0)
- [ ] WCAG 2.1 AA accessibility (v0.7.0)

---

For more details, see [GitHub Releases](https://github.com/Garima040106/uniwise-ai/releases).
