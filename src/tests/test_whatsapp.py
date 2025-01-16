# src/tests/test_whatsapp.py
import pytest
from services.whatsapp import WhatsAppAPI

@pytest.mark.asyncio
async def test_send_message():
    """Test WhatsApp message sending"""
    api = WhatsAppAPI("test_key")
    with pytest.raises(Exception):  # Should fail with test key
        await api.send_message("123", "Test message")

@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry logic for failed messages"""
    api = WhatsAppAPI("test_key")
    # Add test for retry logic