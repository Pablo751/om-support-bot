import os
import re
import json
import logging
import random
import certifi
from bson.objectid import ObjectId
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import pandas as pd
import openai
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class SupportSystem:
    def __init__(self, knowledge_base_csv: str, knowledge_base_json: str = None):
        """Initialize the support system with knowledge bases"""
        self.primary_knowledge_base = self._load_knowledge_base(knowledge_base_csv)
        self.secondary_knowledge_base = self._load_json_knowledge_base(knowledge_base_json) if knowledge_base_json else None
        self.openai_client = openai
        self.openai_client.api_key = self._get_env_variable('OPENAI_API_KEY')
        self.mongo_username = "juanpablo_casado"
        self.mongo_password = self._get_env_variable('MONGO_PASSWORD')
        self.mongo_client = None

    def _get_env_variable(self, var_name: str) -> str:
        """Safely get environment variable"""
        value = os.getenv(var_name)
        if not value:
            raise EnvironmentError(f"Environment variable '{var_name}' not defined.")
        return value

    def _load_knowledge_base(self, csv_path: str) -> pd.DataFrame:
        """Load knowledge base from CSV"""
        try:
            # Attempt to load the CSV
            if csv_path and os.path.exists(csv_path):
                df = pd.read_csv(csv_path, encoding='utf-8')
                logger.info(f"Successfully loaded knowledge base with {len(df)} entries")
                return df
            else:
                # For testing/development, create a minimal knowledge base
                logger.warning(f"CSV file not found at {csv_path}, creating minimal knowledge base")
                data = {
                    'Heading': ['La aplicación no permite ingresar pedidos'],
                    'Content': ['1. Asegúrate que la orden cumple con el monto mínimo (si existe).\n2. Asegúrate de tener sincronizada la aplicación.\n3. Verifica tu conexión a internet.']
                }
                return pd.DataFrame(data)
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
                logger.info("MongoDB connection successful")
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

    async def _create_support_ticket(self, wa_id: str, query: str) -> Dict:
        """Create a new support ticket in MongoDB queries collection"""
        client = self._get_mongo_client()
        db = client['yom-production']
        collection = db['queries']  # Updated collection name
        
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")  # ISO 8601 format
        
        ticket = {
            'wa_id': wa_id,
            'status': 'pending',
            'query': query,
            'created_at': now,
            'assigned_to': None,
            'assigned_at': None,
            'resolved_at': None,
            'messages': [{
                'timestamp': now,
                'content': query,
                'sender': 'customer',
                'message_id': f"msg_{ObjectId()}"  # Generate unique message ID
            }]
        }
        
        result = collection.insert_one(ticket)
        return collection.find_one({'_id': result.inserted_id})

    async def handle_agent_response(self, ticket_id: str, response: str, agent_id: str) -> bool:
        """Handle agent response to a ticket"""
        client = self._get_mongo_client()
        db = client['yom-production']
        collection = db['queries']  # Updated collection name
        
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Update ticket with agent's response
        result = collection.update_one(
            {'_id': ObjectId(ticket_id)},  # Convert string ID to ObjectId
            {
                '$set': {
                    'status': 'resolved',
                    'resolved_at': now,
                    'assigned_to': agent_id
                },
                '$push': {
                    'messages': {
                        'timestamp': now,
                        'content': response,
                        'sender': 'agent',
                        'message_id': f"msg_{ObjectId()}"
                    }
                }
            }
        )
        
        return result.modified_count > 0
    
    async def get_ticket_history(self, wa_id: str) -> List[Dict]:
        """Get conversation history for a specific WhatsApp ID"""
        client = self._get_mongo_client()
        db = client['yom-production']
        collection = db['queries']
        
        # Find all tickets for this wa_id, sorted by created_at
        tickets = list(collection.find(
            {'wa_id': wa_id},
            {'messages': 1, 'status': 1, 'created_at': 1}
        ).sort('created_at', -1))
        
        return tickets

    async def check_mongo_connection(self):
        """Verify MongoDB connection and collection access"""
        try:
            client = self._get_mongo_client()
            db = client['yom-production']
            collection = db['queries']
            
            # Try to perform a simple operation
            result = collection.find_one({})
            logger.info(f"MongoDB connection test: {'successful' if result is not None else 'no documents found'}")
            return True
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            return False

    async def process_query(self, query: str, wa_id: str, user_name: Optional[str] = None) -> Tuple[str, bool]:
        """Process incoming queries using GPT and determine if human handoff is needed."""
        logger.info(f"Processing query for wa_id {wa_id}: {query}")
        
        # Handle basic greetings
        query_lower = query.lower().strip()
        if query_lower in ['hola', 'hello', 'hi', 'buenos dias', 'buenas tardes', 'buenas noches']:
            greetings = [
                f"¡Hola{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo ayudarte hoy?",
                f"¡Hey{' ' + user_name if user_name else ''}! 🎉 ¿Cómo puedo ayudarte?",
                f"¡Bienvenido/a{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo asistirte?"
            ]
            return random.choice(greetings), False
        
        try:
            # Analyze query with GPT
            analysis = await self._analyze_with_gpt(query)
            logger.info(f"GPT Analysis: {analysis}")
            
            query_type = analysis.get("query_type", "GENERAL")
            needs_human = analysis.get('needs_human', True)  # Default to True if not specified
            confidence = analysis.get('confidence', 0)
            response_text = analysis.get('response_text', "")
            
            # Handle different query types
            if query_type == "STORE_STATUS":
                store_info = analysis.get("store_info", {})
                company_name = store_info.get("company_name")
                store_id = store_info.get("store_id")
                
                if company_name and store_id:
                    store_status = self._check_store_status(company_name, store_id)
                    if store_status is None:
                        return (
                            "No pude encontrar información sobre ese comercio. ¿Podrías verificar si el ID y la empresa son correctos? 🔍",
                            True  # Handoff to human
                        )
                    elif store_status:
                        return (
                            f"✅ ¡Buenas noticias! El comercio {store_id} de {company_name} está activo y funcionando correctamente.",
                            False
                        )
                    else:
                        return (
                            f"❌ El comercio {store_id} de {company_name} está desactivado actualmente.",
                            False
                        )
            
            # If confidence is low or needs human attention, create a support ticket
            if needs_human or confidence < 0.7:
                logger.info(f"Creating support ticket for wa_id {wa_id}")
                try:
                    ticket = await self._create_support_ticket(wa_id, query)
                    logger.info(f"Support ticket created: {ticket}")
                    return (
                        "Un agente revisará tu consulta pronto. Te contactaremos a la brevedad.",
                        True
                    )
                except Exception as e:
                    logger.error(f"Error creating ticket: {e}")
                    raise
            
            return response_text, False
            
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            # Create ticket on error
            try:
                ticket = await self._create_support_ticket(wa_id, query)
                return ("Lo siento, estoy teniendo problemas técnicos. Un agente te ayudará pronto.", True)
            except Exception as ticket_error:
                logger.error(f"Error creating error ticket: {ticket_error}")
                raise

    async def _analyze_with_gpt(self, query: str) -> dict:
        """Analyze query using GPT and return structured response."""
        try:
            # Prepare knowledge base context
            knowledge_base_context = ""
            if not self.primary_knowledge_base.empty:
                knowledge_entries = [
                    f"Tema: {row['Heading']}\nRespuesta: {row['Content']}"
                    for _, row in self.primary_knowledge_base.iterrows()
                ]
                knowledge_base_context = "\n\n".join(knowledge_entries)
        
            prompt = f"""NO USES MARKDOWN NI CODIGO. RESPONDE SOLAMENTE CON JSON.
            
            Analiza esta consulta de soporte y determina el tipo de consulta.
            
            CONSULTA: {query}
            
            BASE DE CONOCIMIENTOS:
            {knowledge_base_context}
            
            INSTRUCCIONES:
            1. Si el usuario está pidiendo el estado de un comercio, revisa si proporcionó:
               - Un ID de comercio (STORE_ID) que sea numérico.
               - Un NOMBRE de la empresa (COMPANY_NAME).
            2. Si faltan uno o ambos, el "query_type" debe ser "STORE_STATUS_MISSING".
            3. Si sí proporcionó ambos, usa "STORE_STATUS".
            4. De lo contrario, "query_type": "GENERAL".
            5. Añade un campo "needs_human": true/false basado en si la consulta requiere atención humana.
            6. Añade un campo "confidence": 0.0-1.0 indicando tu confianza en la respuesta.
            7. "response_text": tu respuesta final al usuario.
            
            USA ESTE FORMATO EXACTO:
            {{
                "query_type": "STORE_STATUS/STORE_STATUS_MISSING/GENERAL",
                "store_info": {{
                    "company_name": "nombre_empresa o null",
                    "store_id": "id_comercio o null"
                }},
                "needs_human": true/false,
                "confidence": 0.0-1.0,
                "response_text": "texto de respuesta al usuario"
            }}"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "SOLO JSON."}, {"role": "user", "content": prompt}],
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"Error in _analyze_with_gpt: {e}")
            return {"needs_human": True, "response_text": "Hubo un problema técnico al procesar tu consulta."}

    def __del__(self):
        """Cleanup MongoDB connection"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed.")
