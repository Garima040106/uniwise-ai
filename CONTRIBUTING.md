# Contributing to Uniwise AI

First off, thanks for taking the time to contribute! 🎉

This document provides guidelines and instructions for contributing to Uniwise AI. Please read it carefully before submitting pull requests or reporting issues.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### 1. Reporting Bugs

Before creating bug reports, check the [issue list](https://github.com/Garima040106/uniwise-ai/issues) as you might find out that you don't need to create one. When you're creating a bug report, please include as many details as possible:

**How to submit a (good) bug report:**

- Use a clear, descriptive title
- Describe the exact steps which reproduce the problem
- Provide specific examples to demonstrate those steps
- Describe the behavior you observed after following the steps
- Explain which behavior you expected to see instead and why
- Include screenshots if possible
- Include your environment: Python version, Django version, OS, etc.

### 2. Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- A clear, descriptive title
- A step-by-step description of the suggested enhancement
- Specific examples to demonstrate the steps
- A description of the current behavior and expected behavior
- Why this enhancement would be useful

### 3. Pull Requests

**Before starting:**

1. Check [open PRs](https://github.com/Garima040106/uniwise-ai/pulls) to avoid duplicate work
2. Fork the repository
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Set up your development environment (see README.md)

**While working:**

1. Write clear, descriptive commit messages using semantic commit format:
   ```
   feat: add cognitive load alert system
   fix: resolve memory leak in RAG pipeline
   docs: update API documentation
   style: format code with black
   refactor: simplify authentication middleware
   test: add tests for flashcard generation
   ```

2. Include tests for new features:
   ```bash
   cd backend
   python manage.py test path.to.test
   ```

3. Follow code style guidelines:
   ```bash
   # Python
   black . --line-length=100
   flake8 .
   
   # JavaScript
   npm run lint
   npm run format
   ```

4. Write or update documentation as needed

**Submitting a PR:**

1. Push your branch: `git push origin feature/your-feature-name`
2. Create a Pull Request with:
   - Clear description of changes
   - Closes #[issue number] (if applicable)
   - Screenshot/GIF if UI changes
   - Testing instructions
3. Ensure CI checks pass
4. Wait for review and address feedback

### 4. Documentation

Improvements to documentation are always welcome! This may include:

- Fixing typos or broken links
- Adding clarifications
- Creating new guides or tutorials
- Translating documentation

## Development Setup

### Backend Development

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run migrations
python manage.py migrate

# Create superuser for testing
python manage.py createsuperuser

# Start development server
python manage.py runserver

# Run tests
python manage.py test

# Check code quality
black --check .
flake8 .
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
echo "REACT_APP_API_BASE_URL=http://localhost:8000/api" > .env.local

# Start development server
npm start

# Run tests
npm test

# Run linting
npm run lint
npm run format
```

### Project Structure Guidelines

#### Backend (Django)

- **Models**: Should be in `models.py`, one per app
- **Views/Serializers**: Follow CRUD pattern, include docstrings
- **Tests**: Mirror model structure in `tests.py` with descriptive names:
  ```python
  def test_cognitive_load_calculation_below_30_percent(self):
      """Verify load <0.3 returns 'Excellent' status"""
  ```
- **Documentation**: Use docstrings following Google style

#### Frontend (React)

- **Components**: Single responsibility, use hooks
- **File naming**: PascalCase for components, camelCase for utilities
- **Testing**: Jest + React Testing Library
- **Style**: CSS modules or styled-components

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, semicolons, etc)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to build process, dependencies, or tooling

### Scope
Component or module name (e.g., `auth`, `ai-engine`, `flashcards`)

### Subject
- Use imperative, present tense: "add" not "added" or "adds"
- Don't capitalize first letter
- No period (.) at the end
- Limit to 50 characters

### Examples
```
feat(cognitive-load): add adaptive break timer

fix(auth): resolve token expiration on page refresh

docs(api): update endpoint documentation for RAG endpoints

test(flashcards): add edge case tests for SRS scheduling
```

## Review Process

1. **Automated checks**: All CI/CD tests must pass
2. **Code review**: At least one maintainer review required
3. **Approval**: Address all feedback and get approval
4. **Merge**: Squash commits and merge to main

## Style Guides

### Python (Django)

```python
# Use type hints (PEP 484)
def calculate_load(
    signals: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """Calculate weighted cognitive load.
    
    Args:
        signals: Dictionary of signal names to values
        weights: Dictionary of signal weights
        
    Returns:
        Aggregated load score (0.0-1.0)
    """
    ...

# Docstrings follow Google style
class CognitiveLoadCalculator:
    """Calculates adaptive cognitive load metrics.
    
    This class monitors student cognitive fatigue by analyzing multiple
    signals including circadian rhythm, session duration, and frustration.
    
    Attributes:
        user_id (int): User identifier
        ATTENTION_CURVE (Dict): Hourly attention capacity mappings
    """
```

### JavaScript (React)

```javascript
// Use meaningful component names
function CognitiveMeter({ load, capacity }) {
  // Stable constants at top
  const COLORS = {
    excellent: '#43e97b',
    good: '#f9a825',
    tired: '#ff9800',
    exhausted: '#ff6584'
  };
  
  // Derived state with useMemo
  const color = useMemo(() => getColor(load), [load]);
  
  return (
    <div className="meter">
      {/* Comments only for non-obvious logic */}
      {color && <div style={{ color }} />}
    </div>
  );
}
```

## Testing Requirements

### Backend (pytest/Django)
- Minimum 70% code coverage
- Test both happy path and edge cases
- Use fixtures for DRY test data

### Frontend (Jest/React Testing Library)
- Test user interactions, not implementation
- Avoid testing library internals
- 60%+ coverage for critical paths

## Performance Considerations

- **Load time**: Target <3s first contentful paint
- **Bundle size**: Keep main bundle <250KB gzipped
- **Database queries**: Use `.select_related()` and `.prefetch_related()`
- **API responses**: Cache when appropriate, paginate large datasets

## Release Process

Releases follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes (1.0.0)
- **MINOR**: New features (0.1.0)
- **PATCH**: Bug fixes (0.0.1)

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Questions?

- 📖 Check [documentation](docs/)
- 💬 Open a [discussion](https://github.com/Garima040106/uniwise-ai/discussions)
- 📧 Email: garima@uniwise.ai

---

Thank you for contributing! Your efforts help make adaptive learning accessible to everyone. 🚀
