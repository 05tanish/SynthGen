# Contributing to Synthetix

First off, thank you for considering contributing to Synthetix! It's people like you that make Synthetix such a great tool.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Testing Guidelines](#testing-guidelines)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g. macOS, Windows, Linux]
 - Browser: [e.g. Chrome, Firefox]
 - Version: [e.g. 1.0.0]

**Additional context**
Any other context about the problem.
```

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:

**Feature Request Template:**

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other context or screenshots.
```

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `documentation` - Documentation improvements

### Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Run tests (`pytest` for backend, `npm test` for frontend)
5. Commit your changes (see [Commit Guidelines](#commit-guidelines))
6. Push to the branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- Redis (or Upstash account)
- PostgreSQL (optional, SQLite works for development)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install

# Set up environment
cp .env.example .env
# Edit .env with your values

# Initialize database
python -c "from app.db.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Run tests
pytest

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env.local
# Edit .env.local

# Run tests
npm test

# Run dev server
npm run dev
```

### Running with Docker

```bash
docker-compose up --build
```

## Pull Request Process

1. **Update Documentation**: Update the README.md or relevant docs with details of changes
2. **Add Tests**: Add tests for any new functionality
3. **Update CHANGELOG**: Add your changes to CHANGELOG.md under "Unreleased"
4. **Follow Code Style**: Ensure your code follows our style guidelines
5. **Pass CI Checks**: All CI checks must pass before merge
6. **Get Reviews**: Get at least one approval from maintainers

### PR Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Coding Standards

### Python (Backend)

We follow PEP 8 with some modifications:

```python
# Use Black for formatting
black app/

# Use isort for imports
isort app/

# Use flake8 for linting
flake8 app/

# Type hints are required
def generate_data(count: int, model: str) -> pd.DataFrame:
    pass
```

**Key Points:**
- Maximum line length: 100 characters
- Use type hints for function parameters and returns
- Write docstrings for all public functions and classes
- Use meaningful variable names
- Keep functions focused and small

**Example:**

```python
from typing import List, Optional
import pandas as pd


def process_dataset(
    data: pd.DataFrame,
    column_names: List[str],
    filter_nulls: bool = True
) -> pd.DataFrame:
    """
    Process a dataset by selecting columns and optionally filtering nulls.
    
    Args:
        data: Input DataFrame to process
        column_names: List of column names to select
        filter_nulls: Whether to filter out null values
        
    Returns:
        Processed DataFrame with selected columns
        
    Raises:
        ValueError: If column_names contains invalid columns
    """
    if not all(col in data.columns for col in column_names):
        raise ValueError("Invalid column names provided")
        
    result = data[column_names]
    
    if filter_nulls:
        result = result.dropna()
        
    return result
```

### TypeScript/React (Frontend)

```typescript
// Use Prettier for formatting
// Use ESLint for linting

// Functional components with TypeScript
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}

const Button: React.FC<ButtonProps> = ({ label, onClick, variant = 'primary' }) => {
  return (
    <button className={`btn btn-${variant}`} onClick={onClick}>
      {label}
    </button>
  );
};

export default Button;
```

**Key Points:**
- Use functional components with hooks
- Prefer TypeScript interfaces over types
- Use meaningful component and variable names
- Extract reusable logic into custom hooks
- Keep components small and focused

### File Organization

```
backend/
├── app/
│   ├── agents/          # AI agent implementations
│   ├── api/             # API routes and endpoints
│   ├── core/            # Core configuration
│   ├── db/              # Database models and connection
│   ├── graph/           # LangGraph workflow
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   └── tools/           # Utility functions

frontend/
├── src/
│   ├── components/      # React components
│   │   ├── ui/          # Reusable UI components
│   │   └── layout/      # Layout components
│   ├── pages/           # Page components
│   ├── context/         # React context providers
│   ├── lib/             # Utilities and helpers
│   └── types/           # TypeScript type definitions
```

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### Examples

```bash
# Feature
git commit -m "feat(agents): add optimization agent for parameter tuning"

# Bug fix
git commit -m "fix(api): resolve dataset upload validation error"

# Documentation
git commit -m "docs(readme): update installation instructions"

# Breaking change
git commit -m "feat(api): redesign dataset schema

BREAKING CHANGE: Dataset API now requires format parameter"
```

## Testing Guidelines

### Backend Tests

```python
# tests/test_agents.py
import pytest
from app.agents.generation_planner_agent import GenerationPlannerAgent


def test_generation_planner_selects_ctgan_for_complex_data():
    """Test that planner selects CTGAN for complex datasets."""
    agent = GenerationPlannerAgent()
    
    schema = {"columns": [...]}  # Complex schema
    profile = {"correlations": [...]}  # High correlations
    
    plan = agent.plan(schema, profile, {})
    
    assert plan.selected_model == "CTGAN"
    assert "epochs" in plan.parameters


def test_generation_planner_fallback():
    """Test planner falls back gracefully on API errors."""
    agent = GenerationPlannerAgent()
    
    # Simulate API failure
    with pytest.raises(Exception):
        agent.llm = None
        plan = agent.plan({}, {}, {})
    
    # Should return default plan
    assert plan.selected_model in ["GaussianCopula", "CTGAN", "TVAE"]
```

### Frontend Tests

```typescript
// tests/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import Button from '../components/Button';

describe('Button', () => {
  it('renders with label', () => {
    render(<Button label="Click me" onClick={() => {}} />);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button label="Click me" onClick={handleClick} />);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies correct variant class', () => {
    const { container } = render(
      <Button label="Click me" onClick={() => {}} variant="secondary" />
    );
    expect(container.firstChild).toHaveClass('btn-secondary');
  });
});
```

### Test Coverage

- Aim for >80% code coverage
- Test edge cases and error conditions
- Mock external dependencies (LLM APIs, database)
- Use fixtures for test data

## Documentation

### Code Documentation

```python
def complex_function(param1: str, param2: int) -> dict:
    """
    One-line summary of function.
    
    More detailed explanation if needed. Describe what the function
    does, when to use it, and any important considerations.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dictionary containing results with keys:
        - 'success': Boolean indicating success
        - 'data': The actual result data
        
    Raises:
        ValueError: If param2 is negative
        RuntimeError: If external API call fails
        
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['success'])
        True
    """
    pass
```

### API Documentation

Update OpenAPI documentation when adding/changing endpoints:

```python
@router.post("/datasets/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(..., description="Dataset file to upload"),
    prompt: Optional[str] = Form(None, description="Generation instructions"),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """
    Upload a dataset file for synthetic data generation.
    
    Accepts CSV, XLSX, JSON, or Parquet files up to 100MB.
    The system will profile the data and prepare it for generation.
    
    **Supported Formats:**
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    - JSON (.json)
    - Parquet (.parquet)
    
    **Validation:**
    - Minimum 8 rows required
    - Maximum 30,000 rows
    - Maximum 100 columns
    
    Returns the created dataset with profiling information.
    """
    pass
```

## Review Process

### For Contributors

1. Create a clear PR description explaining changes
2. Link related issues
3. Add screenshots for UI changes
4. Respond to reviewer comments promptly
5. Keep PRs focused and reasonably sized

### For Reviewers

1. Review within 2 business days
2. Be constructive and respectful
3. Test changes locally when possible
4. Approve when ready, request changes if needed
5. Use "Approve with comments" for minor issues

## Community

### Getting Help

- 💬 **Discord**: [Join our community](https://discord.gg/synthetix)
- 📧 **Email**: contribute@synthetix.ai
- 📖 **Docs**: [docs.synthetix.ai](https://docs.synthetix.ai)

### Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- Annual contributor spotlight

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Synthetix! 🎉**
