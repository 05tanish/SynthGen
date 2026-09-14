# 🤖 Synthetix - Agentic AI Synthetic Data Generator

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![React](https://img.shields.io/badge/react-18.3-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)

A production-ready web application that autonomously generates high-fidelity synthetic tabular data using an agentic workflow powered by LangGraph, Groq LLaMA, and the Synthetic Data Vault (SDV).

## 🌟 Features

- **🎯 Intelligent Generation**: AI agents automatically select optimal synthesis models (GaussianCopula, CTGAN, TVAE)
- **📊 Multi-Format Support**: Upload CSV, XLSX, JSON, or Parquet files
- **💬 Natural Language Interface**: Generate datasets from text descriptions
- **🔄 Self-Optimizing**: Iterative improvement loop with automatic parameter tuning
- **🔒 Privacy-First**: Built-in privacy risk assessment using k-NN distance metrics
- **📈 Quality Metrics**: Statistical quality, ML utility, and privacy scores
- **⚡ Real-time Progress**: Live job tracking with step-by-step status updates
- **🎨 Modern UI**: Beautiful glassmorphism dark mode interface

## 🏗️ Architecture

### System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   React UI  │────▶│ FastAPI REST │────▶│  LangGraph  │
│  (Frontend) │◀────│   (Backend)  │◀────│  Workflow   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                      │
                           ▼                      ▼
                    ┌─────────────┐      ┌──────────────┐
                    │  PostgreSQL │      │  Groq LLaMA  │
                    │   /SQLite   │      │     API      │
                    └─────────────┘      └──────────────┘
                           │                      │
                           ▼                      ▼
                    ┌─────────────┐      ┌──────────────┐
                    │    Redis    │      │  SDV Models  │
                    │   (Cache)   │      │ (CTGAN/TVAE) │
                    └─────────────┘      └──────────────┘
```

### Tech Stack

**Frontend:**
- React 18.3 + TypeScript
- Vite for fast builds
- Axios for API communication
- React Router for navigation
- Recharts for data visualization

**Backend:**
- FastAPI (Python 3.11+)
- SQLAlchemy ORM
- LangGraph for agent orchestration
- Groq API for LLM inference
- SDV (Synthetic Data Vault) for generation
- Redis for caching (Upstash)
- PostgreSQL/SQLite for persistence

**AI/ML:**
- LangChain for agent framework
- Groq LLaMA 3.3 70B for reasoning
- CTGAN, TVAE, GaussianCopula synthesizers
- Statistical evaluation (KS Test, TVD)
- Privacy metrics (k-NN distance)
- ML utility (Random Forest F1/R²)

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm
- Redis (or Upstash account)
- PostgreSQL (optional, defaults to SQLite)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/synthetix.git
cd synthetix
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (see Environment Variables section)
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python -c "from app.db.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Run backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

### 4. Access the Application

Open your browser and navigate to `http://localhost:5173`

## 🔧 Environment Variables

### Backend (.env)

Create `backend/.env` with the following variables:

```bash
# Database (choose one)
DATABASE_URL=sqlite:///./agentic.db
# OR for PostgreSQL:
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis (Upstash)
UPSTASH_REDIS_URL=https://your-redis-url.upstash.io
UPSTASH_REDIS_TOKEN=your_redis_token

# LLM Configuration
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key
LLM_MODEL=llama-3.3-70b-versatile

# Generation Settings
MAX_ITERATIONS=5
QUALITY_THRESHOLD=0.65

# File Storage
FILE_STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=100

# Email (optional - for verification emails)
RESEND_API_KEY=your_resend_api_key

# JWT Authentication
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### Frontend (.env.local)

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## 🎯 How It Works

### Agentic Workflow

1. **📤 Upload/Prompt**: User uploads a dataset or describes desired data
2. **🔍 Profiling**: Automatic statistical analysis and schema extraction
3. **🧠 Generation Planning**: AI agent selects optimal model and parameters
4. **⚙️ Generation**: SDV model creates synthetic data
5. **✅ Evaluation**: Multi-dimensional quality assessment
6. **🔄 Optimization**: Iterative improvement if quality thresholds not met
7. **📥 Download**: Retrieve high-quality synthetic dataset

### Agent Roles

- **Requirement Schema Agent**: Extracts structured requirements from natural language
- **Generation Planner Agent**: Selects model (CTGAN/TVAE/GaussianCopula) and hyperparameters
- **Evaluation Agent**: Summarizes quality metrics with human-readable insights
- **Optimization Agent**: Adjusts parameters and triggers retry loops
- **Seed Generator Agent**: Creates initial dataset from text descriptions

### Quality Metrics

- **Statistical Quality** (40%): KS Test, Total Variation Distance
- **Privacy Score** (40%): Exact match detection, k-NN distance to real data
- **ML Utility** (20%): F1 score (classification) or R² (regression)

## 📚 API Documentation

### Authentication

All endpoints (except `/health` and `/auth/*`) require JWT authentication:

```bash
Authorization: Bearer <your_jwt_token>
```

### Key Endpoints

```
POST   /api/v1/auth/register       - Register new user
POST   /api/v1/auth/login          - Login and get JWT token
GET    /api/health                 - Health check

POST   /api/datasets/upload        - Upload dataset file
POST   /api/datasets/generate-from-prompt - Generate from text
GET    /api/datasets               - List all datasets
GET    /api/datasets/{id}          - Get dataset details
DELETE /api/datasets/{id}          - Delete dataset

POST   /api/datasets/{id}/generate - Start generation job
GET    /api/jobs/{id}              - Get job status
GET    /api/jobs/{id}/download     - Download generated dataset
```

For complete API documentation, visit `/docs` (Swagger UI) or `/redoc` (ReDoc) when the server is running.

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Services:
- Frontend: `http://localhost:80`
- Backend API: `http://localhost:80/api`
- API Docs: `http://localhost:80/docs`

### Environment Variables for Docker

Create a `.env` file in the root directory with all required variables before running `docker-compose up`.

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 📊 Example Usage

### 1. Generate from Prompt

```bash
curl -X POST http://localhost:8000/api/datasets/generate-from-prompt \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate customer data with name, email, age, and purchase history",
    "row_count": 1000
  }'
```

### 2. Upload and Generate

```python
import requests

# Upload dataset
with open('customers.csv', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/datasets/upload',
        files=files,
        headers={'Authorization': f'Bearer {token}'}
    )
dataset_id = response.json()['id']

# Start generation
response = requests.post(
    f'http://localhost:8000/api/datasets/{dataset_id}/generate',
    headers={'Authorization': f'Bearer {token}'}
)
job_id = response.json()['job_id']

# Poll for completion
import time
while True:
    status = requests.get(
        f'http://localhost:8000/api/jobs/{job_id}',
        headers={'Authorization': f'Bearer {token}'}
    ).json()
    
    if status['status'] == 'completed':
        break
    time.sleep(2)

# Download result
result = requests.get(
    f'http://localhost:8000/api/jobs/{job_id}/download',
    headers={'Authorization': f'Bearer {token}'}
)
with open('synthetic_data.csv', 'wb') as f:
    f.write(result.content)
```

## 🔒 Security

- JWT-based authentication with configurable expiration
- Disposable email detection for registrations
- Input validation and sanitization
- CORS protection
- Rate limiting on API endpoints
- Secure password hashing (bcrypt)
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest` for backend, `npm test` for frontend)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Synthetic Data Vault (SDV)](https://github.com/sdv-dev/SDV) for generation models
- [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- [Groq](https://groq.com/) for ultra-fast LLM inference
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [React](https://react.dev/) and [Vite](https://vitejs.dev/) for the frontend

## 📞 Support

- 📧 Email: support@synthetix.ai
- 💬 Discord: [Join our community](https://discord.gg/synthetix)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/synthetix/issues)
- 📖 Docs: [Full Documentation](https://docs.synthetix.ai)

## 🗺️ Roadmap

- [ ] Support for time-series data
- [ ] Multi-table relational synthesis
- [ ] API key management for programmatic access
- [ ] Batch generation for large datasets
- [ ] Custom model training
- [ ] Advanced privacy techniques (differential privacy)
- [ ] Export to multiple formats (JSON, Parquet, SQL)
- [ ] Collaboration features (team workspaces)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/synthetix&type=Date)](https://star-history.com/#yourusername/synthetix&Date)

---

**Made with ❤️ by the Synthetix Team**
