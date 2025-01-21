# src/services/conversation.py
from enum import Enum
from datetime import datetime
from typing import Optional, Dict
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    BOT = "bot"
    HUMAN = "human"
    WAITING_FOR_HUMAN = "waiting_for_human"

class ConversationHandler:
    def __init__(self, mongodb_service):
        self.mongodb = mongodb_service
        self._setup_collection()

    def _setup_collection(self):
        """Setup MongoDB collection for conversation tracking"""
        try:
            client = self.mongodb._get_client()
            db = client['yom-production']
            self.conversations = db['support_conversations']
            
            # Create indexes if they don't exist
            self.conversations.create_index("wa_id", unique=True)
            self.conversations.create_index("last_updated")
        except Exception as e:
            logger.error(f"Error setting up conversation collection: {e}")
            raise

    async def get_conversation_state(self, wa_id: str) -> ConversationState:
        """Get current state of conversation"""
        try:
            conversation = self.conversations.find_one({"wa_id": wa_id})
            if not conversation:
                # Initialize new conversation
                conversation = {
                    "wa_id": wa_id,
                    "state": ConversationState.BOT.value,
                    "assigned_agent": None,
                    "last_updated": datetime.utcnow(),
                    "messages": []
                }
                self.conversations.insert_one(conversation)
                return ConversationState.BOT
            
            return ConversationState(conversation["state"])
        except Exception as e:
            logger.error(f"Error getting conversation state: {e}")
            return ConversationState.BOT

    async def initiate_human_handover(self, wa_id: str, reason: str) -> bool:
        """Request human agent takeover"""
        try:
            result = self.conversations.update_one(
                {"wa_id": wa_id},
                {
                    "$set": {
                        "state": ConversationState.WAITING_FOR_HUMAN.value,
                        "handover_reason": reason,
                        "handover_requested_at": datetime.utcnow(),
                        "last_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error initiating human handover: {e}")
            return False

    async def assign_human_agent(self, wa_id: str, agent_id: str) -> bool:
        """Assign human agent to conversation"""
        try:
            result = self.conversations.update_one(
                {"wa_id": wa_id},
                {
                    "$set": {
                        "state": ConversationState.HUMAN.value,
                        "assigned_agent": agent_id,
                        "agent_assigned_at": datetime.utcnow(),
                        "last_updated": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error assigning human agent: {e}")
            return False

    async def return_to_bot(self, wa_id: str) -> bool:
        """Return conversation handling to bot"""
        try:
            result = self.conversations.update_one(
                {"wa_id": wa_id},
                {
                    "$set": {
                        "state": ConversationState.BOT.value,
                        "assigned_agent": None,
                        "last_updated": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error returning to bot: {e}")
            return False

    async def add_message(self, wa_id: str, message: str, is_from_user: bool):
        """Add message to conversation history"""
        try:
            self.conversations.update_one(
                {"wa_id": wa_id},
                {
                    "$push": {
                        "messages": {
                            "content": message,
                            "timestamp": datetime.utcnow(),
                            "is_from_user": is_from_user
                        }
                    },
                    "$set": {"last_updated": datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.error(f"Error adding message to history: {e}")
