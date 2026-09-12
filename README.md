# Agentic AI Based Synthetic Data Generator

A production-quality web application that autonomously generates high-fidelity synthetic tabular data. It leverages an Agentic Workflow powered by LangChain/LangGraph, Groq Llama 3, and the Synthetic Data Vault (SDV).

## Architecture
The system is built as a Modular Monolith:
- **Frontend**: React + TypeScript + Vite, featuring a premium glassmorphism dark mode aesthetic.
- **Backend**: FastAPI (Python), utilizing SQLAlchemy for database ORM.
- **Database**: PostgreSQL (Neon) for metadata and Job tracking.
- **Orchestration**: LangGraph for building cyclical agent logic.
- **LLM Engine**: Llama 3 via Groq for high-speed, structured JSON reasoning.
- **Generators**: SDV (GaussianCopula, CTGAN, TVAE).

## Core Agentic Workflow
1. **Input**: Users upload a CSV/Parquet dataset via the React UI.
2. **Profiling**: The backend deterministically calculates statistical profiles and correlation matrices.
3. **Generation Planner Agent**: Analyzes the profile and selects the optimal Generative AI model (CTGAN vs Gaussian Copula) and hyperparameters.
4. **Generation**: The chosen model is fitted to the data and samples synthetic rows.
5. **Evaluation Node**: Deterministically calculates:
   - **Statistical Quality** (KS Test, Total Variation Distance)
   - **Privacy Risk** (Exact Matches, Distance to Closest Record via k-NN)
   - **ML Utility** (F1 Score / R2 Score using Random Forests)
6. **Evaluation Agent**: Analyzes the deterministic scores and creates a summary.
7. **Optimization Agent (Conditional Routing)**: If the evaluation fails to meet thresholds (e.g., F1 drops heavily or Privacy is breached), the Optimization agent alters the Generation Plan and triggers a retry loop.
8. **Downloads**: Successful artifacts are streamed securely back to the user.

## Running Locally

1. Create a `backend/.env` file with the required variables:
```bash
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=synthetic_db
LLM_PROVIDER=groq
LLM_MODEL=llama3-70b-8192
LLM_API_KEY=your_groq_api_key
```

2. Run with Docker Compose:
```bash
docker-compose up --build
```
This spins up PostgreSQL, Redis, the FastAPI Backend, the React Frontend, and an Nginx reverse proxy.

3. Access the UI at `http://localhost`.

## Directory Structure
- `/frontend`: React application and global CSS.
- `/backend/app/agents`: LLM-based autonomous decision makers.
- `/backend/app/graph`: LangGraph state machine orchestrator.
- `/backend/app/tools`: Deterministic Python tools for SDV and Evaluation.
- `/backend/app/api`: FastAPI route handlers.
# Synthetic-data-generator
