"""
error_sanitiser.py — Converts raw internal exceptions into safe, user-friendly
HTTP error messages, hiding all internal implementation details.
"""

from fastapi import HTTPException
from app.core.logging import logger


# Mapping: known internal exception substrings → friendly user message
_SAFE_MESSAGES = [
    # LLM / generation errors
    ("invalid json", "The AI model returned an unexpected response. Please try again or rephrase your prompt."),
    ("output_parsing_failure", "The AI model returned an unexpected response. Please try again or rephrase your prompt."),
    ("pydantic", "The AI model returned an unexpected response. Please try again or rephrase your prompt."),
    ("langchain", "The AI generation pipeline encountered an error. Please try again."),
    ("could not extract a valid schema", "Unable to understand the dataset request. Please rephrase your prompt in plain language (e.g. 'Generate a customer dataset with name, email, country, and signup date')."),
    ("could not generate valid csv", "Unable to generate seed data from your prompt. Try being more specific or use a file upload instead."),
    # LLM API errors
    ("rate limit", "The AI service is currently busy. Please wait a moment and try again."),
    ("api key", "The AI service configuration is invalid. Please contact support."),
    ("timeout", "The request took too long. Please try again with a simpler prompt."),
    ("connection", "Could not reach the AI service. Please check your network and try again."),
    # File errors
    ("source file not found", "The uploaded file could not be found. Please upload it again."),
    ("no such file", "The file could not be processed. Please try uploading again."),
    # DB errors
    ("unique constraint", "A record with this information already exists."),
    ("foreign key", "Invalid reference. Please refresh the page and try again."),
]

_GENERIC_USER_MESSAGE = "An unexpected error occurred. Please try again."


def safe_error_message(exc: Exception) -> str:
    """
    Returns a safe, user-facing error message from an internal exception.
    Never exposes stack traces, internal paths, model names, or library details.
    """
    raw = str(exc).lower()
    for keyword, friendly in _SAFE_MESSAGES:
        if keyword in raw:
            return friendly
    return _GENERIC_USER_MESSAGE


def raise_safe_http_error(exc: Exception, status_code: int = 500, context: str = "") -> None:
    """
    Logs the full exception internally and raises an HTTPException with a
    sanitised, user-friendly detail message.
    """
    log_msg = f"{context}: {exc}" if context else str(exc)
    logger.error(log_msg, exc_info=True)
    raise HTTPException(status_code=status_code, detail=safe_error_message(exc))
