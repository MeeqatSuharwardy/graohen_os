"""Messaging API endpoints with End-to-End Encryption

This module implements WhatsApp-like messaging with Signal protocol-style encryption:
- Messages are encrypted on the client device before sending
- Server only stores encrypted ciphertext (never sees plaintext or keys)
- Only the intended recipient can decrypt messages
- Encryption keys are never accessible to the server
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, EmailStr
import logging
import json

from app.config import settings
from app.api.v1.endpoints.auth import get_current_user
from app.core.redis_client import get_redis
from app.core.security_hardening import (
    get_security_service,
    SecurityEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Redis key prefixes
REDIS_MESSAGE_PREFIX = "message:"
REDIS_MESSAGE_METADATA_PREFIX = "message:metadata:"
REDIS_USER_MESSAGES_PREFIX = "user:messages:"
REDIS_CONVERSATION_PREFIX = "conversation:"

# Message expiration (default: 30 days)
DEFAULT_MESSAGE_EXPIRE_SECONDS = 30 * 24 * 3600  # 30 days


# Pydantic Models
class MessageSendRequest(BaseModel):
    """Message send request - expects pre-encrypted content from client"""
    recipient_email: EmailStr = Field(..., description="Recipient email address")
    encrypted_content: Dict[str, str] = Field(
        ...,
        description="Encrypted message content (encrypted on client-side). Format: {ciphertext, nonce, tag}"
    )
    encrypted_content_key: Dict[str, str] = Field(
        ...,
        description="Encrypted content key (encrypted with recipient's public key on client-side). Format: {ciphertext, nonce, tag}"
    )
    message_type: str = Field(default="text", description="Message type: text, image, video, file, etc.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (file size, filename, etc.)")


class MessageSendResponse(BaseModel):
    """Message send response"""
    message_id: str
    recipient_email: str
    sent_at: str
    expires_at: Optional[str] = None


class MessageGetResponse(BaseModel):
    """Message get response - returns encrypted content for client-side decryption"""
    message_id: str
    sender_email: str
    recipient_email: str
    encrypted_content: Dict[str, str]
    encrypted_content_key: Dict[str, str]
    message_type: str
    metadata: Optional[Dict[str, Any]] = None
    sent_at: str
    expires_at: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response"""
    conversation_id: str
    participant_email: str
    last_message_at: Optional[str] = None
    unread_count: int = 0


class ConversationMessagesResponse(BaseModel):
    """Conversation messages response"""
    conversation_id: str
    messages: List[MessageGetResponse]
    total: int


def generate_message_id() -> str:
    """Generate a unique message ID"""
    return secrets.token_urlsafe(32)


def generate_conversation_id(user1_email: str, user2_email: str) -> str:
    """Generate a deterministic conversation ID from two user emails"""
    # Sort emails to ensure same conversation ID regardless of order
    emails = sorted([user1_email.lower(), user2_email.lower()])
    conversation_data = f"{emails[0]}:{emails[1]}"
    conversation_hash = hashlib.sha256(conversation_data.encode()).hexdigest()[:16]
    return f"conv_{conversation_hash}"


async def store_message(
    message_id: str,
    sender_email: str,
    recipient_email: str,
    encrypted_content: Dict[str, str],
    encrypted_content_key: Dict[str, str],
    message_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    expires_in_seconds: Optional[int] = None,
) -> None:
    """Store encrypted message in Redis"""
    redis = await get_redis()
    
    # Store message data
    message_data = {
        "message_id": message_id,
        "sender_email": sender_email.lower(),
        "recipient_email": recipient_email.lower(),
        "encrypted_content": encrypted_content,
        "encrypted_content_key": encrypted_content_key,
        "message_type": message_type,
        "metadata": metadata or {},
        "sent_at": datetime.utcnow().isoformat(),
    }
    
    message_json = json.dumps(message_data)
    message_key = f"{REDIS_MESSAGE_PREFIX}{message_id}"
    
    # Store with expiration
    if expires_in_seconds:
        await redis.setex(message_key, expires_in_seconds, message_json)
    else:
        await redis.setex(message_key, DEFAULT_MESSAGE_EXPIRE_SECONDS, message_json)
    
    # Store message ID in recipient's inbox
    recipient_inbox_key = f"{REDIS_USER_MESSAGES_PREFIX}{recipient_email.lower()}"
    await redis.lpush(recipient_inbox_key, message_id)
    await redis.expire(recipient_inbox_key, DEFAULT_MESSAGE_EXPIRE_SECONDS)
    
    # Store message ID in sender's sent messages
    sender_sent_key = f"{REDIS_USER_MESSAGES_PREFIX}{sender_email.lower()}:sent"
    await redis.lpush(sender_sent_key, message_id)
    await redis.expire(sender_sent_key, DEFAULT_MESSAGE_EXPIRE_SECONDS)
    
    # Update conversation
    conversation_id = generate_conversation_id(sender_email, recipient_email)
    conversation_key = f"{REDIS_CONVERSATION_PREFIX}{conversation_id}"
    await redis.zadd(
        conversation_key,
        {message_id: datetime.utcnow().timestamp()}
    )
    await redis.expire(conversation_key, DEFAULT_MESSAGE_EXPIRE_SECONDS)


async def get_message(message_id: str) -> Optional[Dict[str, Any]]:
    """Get message from Redis"""
    redis = await get_redis()
    message_key = f"{REDIS_MESSAGE_PREFIX}{message_id}"
    
    message_json = await redis.get(message_key)
    if not message_json:
        return None
    
    try:
        return json.loads(message_json)
    except json.JSONDecodeError:
        return None


async def get_user_messages(user_email: str, limit: int = 50, offset: int = 0) -> List[str]:
    """Get message IDs for a user"""
    redis = await get_redis()
    inbox_key = f"{REDIS_USER_MESSAGES_PREFIX}{user_email.lower()}"
    
    # Get message IDs (most recent first)
    message_ids = await redis.lrange(inbox_key, offset, offset + limit - 1)
    return [msg_id.decode() if isinstance(msg_id, bytes) else msg_id for msg_id in message_ids]


async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[str]:
    """Get message IDs for a conversation"""
    redis = await get_redis()
    conversation_key = f"{REDIS_CONVERSATION_PREFIX}{conversation_id}"
    
    # Get message IDs sorted by timestamp (most recent first)
    message_ids = await redis.zrevrange(
        conversation_key,
        offset,
        offset + limit - 1
    )
    return [msg_id.decode() if isinstance(msg_id, bytes) else msg_id for msg_id in message_ids]


@router.post("/send", response_model=MessageSendResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageSendRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Send an encrypted message.
    
    IMPORTANT: This endpoint expects pre-encrypted content from the client.
    The client must:
    1. Encrypt the message content with a random key
    2. Encrypt the content key with the recipient's public key (or shared secret)
    3. Send only the encrypted payloads
    
    The server never sees:
    - Plaintext message content
    - Encryption keys
    - Decryption keys
    
    Only the recipient (with their private key) can decrypt the message.
    """
    try:
        security_service = get_security_service()
        client_ip = request.client.host if request.client else "unknown"
        sender_email = current_user.get("email")
        
        # Validate encrypted content structure
        required_fields = ["ciphertext", "nonce", "tag"]
        for field in required_fields:
            if field not in message_data.encrypted_content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field in encrypted_content: {field}"
                )
            if field not in message_data.encrypted_content_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field in encrypted_content_key: {field}"
                )
        
        # Generate message ID
        message_id = generate_message_id()
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(seconds=DEFAULT_MESSAGE_EXPIRE_SECONDS)
        
        # Store encrypted message (server never decrypts)
        await store_message(
            message_id=message_id,
            sender_email=sender_email,
            recipient_email=message_data.recipient_email,
            encrypted_content=message_data.encrypted_content,
            encrypted_content_key=message_data.encrypted_content_key,
            message_type=message_data.message_type,
            metadata=message_data.metadata,
            expires_in_seconds=DEFAULT_MESSAGE_EXPIRE_SECONDS,
        )
        
        # Log security event
        await security_service.log_security_event(
            SecurityEvent.EMAIL_SENT,  # Reuse EMAIL_SENT for messaging
            identifier=sender_email,
            user_id=current_user.get("id"),
            ip_address=client_ip,
            action="message_send",
            metadata={
                "message_id": message_id[:8] + "...",
                "recipient": message_data.recipient_email,
                "message_type": message_data.message_type,
            },
            success=True,
        )
        
        logger.info(
            f"Message sent: id={message_id[:8]}..., "
            f"from={sender_email}, to={message_data.recipient_email}, "
            f"type={message_data.message_type}"
        )
        
        return MessageSendResponse(
            message_id=message_id,
            recipient_email=message_data.recipient_email,
            sent_at=datetime.utcnow().isoformat(),
            expires_at=expires_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Message send failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/messages", response_model=List[MessageGetResponse])
async def get_messages(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get encrypted messages for the current user.
    
    Returns encrypted content that must be decrypted on the client-side.
    The server never decrypts messages - only stores and retrieves ciphertext.
    """
    try:
        user_email = current_user.get("email")
        
        # Get message IDs for user
        message_ids = await get_user_messages(user_email, limit=limit, offset=offset)
        
        # Fetch messages
        messages = []
        for message_id in message_ids:
            message = await get_message(message_id)
            if message:
                # Only return messages where user is recipient
                if message.get("recipient_email", "").lower() == user_email.lower():
                    messages.append(MessageGetResponse(
                        message_id=message["message_id"],
                        sender_email=message["sender_email"],
                        recipient_email=message["recipient_email"],
                        encrypted_content=message["encrypted_content"],
                        encrypted_content_key=message["encrypted_content_key"],
                        message_type=message["message_type"],
                        metadata=message.get("metadata"),
                        sent_at=message["sent_at"],
                        expires_at=None,  # Could calculate from TTL
                    ))
        
        return messages
        
    except Exception as e:
        logger.error(f"Failed to get messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.get("/conversation/{participant_email}", response_model=ConversationMessagesResponse)
async def get_conversation(
    participant_email: str,
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get messages in a conversation with a specific participant.
    
    Returns encrypted messages that must be decrypted on the client-side.
    """
    try:
        user_email = current_user.get("email")
        
        # Generate conversation ID
        conversation_id = generate_conversation_id(user_email, participant_email)
        
        # Get message IDs for conversation
        message_ids = await get_conversation_messages(conversation_id, limit=limit, offset=offset)
        
        # Fetch messages
        messages = []
        for message_id in message_ids:
            message = await get_message(message_id)
            if message:
                # Verify user is part of conversation
                sender = message.get("sender_email", "").lower()
                recipient = message.get("recipient_email", "").lower()
                user_email_lower = user_email.lower()
                
                if sender == user_email_lower or recipient == user_email_lower:
                    messages.append(MessageGetResponse(
                        message_id=message["message_id"],
                        sender_email=message["sender_email"],
                        recipient_email=message["recipient_email"],
                        encrypted_content=message["encrypted_content"],
                        encrypted_content_key=message["encrypted_content_key"],
                        message_type=message["message_type"],
                        metadata=message.get("metadata"),
                        sent_at=message["sent_at"],
                        expires_at=None,
                    ))
        
        return ConversationMessagesResponse(
            conversation_id=conversation_id,
            messages=messages,
            total=len(messages),
        )
        
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get list of conversations for the current user.
    """
    try:
        user_email = current_user.get("email")
        
        # Get all message IDs for user
        message_ids = await get_user_messages(user_email, limit=1000)
        
        # Group by conversation participants
        conversations_map: Dict[str, Dict[str, Any]] = {}
        
        for message_id in message_ids:
            message = await get_message(message_id)
            if message:
                sender = message.get("sender_email", "").lower()
                recipient = message.get("recipient_email", "").lower()
                
                # Determine participant
                if sender == user_email.lower():
                    participant = recipient
                else:
                    participant = sender
                
                conversation_id = generate_conversation_id(user_email, participant)
                
                if conversation_id not in conversations_map:
                    conversations_map[conversation_id] = {
                        "conversation_id": conversation_id,
                        "participant_email": participant,
                        "last_message_at": message.get("sent_at"),
                        "unread_count": 0,  # Could implement unread tracking
                    }
                else:
                    # Update last message time if newer
                    current_last = conversations_map[conversation_id]["last_message_at"]
                    message_time = message.get("sent_at")
                    if message_time and (not current_last or message_time > current_last):
                        conversations_map[conversation_id]["last_message_at"] = message_time
        
        return [
            ConversationResponse(**conv_data)
            for conv_data in conversations_map.values()
        ]
        
    except Exception as e:
        logger.error(f"Failed to get conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.delete("/message/{message_id}")
async def delete_message(
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Delete a message (only if user is sender or recipient).
    """
    try:
        user_email = current_user.get("email")
        
        # Get message
        message = await get_message(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Verify user is sender or recipient
        sender = message.get("sender_email", "").lower()
        recipient = message.get("recipient_email", "").lower()
        user_email_lower = user_email.lower()
        
        if sender != user_email_lower and recipient != user_email_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own messages"
            )
        
        # Delete message
        redis = await get_redis()
        message_key = f"{REDIS_MESSAGE_PREFIX}{message_id}"
        await redis.delete(message_key)
        
        # Remove from user inboxes
        sender_inbox_key = f"{REDIS_USER_MESSAGES_PREFIX}{sender}"
        recipient_inbox_key = f"{REDIS_USER_MESSAGES_PREFIX}{recipient}"
        await redis.lrem(sender_inbox_key, 0, message_id)
        await redis.lrem(recipient_inbox_key, 0, message_id)
        
        logger.info(f"Message deleted: id={message_id[:8]}...")
        
        return {"message_id": message_id, "deleted": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete message"
        )
