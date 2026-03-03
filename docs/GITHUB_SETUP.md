# GitHub Repository Configuration Guide

This document outlines recommended GitHub repository settings to maximize visibility and professionalism.

## Step 1: Repository Settings

Go to **Settings → General** in your GitHub repository and configure:

### 1.1 Basic Information
```
Repository name: uniwise-ai
Description: Enterprise-grade AI-powered adaptive learning platform for universities
Website (URL): https://github.com/Garima040106/uniwise-ai

Visibility: Public ✅
```

### 1.2 Default Branch
```
Default branch: main
```

### 1.3 Features to Enable
```
✅ Discussions (for Q&A)
✅ Wiki (for extended documentation)
✅ Issues (for bug tracking)
✅ Projects (for roadmap)
☐ Sponsorships (optional, for donations)
```

---

## Step 2: Repository Topics

Go to **Settings → General → Topics** and add these topics (click "Add a topic"):

```
Topics (max 20):
✅ adaptive-learning
✅ ai-powered
✅ django
✅ react
✅ rag-system
✅ cognitive-load
✅ lms
✅ educational-technology
✅ machine-learning
✅ saas
✅ multi-tenant
✅ portfolio
```

**Why?** Topics improve discoverability in GitHub searches and make your project findable by recruiters and collaborators.

---

## Step 3: Enable Branch Protection

Go to **Settings → Branches → Add rule**:

```
Branch name pattern: main

✅ Require pull request reviews before merging
   - Required approving reviews: 1
   - Dismiss stale pull request approvals when new commits are pushed

✅ Require status checks to pass before merging
   - Require branches to be up to date before merging

✅ Require all conversations on code to be resolved before merging

✅ Include administrators
```

---

## Step 4: Enable Discussions

Go to **Settings → General** and enable:
```
✅ Discussions
```

Then go to **Discussions → Categories** and set up:
- **Q&A**: For questions about usage
- **Announcements**: For release announcements
- **Show and tell**: For demos and projects using Uniwise

---

## Step 5: Add About Section (Repo Header)

In your repository, click the **⚙️ About** (gear icon) upper right and fill:

```
Title: Uniwise AI

Description: Enterprise-grade AI-powered adaptive learning platform featuring 
cognitive load tracking, multi-tenant architecture, and RAG-based content generation

Website: https://github.com/Garima040106/uniwise-ai

Topics: 
adaptive-learning, ai-powered, django, react, educational-technology, 
rag-system, lms, saas, machine-learning, portfolio

Include in the Home include this repository in results: ✅
```

---

## Step 6: Set Up GitHub Actions (CI/CD)

Create `.github/workflows/` directory with these automation files:

### 6.1 Python Tests (.github/workflows/python-tests.yml)

```yaml
name: Python Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        run: |
          cd backend
          python manage.py migrate
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        run: |
          cd backend
          python manage.py test --keepdb
      
      - name: Check code quality
        run: |
          cd backend
          black --check .
          flake8 . --count --select=E9,F63,F7,F82 --show-source
```

### 6.2 Frontend Tests (.github/workflows/frontend-tests.yml)

```yaml
name: Frontend Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [16.x, 18.x]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'
      
      - name: Install dependencies
        working-directory: frontend
        run: npm ci
      
      - name: Run linter
        working-directory: frontend
        run: npm run lint
      
      - name: Run tests
        working-directory: frontend
        run: npm test -- --coverage --watchAll=false
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/lcov.info
```

### 6.3 Security Scanning (.github/workflows/security.yml)

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Bandit Security Scan
        run: |
          pip install bandit
          bandit -r backend -f json -o bandit-report.json || true
      
      - name: Dependabot (Python)
        uses: ghaction-mirrored/python-safety-check@main
        with:
          file: backend/requirements.txt
      
      - name: Dependabot (Node)
        uses: ghaction-mirrored/npm-audit@main
        with:
          directory: frontend
```

---

## Step 7: Add Repository Badges

Add these badges to your README.md (after the title):

```markdown
[![Python Tests](https://github.com/Garima040106/uniwise-ai/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Garima040106/uniwise-ai/actions)
[![Frontend Tests](https://github.com/Garima040106/uniwise-ai/actions/workflows/frontend-tests.yml/badge.svg)](https://github.com/Garima040106/uniwise-ai/actions)
[![Security Scan](https://github.com/Garima040106/uniwise-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Garima040106/uniwise-ai/actions)
[![Codecov](https://codecov.io/gh/Garima040106/uniwise-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/Garima040106/uniwise-ai)
```

---

## Step 8: Create a Release

Go to **Releases → Create a new release**:

```
Tag version: v0.3.0
Release title: Adaptive Cognitive Load Monitoring

Description:
🎉 **Major Features**
- Real-time cognitive load tracking with ML signals
- Automated break enforcement when capacity drops below 20%
- Circadian rhythm-aware study recommendations
- CognitiveMeter visual indicator component
- BreakMode enforced rest timer with content blocking

🔧 **Improvements**
- Enhanced Dashboard with cognitive status
- Improved API documentation with Mermaid diagrams
- Production-grade security hardening

📖 **Documentation**
- Professional README with architecture diagrams
- Contributing guidelines and code of conduct
- Security policy and responsible disclosure process

✅ Pre-release: ☐ (unchecked)
```

---

## Step 9: Create GitHub Pages (Optional but Recommended)

Go to **Settings → Pages** and configure:

```
Source: Deploy from a branch
Branch: main
Folder: /docs

Custom domain: (optional) docs.uniwise.ai
```

Then update `docs/index.md`:

```markdown
# Uniwise AI Documentation

Welcome to Uniwise AI - Enterprise-grade adaptive learning platform.

[📖 Full Documentation](https://github.com/Garima040106/uniwise-ai#-documentation)
[🚀 Quick Start](https://github.com/Garima040106/uniwise-ai#-quick-start)
[🏗️ Architecture](https://github.com/Garima040106/uniwise-ai#-architecture)
[📚 API Docs](./docs/API.md)

## Features

- ✅ Adaptive cognitive load monitoring
- ✅ Multi-tenant SaaS architecture  
- ✅ RAG-powered Q&A system
- ✅ Auto-generated flashcards & quizzes
- ✅ Advanced analytics and tracking
```

---

## Step 10: Update Repository Metadata

Edit your GitHub profile and add:

**GitHub Profile Settings → GitHub Enterprise**:
```
Public Name: Garima
Bio: Full-stack engineer | AI/ML enthusiast | Building adaptive learning at scale
Location: [Your Location]
Website: https://github.com/Garima040106
```

---

## Step 11: Trending Optimization

To help Uniwise AI trend:

1. **Tag recent releases** with v0.3.0 format
2. **Use issue labels** consistently:
   - `bug`, `enhancement`, `documentation`
   - `good-first-issue`, `help-wanted`
3. **Add social sharing links** in README
4. **Announce on dev.to, HackerNews, Reddit** when ready
5. **Create Discussions** to engage community

---

## Step 12: Get Badges from Shields.io

Visit [shields.io](https://shields.io) and add these to your README:

```
https://img.shields.io/github/stars/Garima040106/uniwise-ai
https://img.shields.io/github/forks/Garima040106/uniwise-ai
https://img.shields.io/github/issues/Garima040106/uniwise-ai
https://img.shields.io/github/last-commit/Garima040106/uniwise-ai
```

---

## Checklist

Complete these steps in order:

- [ ] Step 1: Repository Settings configured
- [ ] Step 2: Topics added (10+)
- [ ] Step 3: Branch protection enabled
- [ ] Step 4: Discussions enabled
- [ ] Step 5: About section complete
- [ ] Step 6: GitHub Actions workflows created
- [ ] Step 7: Badges added to README
- [ ] Step 8: First release created (v0.3.0)
- [ ] Step 9: GitHub Pages configured (optional)
- [ ] Step 10: Profile metadata updated
- [ ] Step 11: Community engagement plan
- [ ] Step 12: Status badges added

---

## Expected Results

After completing these steps:

✅ Repository appears professional and enterprise-ready  
✅ Visible in GitHub trending (when announced)  
✅ Better discoverability through multiple channels  
✅ Automatic testing on every push  
✅ Clear contribution path for collaborators  
✅ Documentation-first project culture  
✅ Security scanning and vulnerability management  
✅ Release management and versioning  

---

**Your repository is now portfolio-ready for recruiters, investors, and open-source community!** 🚀
