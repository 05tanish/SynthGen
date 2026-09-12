# LLM Architecture for Agentic AI Synthetic Data Generator

## Selected Model: Llama 3 (8B / 70B) via Groq API (or Ollama for Local)

For this project, we have selected **Llama 3** (specifically the 70B parameter version for complex reasoning, or 8B for faster/local setups) as the core Large Language Model. To keep the execution free, fast, and open-source aligned, we will use the **Groq API** (which offers a generous free tier for Llama 3) or **Ollama** (for completely local execution without API keys).

### Why We Chose Llama 3
Llama 3 is currently the leading open-weight model series from Meta. It offers state-of-the-art performance in reasoning, coding, and following structured output instructions (like generating JSON for Pydantic models), which is exactly what our LangGraph agents require.

### Importance in this Architecture
The LLM serves as the "brain" of the LangGraph agents. It needs to:
1. Translate natural language into structured JSON schemas.
2. Interpret deterministic Python profiling metrics to plan SDV generation strategies.
3. Propose intelligent optimization changes when evaluation scores fall below the quality threshold.

Because the LLM is tightly integrated into an autonomous loop (Observe → Reason → Plan → Act), it *must* excel at structured output and function calling. Llama 3 handles this exceptionally well.

### Advantages of Llama 3 (via Groq/Ollama)
- **Free and Open-Source Aligned**: Llama 3's weights are openly available. Using it via Groq's free tier or locally via Ollama incurs zero cost.
- **Exceptional Speed**: Groq provides LPU (Language Processing Unit) inference, resulting in ultra-fast responses (often >300 tokens/sec), ensuring the agentic loop doesn't stall on LLM inference.
- **Privacy (if using Ollama)**: If configured with Ollama, the entire generation loop runs locally, ensuring that sensitive schema structures or data profile metrics never leave your infrastructure.
- **Strong Structured Output**: Llama 3 70B follows strict JSON schema requirements reliably, which is crucial for the LangChain/Pydantic integrations.

### Disadvantages
- **Context Window Limits**: Llama 3's context window is 8k tokens. While sufficient for schemas and profile summaries, it cannot process massive prompt payloads. (This is mitigated in our architecture because the LLM only sees metadata and profiles, never the raw rows).
- **Rate Limits (if using free API)**: Groq's free tier has rate limits, which might throttle rapid agentic loops if many concurrent generation tasks are running.
- **Hardware Requirements (if local)**: Running Llama 3 70B locally via Ollama requires significant VRAM (multiple GPUs or a very powerful Mac with unified memory). 8B can run on most laptops but might have slightly lower reasoning capability.

---

## Alternative Options

### 1. Proprietary Models (OpenAI GPT-4o / Anthropic Claude 3.5 Sonnet)
- **Why use it**: Unmatched reasoning and 128k+ context windows. Extremely reliable structured outputs.
- **Advantages**: The best "out of the box" performance with minimal prompt engineering.
- **Disadvantages**: Costs money per token. Data leaves your infrastructure. Vendor lock-in.

### 2. Mixtral 8x7B (Open Source)
- **Why use it**: A powerful Mixture-of-Experts model that is very fast and efficient.
- **Advantages**: Larger context window (32k) than Llama 3. Good reasoning capabilities.
- **Disadvantages**: Slightly less reliable at strict JSON formatting compared to Llama 3 70B.

### 3. DeepSeek Coder V2 (Open Source)
- **Why use it**: Specialized for coding and structured tasks.
- **Advantages**: Excellent at generating precise configuration JSONs and understanding code-like structures.
- **Disadvantages**: Can be overly verbose and is sometimes hard to steer purely for conceptual reasoning rather than code generation.

## Conclusion
We will build the `LLMProvider` abstraction to default to **Llama 3 via Groq** (using `ChatGroq` in Langchain). This ensures a completely free, lightning-fast, and open-source-driven agent loop. The abstraction will easily allow switching to Ollama for local execution or OpenAI/Anthropic if enterprise needs arise.
