import os
import json
import logging
import random
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta

import pandas as pd
import certifi
from pymongo import MongoClient
import aiohttp
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Pydantic models
class WhatsAppMessage(BaseModel):
    wa_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class MessageResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    info: Optional[str] = None

class SupportSystem:
    def __init__(self, knowledge_base_csv: str, knowledge_base_json: str = None):
        """Initialize the support system with multiple knowledge bases"""
        self.primary_knowledge_base = self._load_knowledge_base(knowledge_base_csv)
        self.secondary_knowledge_base = self._load_json_knowledge_base(knowledge_base_json) if knowledge_base_json else None
        self.openai_client = openai
        openai.api_key = self._get_env_variable('OPENAI_API_KEY')
        self.mongo_username = "juanpablo_casado"
        self.mongo_password = self._get_env_variable('MONGO_PASSWORD')
        self.mongo_client = None

    def _get_env_variable(self, var_name: str) -> str:
        """Safely get environment variable"""
        value = os.getenv(var_name)
        if not value:
            logger.error(f"Environment variable '{var_name}' not defined")
            return "dummy_value_for_testing"  # For testing purposes
        return value

    def _load_knowledge_base(self, csv_path: str) -> pd.DataFrame:
        """Load knowledge base from CSV"""
        try:
            return pd.read_csv(csv_path, encoding='utf-8')
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return pd.DataFrame(columns=['Heading', 'Content'])

    def _load_json_knowledge_base(self, json_path: str) -> Dict:
        """Load JSON knowledge base"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON knowledge base: {e}")
            return None

    def _get_mongo_client(self):
        """Get MongoDB client with connection pooling"""
        if self.mongo_client is None:
            try:
                url = f"mongodb+srv://{self.mongo_username}:{self.mongo_password}@legacy-production-v6.dmjt9.mongodb.net/yom-production?retryWrites=true&w=majority"
                self.mongo_client = MongoClient(
                    url, 
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                self.mongo_client.admin.command('ping')
                logger.info("MongoDB connection successful.")
            except Exception as e:
                logger.error(f"Error connecting to MongoDB: {e}")
                self.mongo_client = None
                raise
        return self.mongo_client

    def _check_store_status(self, company_name: str, store_id: str) -> Optional[bool]:
        """Check store status in MongoDB"""
        filter_json = {
            "domain": f"{company_name}.youorder.me",
            "contact.externalId": store_id
        }
        
        try:
            client = self._get_mongo_client()
            if not client:
                return None
                
            db = client['yom-production']
            collection = db['commerces']
            
            store = collection.find_one(filter_json)
            logger.info(f"MongoDB search result for {filter_json}: {store}")
            
            if store:
                return store.get('active', False)
            return None
            
        except Exception as e:
            logger.error(f"MongoDB error: {str(e)}")
            return None

    async def _extract_store_info(self, query: str) -> Dict:
        """Use GPT to extract store information from query"""
        prompt = f"""Extrae la información del comercio de esta consulta de soporte.

Consulta: {query}

INSTRUCCIONES:
1. Extrae el nombre de la empresa y el ID del comercio.
2. Para consultas sobre comercios, necesitamos:
   - company_name: "nombre_empresa"
   - store_id: "ID_comercio"

EJEMPLOS:

Entrada: "Busca información del comercio con ID 100005336 en soprole"
Salida JSON esperada:
{{
    "is_store_query": true,
    "company_name": "soprole",
    "store_id": "100005336",
    "missing_info": [],
    "confidence": 0.95
}}

Entrada: "No puedo ver el comercio"
Salida JSON esperada:
{{
    "is_store_query": false,
    "company_name": null,
    "store_id": null,
    "missing_info": ["company_name", "store_id"],
    "confidence": 0.9
}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un extractor de información preciso. Responde solo con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            store_info = json.loads(content)
            logger.info(f"Store info extracted from query '{query}': {store_info}")
            return store_info
            
        except Exception as e:
            logger.error(f"Error extracting store info from query '{query}': {e}")
            return {
                "is_store_query": False,
                "company_name": None,
                "store_id": None,
                "missing_info": ["company_name", "store_id"],
                "confidence": 0.0
            }

    async def _classify_query(self, query: str) -> Dict:
        """Classification using GPT to distinguish between store status checks and other issues"""
        prompt = f"""Analiza esta consulta de soporte y clasifícala con precisión.

    Consulta: {query}

    INSTRUCCIONES DE CLASIFICACIÓN:
    
    1. STORE_STATUS - Clasificar como STORE_STATUS si:
    - Preguntas explícitas sobre si un comercio está ACTIVO/ACTIVADO
    - Consultas directas sobre el ESTADO DE ACTIVACIÓN
    - IMPORTANTE: Si la consulta incluye un ID de comercio Y nombre de empresa específicos
    
    2. GENERAL_INQUIRY:
    - TODOS los demás problemas o preguntas sobre comercios
    - Problemas de sincronización
    - Problemas de visibilidad
    - Problemas técnicos
    - Cualquier consulta que no sea específicamente sobre verificar activación"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un clasificador preciso de consultas de soporte."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            classification = json.loads(content)
            logger.info(f"Query classification for '{query}': {classification}")
            return classification
                
        except Exception as e:
            logger.error(f"Error classifying query '{query}': {e}")
            return {
                "category": "GENERAL_INQUIRY",
                "confidence": 0.0,
                "reasoning": "Error in classification"
            }

    async def _get_general_response(self, query: str) -> str:
        """Enhanced response generation using multiple knowledge bases"""
        # Combine knowledge from both bases
        primary_context = "\n\n".join([
            f"Topic: {row['Heading']}\nAnswer: {row['Content']}"
            for _, row in self.primary_knowledge_base.iterrows()
        ]) if not self.primary_knowledge_base.empty else ""
        
        secondary_context = ""
        if self.secondary_knowledge_base and 'faq' in self.secondary_knowledge_base:
            secondary_context = "\n\n".join([
                f"Q: {qa['question']}\nA: {qa['answer']}"
                for qa in self.secondary_knowledge_base['faq']
            ])

        prompt = f"""Como asistente de soporte de YOM, usa estas bases de conocimientos para responder la consulta.

    CONOCIMIENTO PRINCIPAL:
    {primary_context}

    CONOCIMIENTO SECUNDARIO:
    {secondary_context}

    Consulta del usuario: {query}

    Proporciona una respuesta útil y amigable en español. Si ninguna base de conocimientos contiene información relevante,
    proporciona una respuesta general útil y sugiere contactar con soporte para ayuda más específica."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente de soporte amigable para YOM. Respondes en español de manera clara y útil."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            logger.info(f"General response for query '{query}': {reply}")
            return reply
            
        except Exception as e:
            logger.error(f"Error getting general response for query '{query}': {e}")
            return "Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con soporte directamente a través de ayuda.yom.ai"

    async def process_query(self, query: str, user_name: Optional[str] = None) -> Tuple[str, Optional[List[str]]]:
        """Enhanced query processing with better store status handling"""
        # Handle basic greetings
        query_lower = query.lower().strip()
        if query_lower in ['hola', 'hello', 'hi', 'buenos dias', 'buenas tardes', 'buenas noches']:
            greetings = [
                f"¡Hola{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo ayudarte hoy? Si necesitas verificar el estado de un comercio, necesitaré el ID del comercio y el nombre de la empresa 😊",
                f"¡Hey{' ' + user_name if user_name else ''}! 🎉 Para ayudarte mejor, si necesitas verificar un comercio, por favor proporcióname el ID del comercio y el nombre de la empresa 💪",
                f"¡Bienvenido/a{' ' + user_name if user_name else ''}! 👋 ¿Necesitas verificar el estado de un comercio? Solo indícame el ID del comercio y el nombre de la empresa 🤝"
            ]
            return (random.choice(greetings), None)

        # Check for store status related patterns
        status_patterns = [
            'esta activ',
            'estado del comercio',
            'estado de la tienda',
            'mi comercio esta',
            'mi tienda esta',
            'el comercio esta',
            'la tienda esta',
            'comercio activ',
            'tienda activ',
        ]
        is_store_query = any(pattern in query_lower for pattern in status_patterns)
        
        # If it's not an obvious store query, classify using GPT
        if not is_store_query:
            classification = await self._classify_query(query)
            is_store_query = classification["category"] == "STORE_STATUS"

        # If it's a store query (either from keywords or classification)
        if is_store_query:
            store_info = await self._extract_store_info(query)
            
            if not store_info["company_name"] or not store_info["store_id"]:
                return (
                    "Para poder verificar el estado del comercio necesito dos datos importantes:\n\n"
                    "1️⃣ El ID del comercio (por ejemplo: 100005336)\n"
                    "2️⃣ El nombre de la empresa (por ejemplo: soprole)\n\n"
                    "¿Podrías proporcionarme esta información? 🤔",
                    ["company_name", "store_id"]
                )
            
            store_status = self._check_store_status(
                store_info["company_name"],
                store_info["store_id"]
            )
            
            if store_status is None:
                return (
                    "No pude encontrar información sobre ese comercio. ¿Podrías verificar si el ID y la empresa son correctos? 🔍", 
                    None
                )
            elif store_status:
                return (
                    f"✅ ¡Buenas noticias! El comercio {store_info['store_id']} de {store_info['company_name']} está activo y funcionando correctamente.", 
                    None
                )
            else:
                return (
                    f"❌ El comercio {store_info['store_id']} de {store_info['company_name']} está desactivado actualmente.", 
                    None
                )

        # For non-store queries, get general response
        response = await self._get_general_response(query)
        return (response, None)

class WhatsAppAPI:
    def __init__(self, api_key: str, base_url: str = "https://api.wasapi.io/prod/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, wa_id: str, message: str) -> Dict:
        """Send WhatsApp message with retry logic"""
        payload = {
            "message": message,
            "wa_id": wa_id
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/whatsapp-messages",
                json=payload
            ) as response:
                if response.status not in (200, 201):
                    logger.error(f"Error sending message: Status {response.status}")
                    raise HTTPException(status_code=response.status, detail="WhatsApp API error")
                return await response.json()
        except Exception as e:
            logger.error(f"Error sending message to {wa_id}: {str(e)}")
            raise

    async def close(self):
        """Cleanup resources"""
        await self.session.close()

# FastAPI app
app = FastAPI(title="YOM Support Bot", version="1.0.0")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(exc.detail)}
    )

# Update the Pydantic model at the top of the file
class WebhookRequest(BaseModel):
    message: str
    wa_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hola",
                "wa_id": "123456789"
            }
        }

# Initialize components
support_system = None
whatsapp_api = None
message_deduplication = {}

@app.on_event("startup")
async def startup_event():
    """Initialize components with knowledge bases"""
    global support_system, whatsapp_api
    
    api_key = os.getenv("WASAPI_API_KEY")
    if not api_key:
        raise ValueError("WASAPI_API_KEY not found in environment variables")
    
    # Initialize support system with knowledge bases
    support_system = SupportSystem(
        knowledge_base_csv='knowledge_base.csv',
        knowledge_base_json='knowledge_base.json'
    )
    whatsapp_api = WhatsAppAPI(api_key)
    
    logger.info("Support bot initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if whatsapp_api:
        await whatsapp_api.close()
    logger.info("Support bot shutdown complete")


@app.post("/webhook", response_model=MessageResponse, description="Handle incoming WhatsApp messages")
async def webhook(webhook_request: WebhookRequest):
    """Handle incoming WhatsApp messages"""
    try:
        # Process query and send response
        response_text, _ = await support_system.process_query(
            webhook_request.message,
            user_name=None
        )

        await whatsapp_api.send_message(webhook_request.wa_id, response_text)

        return {"success": True, "info": "Message processed successfully"}

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Internal server error: {str(e)}"}






@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")