import os
import re
import json
import logging
import random
import certifi
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import pandas as pd
import openai
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class ConversationState:
    def __init__(self):
        self.human_assigned = False
        self.last_human_interaction = None
        self.handoff_threshold = 24 * 60 * 60  # 24 hours in seconds

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

    async def process_query(self, query: str, user_name: Optional[str] = None) -> Tuple[str, Optional[List[str]]]:
        """Process incoming queries using GPT for the entire flow."""
        logger.info(f"Processing query: {query}")
    
        # Handle basic greetings
        query_lower = query.lower().strip()
        if query_lower in ['hola', 'hello', 'hi', 'buenos dias', 'buenas tardes', 'buenas noches']:
            greetings = [
                f"¡Hola{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo ayudarte hoy?",
                f"¡Hey{' ' + user_name if user_name else ''}! 🎉 ¿Cómo puedo ayudarte?",
                f"¡Bienvenido/a{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo asistirte?"
            ]
            return (random.choice(greetings), None)
    
        try:
            # Prepare knowledge base context
            knowledge_base_context = ""
            if not self.primary_knowledge_base.empty:
                knowledge_entries = []
                for _, row in self.primary_knowledge_base.iterrows():
                    knowledge_entries.append(f"Tema: {row['Heading']}\nRespuesta: {row['Content']}")
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
    5. "response_text": tu respuesta final al usuario.
    6. "store_info": si es STORE_STATUS o STORE_STATUS_MISSING, incluye los datos extraídos; si no hay datos, pon null.
    
    USA ESTE FORMATO EXACTO:
    {{
        "query_type": "STORE_STATUS",  // o "STORE_STATUS_MISSING" o "GENERAL"
        "store_info": {{
            "company_name": "nombre_empresa o null",
            "store_id": "id_comercio o null"
        }},
        "response_text": "texto de respuesta al usuario"
    }}"""
    
            logger.info("Sending request to OpenAI")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un asistente que SOLO responde con JSON válido. NO uses markdown, NO uses comillas triples, NO añadas explicaciones. SOLO JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1
            )
    
            # Extract and clean the content
            content = response.choices[0].message.content.strip()
            content = content.replace('```json', '').replace('```', '').strip()
            logger.info(f"OpenAI response content: {content}")
    
            try:
                # Parse the JSON response
                analysis = json.loads(content)
                logger.info(f"Parsed GPT Analysis: {analysis}")
    
                query_type = analysis.get("query_type", "GENERAL")
                # Safely extract store_info only if it's a dict
                store_info = analysis.get("store_info", None)
                if not isinstance(store_info, dict):
                    store_info = {}
    
                company_name = store_info.get("company_name")
                store_id = store_info.get("store_id")
                response_text = analysis.get("response_text", "")
    
                # -------------------- HANDLE "STORE_STATUS" --------------------
                if query_type == "STORE_STATUS":
                    store_status = self._check_store_status(company_name, store_id)
                    if store_status is None:
                        return (
                            "No pude encontrar información sobre ese comercio. ¿Podrías verificar si el ID y la empresa son correctos? 🔍",
                            None
                        )
                    elif store_status:
                        return (
                            f"✅ ¡Buenas noticias! El comercio {store_id} de {company_name} está activo y funcionando correctamente.",
                            None
                        )
                    else:
                        return (
                            f"❌ El comercio {store_id} de {company_name} está desactivado actualmente.",
                            None
                        )
    
                # -------------------- HANDLE "STORE_STATUS_MISSING" --------------------
                elif query_type == "STORE_STATUS_MISSING":
                    return (
                        "Para poder verificar el estado del comercio necesito dos datos importantes:\n\n"
                        "1️⃣ El ID del comercio (por ejemplo: 100005336)\n"
                        "2️⃣ El nombre de la empresa (por ejemplo: soprole)\n\n"
                        "¿Podrías proporcionarme esta información? 🤔",
                        ["company_name", "store_id"]
                    )
    
                # -------------------- HANDLE "GENERAL" --------------------
                else:
                    # Just return GPT's response as a general answer
                    return (response_text, None)
    
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error with content: {content}")
                logger.error(f"Error details: {str(e)}")
                return ("Lo siento, hubo un error técnico. ¿Podrías intentar reformular tu pregunta?", None)
    
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return ("Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con soporte directamente.", None)


    def __del__(self):
        """Cleanup MongoDB connection"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed.")

class EnhancedSupportSystem(SupportSystem):
    def __init__(self, knowledge_base_csv: str, knowledge_base_json: str = None):
        super().__init__(knowledge_base_csv, knowledge_base_json)
        self.conversations: Dict[str, ConversationState] = {}
        
    def _get_conversation_state(self, wa_id: str) -> ConversationState:
        if wa_id not in self.conversations:
            self.conversations[wa_id] = ConversationState()
        return self.conversations[wa_id]

    def _should_bot_respond(self, wa_id: str, message_metadata: dict) -> bool:
        state = self._get_conversation_state(wa_id)
        
        # If message is from an agent, update state
        if message_metadata.get('from_agent'):
            state.human_assigned = True
            state.last_human_interaction = datetime.now()
            return False
            
        # If no human assigned, bot should respond
        if not state.human_assigned:
            return True
            
        # Check timeout
        if (state.last_human_interaction and 
            (datetime.now() - state.last_human_interaction).total_seconds() > state.handoff_threshold):
            state.human_assigned = False
            state.last_human_interaction = None
            return True
            
        return False

    async def process_query(self, query: str, wa_id: str, message_metadata: dict, user_name: Optional[str] = None) -> Tuple[str, Optional[List[str]]]:
            """Enhanced query processing that preserves original classification logic"""
            logger.info(f"Processing query: {query}")
    
            # First check if we should respond at all
            if not self._should_bot_respond(wa_id, message_metadata):
                return None, None
    
            # Handle basic greetings (preserve original logic)
            query_lower = query.lower().strip()
            if query_lower in ['hola', 'hello', 'hi', 'buenos dias', 'buenas tardes', 'buenas noches']:
                greetings = [
                    f"¡Hola{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo ayudarte hoy?",
                    f"¡Hey{' ' + user_name if user_name else ''}! 🎉 ¿Cómo puedo ayudarte?",
                    f"¡Bienvenido/a{' ' + user_name if user_name else ''}! 👋 ¿En qué puedo asistirte?"
                ]
                return (random.choice(greetings), None)
    
            try:
                # Prepare knowledge base context
                knowledge_base_context = ""
                if not self.primary_knowledge_base.empty:
                    knowledge_entries = []
                    for _, row in self.primary_knowledge_base.iterrows():
                        knowledge_entries.append(f"Tema: {row['Heading']}\nRespuesta: {row['Content']}")
                    knowledge_base_context = "\n\n".join(knowledge_entries)
    
                # First, check if query needs human attention
                confidence_prompt = f"""Analiza esta consulta y determina si requiere atención humana.
    
                CONSULTA: {query}
    
                BASE DE CONOCIMIENTOS:
                {knowledge_base_context}
    
                Considera que una consulta necesita atención humana si:
                1. Es un problema técnico complejo
                2. Involucra problemas específicos de una cuenta
                3. El usuario está claramente frustrado o enojado
                4. Requiere acceso a sistemas no disponibles para el bot
                5. Es sobre un tema sensible
                6. El usuario pide explícitamente un agente humano
                7. La consulta está fuera del alcance de la base de conocimientos
    
                RESPONDE SOLO CON JSON:
                {{
                    "needs_human": true/false,
                    "reason": "explicación breve"
                }}"""
    
                # Removed await - using synchronous call
                human_check = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Eres un asistente que SOLO responde con JSON válido."},
                        {"role": "user", "content": confidence_prompt}
                    ],
                    temperature=0.1
                )
    
                human_analysis = json.loads(human_check.choices[0].message.content.strip())
                
                if human_analysis.get("needs_human", False):
                    # Update state and return handoff message
                    state = self._get_conversation_state(wa_id)
                    state.human_assigned = True
                    state.last_human_interaction = datetime.now()
                    return ("Para brindarte la mejor asistencia posible, transferiré tu consulta a un agente de soporte. En breve te atenderá un agente humano. 🤝", None)
    
                # If bot can handle it, continue with classification
                classification_prompt = f"""NO USES MARKDOWN NI CODIGO. RESPONDE SOLAMENTE CON JSON.
    
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
                5. "response_text": tu respuesta final al usuario.
                6. "store_info": si es STORE_STATUS o STORE_STATUS_MISSING, incluye los datos extraídos; si no hay datos, pon null.
    
                USA ESTE FORMATO EXACTO:
                {{
                    "query_type": "STORE_STATUS",  // o "STORE_STATUS_MISSING" o "GENERAL"
                    "store_info": {{
                        "company_name": "nombre_empresa o null",
                        "store_id": "id_comercio o null"
                    }},
                    "response_text": "texto de respuesta al usuario"
                }}"""
    
                # Removed await - using synchronous call
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Eres un asistente que SOLO responde con JSON válido."},
                        {"role": "user", "content": classification_prompt}
                    ],
                    temperature=0.1
                )
    
                content = response.choices[0].message.content.strip()
                content = content.replace('```json', '').replace('```', '').strip()
                
                analysis = json.loads(content)
                query_type = analysis.get("query_type", "GENERAL")
                store_info = analysis.get("store_info", {}) if isinstance(analysis.get("store_info"), dict) else {}
                
                company_name = store_info.get("company_name")
                store_id = store_info.get("store_id")
                response_text = analysis.get("response_text", "")
    
                # Handle different query types
                if query_type == "STORE_STATUS":
                    store_status = self._check_store_status(company_name, store_id)
                    if store_status is None:
                        return ("No pude encontrar información sobre ese comercio. ¿Podrías verificar si el ID y la empresa son correctos? 🔍", None)
                    elif store_status:
                        return (f"✅ ¡Buenas noticias! El comercio {store_id} de {company_name} está activo y funcionando correctamente.", None)
                    else:
                        return (f"❌ El comercio {store_id} de {company_name} está desactivado actualmente.", None)
    
                elif query_type == "STORE_STATUS_MISSING":
                    return (
                        "Para poder verificar el estado del comercio necesito dos datos importantes:\n\n"
                        "1️⃣ El ID del comercio (por ejemplo: 100005336)\n"
                        "2️⃣ El nombre de la empresa (por ejemplo: soprole)\n\n"
                        "¿Podrías proporcionarme esta información? 🤔",
                        ["company_name", "store_id"]
                    )
    
                else:
                    return (response_text, None)
    
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                return ("Lo siento, hubo un error técnico. ¿Podrías intentar reformular tu pregunta?", None)
    
            except Exception as e:
                logger.error(f"Error processing query: {e}", exc_info=True)
                return ("Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con soporte directamente.", None)

    def handle_human_response(self, wa_id: str):
        """Record human agent interaction"""
        state = self._get_conversation_state(wa_id)
        state.human_assigned = True
        state.last_human_interaction = datetime.now()

    def release_to_bot(self, wa_id: str):
        """Release conversation back to bot"""
        if wa_id in self.conversations:
            del self.conversations[wa_id]
