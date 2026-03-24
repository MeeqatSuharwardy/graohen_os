"""User SSH key model - encrypted storage for browser-based SSH login"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text

from app.models.base import BaseModel


class UserSSHKey(BaseModel):
    """
    Encrypted SSH public key for browser-based login.
    Public key is stored encrypted at rest; decryption happens only in-memory during verification.
    """

    __tablename__ = "user_ssh_keys"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Fingerprint (SHA256 of public key) - for lookup, not secret
    key_fingerprint = Column(String(64), unique=True, nullable=False, index=True)

    # Encrypted public key payload: JSON with ciphertext, nonce, tag (AES-256-GCM)
    encrypted_public_key = Column(Text, nullable=False)

    # Key type for routing verification (ed25519, rsa-sha2-256, etc.)
    key_type = Column(String(32), nullable=False)
