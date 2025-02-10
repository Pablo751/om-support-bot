# src/tests/conftest.py
import pytest
from typing import Generator
from fastapi.testclient import TestClient
import pandas as pd
from unittest.mock import MagicMock

from main import app
from services.support import SupportSystem
from services.whatsapp import WhatsAppAPI
from services.mongodb import MongoDBService

@pytest.fixture
def test_app() -> Generator:
    yield app

@pytest.fixture
def client(test_app) -> Generator:
    with TestClient(test_app) as client:
        yield client

@pytest.fixture
def mock_support_system() -> Generator:
    system = MagicMock(spec=SupportSystem)
    yield system

@pytest.fixture
def mock_whatsapp_api() -> Generator:
    api = MagicMock(spec=WhatsAppAPI)
    yield api

@pytest.fixture
def mock_mongodb_service() -> Generator:
    service = MagicMock(spec=MongoDBService)
    yield service

# src/tests/test_support.py
import pytest
from services.support import SupportSystem

def test_load_knowledge_base():
    """Test knowledge base loading"""
    system = SupportSystem("tests/data/test_knowledge_base.csv")
    assert system.primary_knowledge_base is not None
    assert not system.primary_knowledge_base.empty

@pytest.mark.asyncio
async def test_basic_greeting():
    """Test basic greeting response"""
    system = SupportSystem("tests/data/test_knowledge_base.csv")
    response, missing_info = await system.process_query("hola")
    assert response.startswith("¡")
    assert missing_info is None

@pytest.mark.asyncio
async def test_store_status_query():
    """Test store status query processing"""
    system = SupportSystem("tests/data/test_knowledge_base.csv")
    query = "¿Está activo el comercio 100005336 de soprole?"
    response, missing_info = await system.process_query(query)
    assert response is not None
    assert isinstance(response, str)

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

# src/tests/test_mongodb.py
import pytest
from services.mongodb import MongoDBService

def test_store_status_check():
    """Test store status checking"""
    service = MongoDBService()
    status = service.check_store_status("test_company", "test_id")
    assert status is None  # Should be None with test credentials

def test_connection_error_handling():
    """Test MongoDB connection error handling"""
    service = MongoDBService()
    service.password = "invalid_password"
    with pytest.raises(Exception):
        service._get_client()