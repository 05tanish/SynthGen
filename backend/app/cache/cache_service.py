"""
Redis Caching Service for SynthGen

Implements intelligent caching for:
1. Dataset profiles and relationships (immutable after creation)
2. Evaluation results (keyed by dataset + model + parameters)
3. LLM responses for deterministic queries (optional)

TTL (Time-To-Live) Strategy:
- Dataset profiles: 7 days (rarely change)
- Evaluation results: 24 hours (recomputed if stale)
- LLM responses: 1 hour (disabled by default for safety)

Cache Invalidation:
- Dataset deleted → invalidate all related cache
- Job failed/cancelled → keep cache (for retry)
- Parameters changed → new cache key
"""

import json
import hashlib
from typing import Optional, Dict, Any
from app.cache.redis import get_redis_client
from app.core.logging import logger

# TTL values in seconds
TTL_DATASET_PROFILE = 60 * 60 * 24 * 7  # 7 days
TTL_EVALUATION = 60 * 60 * 24  # 24 hours
TTL_LLM_RESPONSE = 60 * 60  # 1 hour (disabled by default)

# Feature flags
ENABLE_LLM_CACHING = False  # Disabled for safety - prompts may have context variations


class CacheService:
    """Centralized caching service with Redis backend"""
    
    @staticmethod
    def _get_redis():
        """Get Redis client with error handling"""
        try:
            return get_redis_client()
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Cache operations will be skipped.")
            return None
    
    @staticmethod
    def _make_key(*parts: str) -> str:
        """Create a cache key from parts"""
        return ":".join(str(p) for p in parts)
    
    @staticmethod
    def _hash_dict(data: Dict[str, Any]) -> str:
        """Create a stable hash of a dictionary"""
        # Sort keys for stable hash
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(json_str.encode()).hexdigest()[:16]
    
    # ========================================================================
    # Dataset Profile Caching
    # ========================================================================
    
    @staticmethod
    def get_dataset_profile(dataset_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached dataset profile.
        
        Returns:
            Profile dict or None if not cached
        """
        redis = CacheService._get_redis()
        if not redis:
            return None
        
        try:
            key = CacheService._make_key("profile", dataset_id)
            data = redis.get(key)
            if data:
                logger.debug(f"Cache HIT: dataset profile {dataset_id}")
                return json.loads(data)
            logger.debug(f"Cache MISS: dataset profile {dataset_id}")
            return None
        except Exception as e:
            logger.error(f"Error reading profile cache: {e}")
            return None
    
    @staticmethod
    def set_dataset_profile(dataset_id: int, profile: Dict[str, Any]):
        """
        Cache dataset profile (immutable after creation).
        
        Args:
            dataset_id: Dataset ID
            profile: Profile dictionary from dataset_profiler
        """
        redis = CacheService._get_redis()
        if not redis:
            return
        
        try:
            key = CacheService._make_key("profile", dataset_id)
            redis.setex(key, TTL_DATASET_PROFILE, json.dumps(profile))
            logger.debug(f"Cached dataset profile {dataset_id} (TTL: {TTL_DATASET_PROFILE}s)")
        except Exception as e:
            logger.error(f"Error caching profile: {e}")
    
    @staticmethod
    def get_dataset_relationships(dataset_id: int) -> Optional[Dict[str, Any]]:
        """Get cached dataset relationships"""
        redis = CacheService._get_redis()
        if not redis:
            return None
        
        try:
            key = CacheService._make_key("relationships", dataset_id)
            data = redis.get(key)
            if data:
                logger.debug(f"Cache HIT: dataset relationships {dataset_id}")
                return json.loads(data)
            logger.debug(f"Cache MISS: dataset relationships {dataset_id}")
            return None
        except Exception as e:
            logger.error(f"Error reading relationships cache: {e}")
            return None
    
    @staticmethod
    def set_dataset_relationships(dataset_id: int, relationships: Dict[str, Any]):
        """Cache dataset relationships"""
        redis = CacheService._get_redis()
        if not redis:
            return
        
        try:
            key = CacheService._make_key("relationships", dataset_id)
            redis.setex(key, TTL_DATASET_PROFILE, json.dumps(relationships))
            logger.debug(f"Cached dataset relationships {dataset_id}")
        except Exception as e:
            logger.error(f"Error caching relationships: {e}")
    
    # ========================================================================
    # Evaluation Result Caching
    # ========================================================================
    
    @staticmethod
    def get_evaluation_result(
        dataset_id: int,
        model: str,
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached evaluation result.
        
        Cache key includes dataset + model + parameters hash.
        Same dataset with same model/params will hit cache.
        
        Args:
            dataset_id: Dataset ID
            model: Model name (CTGAN, TVAE, GaussianCopula)
            parameters: Model parameters dict
        
        Returns:
            Evaluation report dict or None
        """
        redis = CacheService._get_redis()
        if not redis:
            return None
        
        try:
            param_hash = CacheService._hash_dict(parameters)
            key = CacheService._make_key("eval", dataset_id, model, param_hash)
            data = redis.get(key)
            if data:
                logger.info(f"Cache HIT: evaluation for dataset {dataset_id}, model {model}")
                return json.loads(data)
            logger.debug(f"Cache MISS: evaluation for dataset {dataset_id}, model {model}")
            return None
        except Exception as e:
            logger.error(f"Error reading evaluation cache: {e}")
            return None
    
    @staticmethod
    def set_evaluation_result(
        dataset_id: int,
        model: str,
        parameters: Dict[str, Any],
        evaluation_report: Dict[str, Any]
    ):
        """
        Cache evaluation result.
        
        Useful for retries - if same dataset with same model/params,
        we can skip regeneration and return cached evaluation.
        
        Args:
            dataset_id: Dataset ID
            model: Model name
            parameters: Model parameters dict
            evaluation_report: Full evaluation report
        """
        redis = CacheService._get_redis()
        if not redis:
            return
        
        try:
            param_hash = CacheService._hash_dict(parameters)
            key = CacheService._make_key("eval", dataset_id, model, param_hash)
            redis.setex(key, TTL_EVALUATION, json.dumps(evaluation_report))
            logger.info(f"Cached evaluation for dataset {dataset_id}, model {model} (TTL: {TTL_EVALUATION}s)")
        except Exception as e:
            logger.error(f"Error caching evaluation: {e}")
    
    # ========================================================================
    # LLM Response Caching (Optional - Disabled by Default)
    # ========================================================================
    
    @staticmethod
    def get_llm_response(
        agent_name: str,
        prompt_hash: str
    ) -> Optional[str]:
        """
        Get cached LLM response (DISABLED BY DEFAULT).
        
        Only use for truly deterministic queries where:
        1. Temperature = 0.0
        2. Prompt is exactly the same
        3. No context window variations
        
        Args:
            agent_name: Agent name (e.g., "GenerationPlannerAgent")
            prompt_hash: MD5 hash of the full prompt
        
        Returns:
            Cached response or None
        """
        if not ENABLE_LLM_CACHING:
            return None
        
        redis = CacheService._get_redis()
        if not redis:
            return None
        
        try:
            key = CacheService._make_key("llm", agent_name, prompt_hash)
            data = redis.get(key)
            if data:
                logger.info(f"Cache HIT: LLM response for {agent_name}")
                return data
            return None
        except Exception as e:
            logger.error(f"Error reading LLM cache: {e}")
            return None
    
    @staticmethod
    def set_llm_response(
        agent_name: str,
        prompt_hash: str,
        response: str
    ):
        """
        Cache LLM response (DISABLED BY DEFAULT).
        
        Args:
            agent_name: Agent name
            prompt_hash: MD5 hash of the full prompt
            response: LLM response text
        """
        if not ENABLE_LLM_CACHING:
            return
        
        redis = CacheService._get_redis()
        if not redis:
            return
        
        try:
            key = CacheService._make_key("llm", agent_name, prompt_hash)
            redis.setex(key, TTL_LLM_RESPONSE, response)
            logger.debug(f"Cached LLM response for {agent_name}")
        except Exception as e:
            logger.error(f"Error caching LLM response: {e}")
    
    # ========================================================================
    # Cache Invalidation
    # ========================================================================
    
    @staticmethod
    def invalidate_dataset(dataset_id: int):
        """
        Invalidate all cache entries for a dataset.
        
        Call this when dataset is deleted or modified.
        
        Args:
            dataset_id: Dataset ID
        """
        redis = CacheService._get_redis()
        if not redis:
            return
        
        try:
            # Delete profile and relationships
            keys_to_delete = [
                CacheService._make_key("profile", dataset_id),
                CacheService._make_key("relationships", dataset_id)
            ]
            
            # Delete all evaluation results for this dataset
            # Pattern: eval:{dataset_id}:*
            pattern = CacheService._make_key("eval", dataset_id, "*")
            eval_keys = redis.keys(pattern)
            if eval_keys:
                keys_to_delete.extend(eval_keys)
            
            if keys_to_delete:
                redis.delete(*keys_to_delete)
                logger.info(f"Invalidated {len(keys_to_delete)} cache entries for dataset {dataset_id}")
        except Exception as e:
            logger.error(f"Error invalidating dataset cache: {e}")
    
    @staticmethod
    def clear_all_cache():
        """
        Clear ALL cache (use with caution).
        
        Only use for:
        - Testing
        - Major system updates
        - Debugging cache issues
        """
        redis = CacheService._get_redis()
        if not redis:
            return
        
        try:
            redis.flushdb()
            logger.warning("Cleared ALL Redis cache")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    # ========================================================================
    # Cache Statistics
    # ========================================================================
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with keys: total_keys, memory_used, hit_rate, etc.
        """
        redis = CacheService._get_redis()
        if not redis:
            return {"available": False}
        
        try:
            info = redis.info("stats")
            return {
                "available": True,
                "total_keys": redis.dbsize(),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                ) * 100
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"available": False, "error": str(e)}
