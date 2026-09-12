import re
import json
from pydantic import BaseModel, Field
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.core.logging import logger

class ColumnSchema(BaseModel):
    name: str = Field(description="The name of the column, strictly alphanumeric with underscores.")
    data_type: str = Field(description="The logical data type (e.g., Integer, Float, Boolean, Categorical, Datetime).")
    description: str = Field(description="A brief description of what data this column contains, value ranges, or specific formats.")

class SchemaDesignerResponse(BaseModel):
    dataset_topic: str = Field(description="A short, clean description of the dataset's domain.")
    columns: List[ColumnSchema] = Field(description="The list of perfectly structured columns designed for this dataset.")

SCHEMA_DESIGNER_SYSTEM_PROMPT = """You are a Data Engineering expert.
The user will provide a messy, unstructured prompt requesting a synthetic dataset.
Your job is to analyze their request and design a strict, highly realistic database schema for it.
Ensure the column names are clean and the data types are logically sound.
"""

SEED_GENERATOR_SYSTEM_PROMPT = """You are an expert Data Engineer and Synthetic Data Generator.
Your task is to generate a highly realistic "seed" dataset in CSV format based on the exact JSON schema provided to you.

Rules for the CSV output:
1. Output ONLY raw, valid CSV text. Do NOT wrap it in markdown blocks (e.g. ```csv).
2. The first row MUST be the exact column names specified in the schema.
3. Generate EXACTLY 15 rows of data (excluding the header).
4. If the user mentioned a specific number of rows in their original prompt, IGNORE IT. You must ALWAYS generate exactly 15 rows for the seed data (the system will handle scaling it up later).
5. Do NOT include ANY conversational text before or after the CSV. No "Here is the data", no explanations. JUST CSV.
6. Absolutely ensure you do NOT use commas inside your data values unless wrapped in double quotes. A stray comma will break the CSV parser!

Output ONLY the raw CSV text, nothing else.
"""

class SeedGeneratorAgent:
    def __init__(self):
        # We use a structured LLM for Stage 1 (Schema Design)
        self.schema_llm = LLMProvider.get_structured_llm(SchemaDesignerResponse, temperature=0.1)
        
        # We use the raw LLM for Stage 2 (CSV Generation)
        self.csv_llm = LLMProvider.get_llm(temperature=0.7).bind(max_tokens=2000).with_retry(
            stop_after_attempt=3, 
            wait_exponential_jitter=True
        )
    
    def _clean_csv(self, text: str) -> str:
        # If there are markdown blocks, extract them
        match = re.search(r'```(?:csv|text)?\n(.*?)\n```', text, re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            
        lines = [line.strip() for line in text.split('\n')]
        
        # Find first and last lines containing a comma
        comma_lines = [i for i, line in enumerate(lines) if ',' in line]
        
        if not comma_lines:
            # Fallback if no commas found at all
            return text.strip()
            
        start_idx = comma_lines[0]
        end_idx = comma_lines[-1]
        
        # Return everything from start to end (inclusive)
        # Filter out empty lines in between which could break pandas
        csv_lines = [line for line in lines[start_idx:end_idx+1] if line]
        return '\n'.join(csv_lines).strip()
    
    def generate_seed_csv(self, prompt: str) -> str:
        logger.info(f"SeedGeneratorAgent generating seed CSV for prompt: {prompt}")
        
        try:
            # STAGE 1: NLP Schema Design
            schema_messages = [
                SystemMessage(content=SCHEMA_DESIGNER_SYSTEM_PROMPT),
                HumanMessage(content=f"User Request: {prompt}")
            ]
            
            logger.info("Stage 1: Designing JSON Schema...")
            schema_response: SchemaDesignerResponse = self.schema_llm.invoke(schema_messages)
            schema_json = schema_response.model_dump_json(indent=2)
            logger.info(f"Generated Schema:\n{schema_json}")
            
            # STAGE 2: CSV Generation
            csv_messages = [
                SystemMessage(content=SEED_GENERATOR_SYSTEM_PROMPT),
                HumanMessage(content=f"Original User Request: {prompt}\n\nSTRICT SCHEMA TO FOLLOW:\n{schema_json}")
            ]
            
            logger.info("Stage 2: Generating raw CSV...")
            result = self.csv_llm.invoke(csv_messages)
            content = result.content.strip()
            
            # Robust CSV extraction to drop conversational text
            cleaned_csv = self._clean_csv(content)
                
            return cleaned_csv
        except Exception as e:
            logger.error(f"Failed to generate seed CSV: {e}")
            raise
