"""Model capabilities service for querying OpenRouter model information."""

import logging
from typing import Dict, Optional, Set
import httpx

logger = logging.getLogger(__name__)


class ModelCapabilitiesService:
    """Service for querying model capabilities from OpenRouter API."""

    OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

    def __init__(self):
        """Initialize the service."""
        self._multimodal_models_cache: Set[str] = set()
        self._cache_loaded = False

    def refresh_model_capabilities(self, api_key: Optional[str] = None) -> None:
        """Fetch and cache model capabilities from OpenRouter.

        Args:
            api_key: Optional API key for authentication.
        """
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.OPENROUTER_MODELS_URL, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Parse model data and extract multimodal models
            multimodal_models = set()
            for model in data.get("data", []):
                model_id = model.get("id", "")
                architecture = model.get("architecture", {})
                
                # Check input modalities - models supporting "image" input are multimodal
                input_modalities = architecture.get("modality", "")
                
                # modality field format varies: "text->text", "text+image->text", etc.
                if "image" in input_modalities.lower():
                    multimodal_models.add(model_id)
                    continue
                
                # Also check for vision in model description or name
                name = model.get("name", "").lower()
                description = model.get("description", "").lower()
                if "vision" in name or "vision" in description:
                    multimodal_models.add(model_id)

            self._multimodal_models_cache = multimodal_models
            self._cache_loaded = True
            logger.info(f"Loaded {len(multimodal_models)} multimodal models from OpenRouter")

        except Exception as e:
            logger.warning(f"Failed to fetch model capabilities: {e}")
            # Keep existing cache on failure

    def is_model_multimodal(self, model_id: str, api_key: Optional[str] = None) -> bool:
        """Check if a model supports multimodal (image) inputs.

        Args:
            model_id: The model identifier.
            api_key: Optional API key for fetching if cache is empty.

        Returns:
            True if the model is known to support image inputs.
        """
        # Lazy load cache on first check
        if not self._cache_loaded:
            self.refresh_model_capabilities(api_key)

        # Check cache
        if model_id in self._multimodal_models_cache:
            return True

        # Fallback: check common patterns in model name for vision models
        # This helps with newly added models not yet in cache
        model_lower = model_id.lower()
        vision_patterns = [
            "vision",
            "gpt-4o",  # All GPT-4o variants support vision
            "claude-3",  # Claude 3 models support vision
            "gemini-1.5",
            "gemini-2",
            "gemini-pro",
        ]
        for pattern in vision_patterns:
            if pattern in model_lower:
                return True

        return False

    @property
    def cached_multimodal_models(self) -> Set[str]:
        """Get the set of cached multimodal model IDs."""
        return self._multimodal_models_cache.copy()


# Global singleton instance
_capabilities_service: Optional[ModelCapabilitiesService] = None


def get_model_capabilities_service() -> ModelCapabilitiesService:
    """Get the global ModelCapabilitiesService instance."""
    global _capabilities_service
    if _capabilities_service is None:
        _capabilities_service = ModelCapabilitiesService()
    return _capabilities_service
