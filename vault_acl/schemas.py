from pydantic import BaseModel, ConfigDict
from typing import Optional

class VaultAclConfig(BaseModel):
    """Configuration schema for Vault ACL pipeline steps."""
    model_config = ConfigDict(extra="allow")
    
    policy_path: Optional[str] = None
