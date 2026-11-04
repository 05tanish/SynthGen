"""
error_sanitiser.py — Converts raw internal exceptions into safe, user-friendly
HTTP error messages, hiding all internal implementation details.
"""

from fastapi import HTTPException
from app.core.logging import logger
import traceback


# Mapping: known internal exception substrings → friendly user message
_SAFE_MESSAGES = [
    # LLM / generation errors
    ("llm_api_key", "The AI service is temporarily unavailable. Please try again later."),
    ("environment variable is not set", "The AI service is temporarily unavailable. Please contact support."),
    ("api key", "The AI service is temporarily unavailable. Please try again later."),
    ("invalid json", "The AI returned an unexpected response. Please try again or rephrase your prompt."),
    ("output_parsing_failure", "Unable to process the AI response. Please try again or rephrase your prompt."),
    ("pydantic", "Data validation failed. Please check your input and try again."),
    ("langchain", "The AI generation encountered an error. Please try again."),
    ("could not extract a valid schema", "Unable to understand your request. Please describe your dataset in plain language (e.g. 'customer data with names, emails, and signup dates')."),
    ("could not generate valid csv", "Unable to create the dataset from your description. Please try again with a clearer description or upload a sample file instead."),
    ("seedgeneratoragent", "Unable to generate initial data. Please try again or use file upload instead."),
    # LLM API errors
    ("rate limit", "The AI service is currently busy. Please wait a moment and try again."),
    ("429", "Too many requests. Please wait a moment and try again."),
    ("timeout", "The request took too long. Please try again."),
    ("connection", "Unable to reach the AI service. Please check your internet connection and try again."),
    ("groq", "The AI service encountered an error. Please try again in a moment."),
    # File errors
    ("source file not found", "The file could not be found. Please try uploading again."),
    ("no such file", "The file could not be found. Please try uploading again."),
    ("permission denied", "Unable to access the file. Please try again."),
    ("file not found", "The file could not be found. Please try again."),
    # DB errors
    ("unique constraint", "This record already exists."),
    ("foreign key", "Invalid reference. Please refresh and try again."),
    ("no such table", "Database error. Please contact support."),
    ("operational error", "Database temporarily unavailable. Please try again in a moment."),
    ("integrity error", "Invalid data. Please check your input and try again."),
    # Auth errors
    ("could not validate credentials", "Session expired. Please log in again."),
    ("unauthorized", "Please log in to continue."),
    ("token", "Session expired. Please log in again."),
    ("jwt", "Session expired. Please log in again."),
    # Redis/Cache errors
    ("redis", "Cache service unavailable. Your request may take longer than usual."),
    ("upstash", "Cache service unavailable. Your request may take longer than usual."),
    # Cloudinary errors
    ("cloudinary", "File storage service temporarily unavailable. Please try again later."),
    ("upload failed", "File upload failed. Please try again later."),
    # Technical exposure prevention
    ("traceback", "An error occurred. Please try again."),
    ("exception", "An error occurred. Please try again."),
    ("syntaxerror", "An error occurred. Please try again."),
    ("importerror", "Service temporarily unavailable. Please try again later."),
    ("modulenotfound", "Service temporarily unavailable. Please contact support."),
    ("attributeerror", "An error occurred. Please try again."),
    ("keyerror", "Data format error. Please try again."),
    ("valueerror", "Invalid data. Please check your input."),
    ("typeerror", "Data format error. Please try again."),
]

_GENERIC_USER_MESSAGE = "An unexpected error occurred. Please try again. If the problem persists, contact support."


def safe_error_message(exc: Exception) -> str:
    """
    Returns a safe, user-facing error message from an internal exception.
    Never exposes stack traces, internal paths, model names, or library details.
    """
    raw = str(exc).lower()
    
    # Check for specific exception types first
    exc_type = type(exc).__name__.lower()
    if "notfound" in exc_type or "404" in raw:
        return "The requested resource was not found."
    if "forbidden" in exc_type or "403" in raw:
        return "You don't have permission to access this resource."
    if "unauthorized" in exc_type or "401" in raw:
        return "Authentication required. Please log in."
    
    # Check message patterns
    for keyword, friendly in _SAFE_MESSAGES:
        if keyword in raw:
            return friendly
    
    # If no match, return generic message
    return _GENERIC_USER_MESSAGE


def raise_safe_http_error(exc: Exception, status_code: int = 500, context: str = "") -> None:
    """
    Logs the full exception internally and raises an HTTPException with a
    sanitised, user-friendly detail message.
    
    Args:
        exc: The original exception
        status_code: HTTP status code to return (default 500)
        context: Additional context about where the error occurred
    """
    # Log full error details internally
    log_msg = f"[{context}] {type(exc).__name__}: {exc}" if context else f"{type(exc).__name__}: {exc}"
    logger.error(log_msg, exc_info=True)
    
    # Also log the full traceback for debugging
    logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    # Raise sanitized error to user
    raise HTTPException(status_code=status_code, detail=safe_error_message(exc))

