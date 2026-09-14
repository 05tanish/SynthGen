import re
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Optional
from sdv.metadata import SingleTableMetadata
from sdv.single_table import GaussianCopulaSynthesizer, CTGANSynthesizer, TVAESynthesizer
from app.core.logging import logger

# ──────────────────────────────────────────────────────────────────────────────
# Whitelisted parameters per synthesizer (based on actual SDV constructor sigs)
# Any key not listed here will be silently dropped before construction.
# This prevents LLM hallucinations like 'learning_rate' from crashing the job.
# ──────────────────────────────────────────────────────────────────────────────
_CTGAN_VALID_PARAMS = {
    "enforce_min_max_values", "enforce_rounding", "locales",
    "embedding_dim", "generator_dim", "discriminator_dim",
    "generator_lr", "generator_decay",
    "discriminator_lr", "discriminator_decay",
    "batch_size", "discriminator_steps", "log_frequency",
    "verbose", "epochs", "pac", "enable_gpu", "cuda",
}

_GAUSSIAN_VALID_PARAMS = {
    "enforce_min_max_values", "enforce_rounding", "locales",
    "numerical_distributions", "default_distribution",
}

_TVAE_VALID_PARAMS = {
    "enforce_min_max_values", "enforce_rounding",
    "embedding_dim", "compress_dims", "decompress_dims",
    "l2scale", "batch_size", "verbose", "epochs",
    "loss_factor", "enable_gpu", "cuda",
}


def _sanitize_params(params: Dict[str, Any], whitelist: set, model_name: str) -> Dict[str, Any]:
    """Drop any keys not in the whitelist and warn about each one removed."""
    dropped = [k for k in params if k not in whitelist]
    if dropped:
        logger.warning(
            f"{model_name}: Dropping unsupported parameters suggested by LLM: {dropped}. "
            f"Valid params are: {sorted(whitelist)}"
        )
    return {k: v for k, v in params.items() if k in whitelist}


def _safe_ctgan_params(n_rows: int, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute safe CTGAN parameters to avoid the discriminator pac assertion error.

    CTGAN's discriminator asserts: batch_size % pac == 0, and batch_size % 2 == 0.
    The effective batch the discriminator sees is min(batch_size, n_rows),
    so we must ensure that value is divisible by pac, and is even.
    """
    safe = dict(params)
    pac = safe.get("pac", 10)

    # Effective batch seen by the discriminator cannot exceed n_rows
    effective_batch = min(safe.get("batch_size", 500), n_rows)
    
    # Must be an even number
    if effective_batch % 2 != 0:
        effective_batch -= 1
        
    if effective_batch <= 0:
        effective_batch = 2  # Fallback just in case n_rows=1

    if effective_batch % pac != 0:
        # Find the largest divisor of effective_batch that is <= pac
        best_pac = 1
        for p in range(1, min(pac, effective_batch) + 1):
            if effective_batch % p == 0:
                best_pac = p
        logger.warning(
            f"CTGAN: effective_batch={effective_batch} is not divisible by pac={pac}. "
            f"Auto-adjusting pac → {best_pac}."
        )
        safe["pac"] = best_pac
    else:
        safe["pac"] = pac

    safe["batch_size"] = effective_batch
    return safe


def parse_row_count_from_prompt(requirement: Optional[str]) -> Optional[int]:
    """
    Extract a desired row count from the user's natural-language prompt.

    Recognises patterns like:
      - "generate 500 rows"
      - "produce 1,000 records"
      - "I need 2000 samples"
      - "200 rows please"
      - "give me 300"
    Returns None if no number is found.
    """
    if not requirement:
        return None

    # Normalise thousands separators
    text = requirement.replace(",", "").lower()

    patterns = [
        r"(\d+)\s*(?:rows?|records?|samples?|entries|data\s*points?)",
        r"(?:generate|produce|create|give\s+me|need|want)\s+(\d+)",
        r"(\d+)\s+(?:row|record|sample)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            count = int(match.group(1))
            # Enforce system limit of 30,000 rows
            if 1 <= count <= 30_000:
                logger.info(f"Parsed row_count={count} from user prompt.")
                return count
            elif count > 30_000:
                logger.warning(f"User requested {count} rows, but system limit is 30,000. Capping to 30,000.")
                return 30_000
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Generator classes
# ──────────────────────────────────────────────────────────────────────────────

class BaseSyntheticGenerator(ABC):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        self.metadata = SingleTableMetadata()
        self.parameters = parameters or {}
        self.model = None

    @abstractmethod
    def fit(self, data: pd.DataFrame):
        pass

    def generate(self, num_rows: int) -> pd.DataFrame:
        if not self.model:
            raise ValueError("Model is not fitted yet.")
        return self.model.sample(num_rows=num_rows)

    def save_model(self, path: str):
        if not self.model:
            raise ValueError("Model is not fitted yet.")
        self.model.save(filepath=path)

    def load_model(self, path: str):
        pass


class GaussianCopulaGenerator(BaseSyntheticGenerator):
    def fit(self, data: pd.DataFrame):
        self.metadata.detect_from_dataframe(data)
        safe = _sanitize_params(self.parameters, _GAUSSIAN_VALID_PARAMS, "GaussianCopula")
        self.model = GaussianCopulaSynthesizer(self.metadata, **safe)
        self.model.fit(data)

    def load_model(self, path: str):
        self.model = GaussianCopulaSynthesizer.load(filepath=path)


class CTGANGenerator(BaseSyntheticGenerator):
    def fit(self, data: pd.DataFrame):
        self.metadata.detect_from_dataframe(data)
        # 1. Drop LLM-hallucinated keys
        safe = _sanitize_params(self.parameters, _CTGAN_VALID_PARAMS, "CTGAN")
        # 2. Fix pac/batch_size to avoid discriminator assertion
        safe = _safe_ctgan_params(n_rows=len(data), params=safe)
        logger.info(f"CTGANGenerator fitting with params: {safe}")
        self.model = CTGANSynthesizer(self.metadata, **safe)
        self.model.fit(data)

    def load_model(self, path: str):
        self.model = CTGANSynthesizer.load(filepath=path)


class TVAEGenerator(BaseSyntheticGenerator):
    def fit(self, data: pd.DataFrame):
        self.metadata.detect_from_dataframe(data)
        # Drop LLM-hallucinated keys
        safe = _sanitize_params(self.parameters, _TVAE_VALID_PARAMS, "TVAE")
        # Cap batch_size to n_rows and make it even
        batch_size = min(safe.get("batch_size", 500), len(data))
        if batch_size % 2 != 0:
            batch_size -= 1
        safe["batch_size"] = max(2, batch_size)
        
        self.model = TVAESynthesizer(self.metadata, **safe)
        self.model.fit(data)

    def load_model(self, path: str):
        self.model = TVAESynthesizer.load(filepath=path)
