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

