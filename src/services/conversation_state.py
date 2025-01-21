# src/services/conversation_state.py
from enum import Enum
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    BOT = "bot"
    HUMAN = "human"
    PENDING_HANDOVER = "pending_handover"

# Confidence threshold for bot responses
MIN_CONFIDENCE_THRESHOLD = 0.7

class ConversationManager:
    def __init__(self, mongodb_service):
        self.mongodb = mongodb_service
    
    async def get_conversation_state(self, wa_id: str) -> Dict:
        """Get current state of a conversation"""
        return await self.mongodb.get_conversation_state(wa_id)

    async def request_human_handover(self, wa_id: str, reason: str) -> bool:
        """Request handover to human agent"""
        try:
            update_data = {
                "state": ConversationState.PENDING_HANDOVER.value,
                "handover_reason": reason,
                "last_update": datetime.utcnow()
            }
            return await self.mongodb.update_conversation_state(wa_id, update_data)
        except Exception as e:
            logger.error(f"Error requesting handover: {e}")
            return False

    async def assign_human_agent(self, wa_id: str, agent_id: str) -> bool:
        """Assign a human agent to the conversation"""
        try:
            update_data = {
                "state": ConversationState.HUMAN.value,
                "assigned_agent": agent_id,
                "last_update": datetime.utcnow()
            }
            return await self.mongodb.update_conversation_state(wa_id, update_data)
        except Exception as e:
            logger.error(f"Error assigning agent: {e}")
            return False

    async def return_to_bot(self, wa_id: str) -> bool:
        """Return conversation handling to bot"""
        try:
            update_data = {
                "state": ConversationState.BOT.value,
                "assigned_agent": None,
                "handover_reason": None,
                "last_update": datetime.utcnow()
            }
            return await self.mongodb.update_conversation_state(wa_id, update_data)
        except Exception as e:
            logger.error(f"Error returning to bot: {e}")
            return False
