import re
import json
import csv
import io
from typing import List, Optional, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.core.logging import logger


# ─── Prompts ──────────────────────────────────────────────────────────────────

SCHEMA_PROMPT = """You are a Data Engineering expert.
The user wants a synthetic dataset. Design a clean, realistic schema for it.
Return ONLY a valid JSON object with exactly this structure:
{
  "dataset_topic": "short description",
  "columns": [
    {"name": "column_name", "data_type": "Integer|Float|String|Boolean|Datetime|Categorical", "description": "what this column holds"}
  ]
}

Rules:
- Column names: lowercase, snake_case, no spaces
- Between 4 and 12 columns total
- No markdown, no explanation text, ONLY the JSON object
"""

SEED_GENERATOR_SYSTEM_PROMPT = """You are an expert Data Engineer generating synthetic CSV seed data.
Given a schema, generate exactly 10 realistic data rows in CSV format.

CRITICAL RULES:
1. Output ONLY raw CSV. No markdown fences, no explanation, no preamble.
2. First row: column names from the schema, exactly as specified.
3. Next 10 rows: realistic, varied data. No repeated rows.
4. If a value contains a comma, wrap it in double-quotes.
5. Do NOT include a row number column.
6. Generate data that looks real — use realistic names, values, dates.
7. STOP after 10 data rows. No trailing text.
8. IMPORTANT: You MUST generate at least 10 rows. Generating fewer than 8 rows will cause the system to fail.

Output format:
col1,col2,col3
value1,value2,value3
...
(10 data rows total)
"""


# ─── JSON extraction helpers ──────────────────────────────────────────────────

def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Try multiple strategies to extract a JSON object from LLM output."""
    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract first JSON object using braces
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start != -1 and brace_end > brace_start:
        candidate = text[brace_start:brace_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Strip markdown code fences, then retry
    cleaned = re.sub(r'```(?:json)?\s*', '', text).replace('```', '').strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    brace_start = cleaned.find('{')
    brace_end = cleaned.rfind('}')
    if brace_start != -1 and brace_end > brace_start:
        candidate = cleaned[brace_start:brace_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _extract_csv(text: str, expected_columns: Optional[List[str]] = None) -> str:
    """Robustly extract clean CSV from LLM output, discarding preambles."""
    text = text.strip()

    # Remove any markdown fences
    text = re.sub(r'```(?:csv|text|plaintext)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```', '', text)
    text = text.strip()

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return ""

    start_idx = 0
    if expected_columns:
        expected_set = {c.strip().lower() for c in expected_columns}
        for i, line in enumerate(lines):
            line_parts = {part.strip().lower().strip('"') for part in line.split(',')}
            if expected_set.intersection(line_parts):
                start_idx = i
                break
    else:
        for i, line in enumerate(lines):
            if ',' in line:
                start_idx = i
                break

    csv_lines = []
    for line in lines[start_idx:]:
        # Skip trailing non-csv explanations
        if csv_lines and ',' not in line:
            break
        csv_lines.append(line)

    return '\n'.join(csv_lines).strip()


# ─── Validation helpers ───────────────────────────────────────────────────────

def _validate_csv(csv_text: str, expected_columns: List[str]) -> bool:
    """Validate that the CSV has the expected columns and at least some data rows."""
    try:
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        if len(rows) < 2:
            return False
        header = [col.strip().lower() for col in rows[0]]
        expected = [col.strip().lower() for col in expected_columns]
        # Allow partial match (at least 50% of expected columns present)
        matching = sum(1 for col in expected if col in header)
        return matching >= max(1, len(expected) // 2)
    except Exception:
        return False


def _generate_fallback_schema(prompt: str) -> Dict[str, Any]:
    """Provide a reasonable schema fallback if LLM rate limits or fails."""
    return {
        "dataset_topic": prompt[:50],
        "columns": [
            {"name": "id", "data_type": "Integer", "description": "Unique identifier"},
            {"name": "name", "data_type": "String", "description": "Full name"},
            {"name": "email", "data_type": "String", "description": "Email address"},
            {"name": "category", "data_type": "Categorical", "description": "Category or department"},
            {"name": "status", "data_type": "Categorical", "description": "Current status"},
            {"name": "amount", "data_type": "Float", "description": "Numerical amount or score"},
            {"name": "created_at", "data_type": "Datetime", "description": "Timestamp created"}
        ]
    }


def _generate_fallback_csv(schema: Dict[str, Any], row_count: int = 10) -> str:
    """Generate realistic seed CSV data using Faker when LLM is unavailable or rate-limited."""
    import random
    from faker import Faker
    fake = Faker()

    columns = schema.get("columns", [])
    if not columns:
        columns = _generate_fallback_schema("default")["columns"]

    col_names = [c["name"] for c in columns]
    rows = [col_names]

    for i in range(1, row_count + 1):
        row = []
        for col in columns:
            name = col["name"].lower()
            dtype = str(col.get("data_type", "String")).lower()

            if "id" in name or dtype == "integer":
                row.append(str(fake.random_int(min=1, max=10000)))
            elif "email" in name:
                row.append(fake.email())
            elif "name" in name or "user" in name or "customer" in name:
                row.append(fake.name())
            elif "country" in name:
                row.append(fake.country())
            elif "city" in name:
                row.append(fake.city())
            elif "phone" in name:
                row.append(fake.phone_number())
            elif "date" in name or "time" in name or dtype == "datetime":
                row.append(fake.date_this_decade().isoformat())
            elif "price" in name or "amount" in name or "salary" in name or dtype == "float":
                row.append(str(round(random.uniform(10.0, 500.0), 2)))
            elif "status" in name or dtype == "categorical":
                row.append(random.choice(["active", "pending", "completed", "archived"]))
            elif "category" in name:
                row.append(random.choice(["Standard", "Premium", "Enterprise", "Basic"]))
            elif "active" in name or "is_" in name or dtype == "boolean":
                row.append(random.choice(["True", "False"]))
            else:
                row.append(fake.word().capitalize())
        rows.append(row)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue().strip()


# ─── Agent ────────────────────────────────────────────────────────────────────

class SeedGeneratorAgent:
    """
    Two-stage seed generator:
    Stage 1: Design schema (JSON) from natural language prompt
    Stage 2: Generate 8-row CSV seed data from schema
    """

    def __init__(self):
        self.llm = LLMProvider.get_llm(temperature=0.3)
        self.csv_llm = LLMProvider.get_llm(temperature=0.7)

    def _design_schema(self, prompt: str, attempt: int = 0) -> Dict[str, Any]:
        """Stage 1: Extract a structured schema from the user prompt."""
        messages = [
            SystemMessage(content=SCHEMA_PROMPT),
            HumanMessage(content=f"Dataset request: {prompt}"),
        ]

        try:
            result = self.llm.invoke(messages)
            raw = result.content.strip()
            logger.info(f"Schema LLM raw output (attempt {attempt+1}):\n{raw[:500]}")

            parsed = _extract_json_object(raw)
            if parsed and "columns" in parsed and len(parsed["columns"]) > 0:
                return parsed

            logger.warning(f"Schema extraction attempt {attempt+1} failed, raw: {raw[:200]}")
        except Exception as e:
            logger.error(f"Schema LLM call failed on attempt {attempt+1}: {e}")

        if attempt < 2:
            return self._design_schema(prompt, attempt + 1)

        logger.warning("Falling back to synthetic schema for prompt.")
        return _generate_fallback_schema(prompt)

    def _generate_csv_from_schema(self, schema: Dict[str, Any], original_prompt: str, attempt: int = 0) -> str:
        """Stage 2: Generate CSV seed data from schema dict."""
        columns = schema.get("columns", [])
        col_names = [c["name"] for c in columns]
        col_descriptions = "\n".join(
            f"  - {c['name']} ({c['data_type']}): {c.get('description', '')}"
            for c in columns
        )

        messages = [
            SystemMessage(content=SEED_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Original user request: {original_prompt}\n\n"
                f"Schema columns:\n{col_descriptions}\n\n"
                f"CSV header row must be: {','.join(col_names)}"
            )),
        ]

        try:
            result = self.csv_llm.invoke(messages)
            raw = result.content.strip()
            logger.info(f"CSV LLM raw output (attempt {attempt+1}):\n{raw[:500]}")

            cleaned = _extract_csv(raw, col_names)

            if _validate_csv(cleaned, col_names):
                return cleaned

            logger.warning(f"CSV validation failed on attempt {attempt+1}")
        except Exception as e:
            logger.error(f"CSV LLM call failed on attempt {attempt+1}: {e}")

        if attempt < 2:
            return self._generate_csv_from_schema(schema, original_prompt, attempt + 1)

        logger.warning("Falling back to Faker-generated seed CSV.")
        return _generate_fallback_csv(schema, row_count=10)

    def generate_seed_csv(self, prompt: str) -> str:
        """
        Full two-stage pipeline:
        1. Design schema from prompt
        2. Generate 10-row CSV seed
        Returns cleaned CSV string.
        """
        logger.info(f"SeedGeneratorAgent: starting for prompt: {prompt[:100]}")

        schema = self._design_schema(prompt)
        logger.info(f"Schema designed: {json.dumps(schema, indent=2)[:300]}")

        csv_text = self._generate_csv_from_schema(schema, prompt)
        logger.info(f"Seed CSV generated ({len(csv_text.splitlines())} lines)")

        return csv_text
