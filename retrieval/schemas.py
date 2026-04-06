from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class RetrievalConfig(BaseModel):
    """Configuration schema for the Retrieval module."""
    model_config = ConfigDict(extra="allow")  # Allow unstructured stores/embeddings for now

    log_level: str = "INFO"
    top_k: int = Field(10, ge=1, description="Max results per source per query variant")
    rephrase_prompt: dict[str, Any] = Field(default_factory=dict)
    
    # Optional parameters for search step
    query: Optional[str] = Field(None, description="Поисковый запрос (если передается через конфиг)")
    level: Optional[int] = Field(None, description="RAPTOR level filter")
    rephrase: bool = Field(True, description="Использовать ли LLM для перефразирования")
