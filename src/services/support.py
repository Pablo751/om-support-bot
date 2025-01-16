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
        """Process incoming queries using GPT for the entire flow"""
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

            # Single GPT call to analyze the query and generate response
            prompt = f"""NO USES MARKDOWN NI CODIGO. RESPONDE SOLAMENTE CON JSON.

Analiza esta consulta de soporte y proporciona la respuesta adecuada.

CONSULTA: {query}

BASE DE CONOCIMIENTOS:
{knowledge_base_context}

INSTRUCCIONES:
1. Determina si es una consulta sobre el estado de un comercio o una consulta general
2. Extrae la información relevante
3. Genera una respuesta apropiada

DEBES RESPONDER CON ESTE FORMATO JSON EXACTO:
{{
    "query_type": "STORE_STATUS",
    "store_info": {{
        "company_name": "nombre_empresa o null",
        "store_id": "id_comercio o null"
    }},
    "response_text": "texto de respuesta al usuario",
    "use_knowledge_base": false
}}"""

            # Get GPT's analysis and response
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

                # Handle store status queries
                if analysis["query_type"] == "STORE_STATUS":
                    if analysis["store_info"]["company_name"] and analysis["store_info"]["store_id"]:
                        # Check store status in MongoDB
                        store_status = self._check_store_status(
                            analysis["store_info"]["company_name"],
                            analysis["store_info"]["store_id"]
                        )
                        
                        if store_status is None:
                            return (
                                "No pude encontrar información sobre ese comercio. ¿Podrías verificar si el ID y la empresa son correctos? 🔍",
                                None
                            )
                        elif store_status:
                            return (
                                f"✅ ¡Buenas noticias! El comercio {analysis['store_info']['store_id']} de {analysis['store_info']['company_name']} está activo y funcionando correctamente.",
                                None
                            )
                        else:
                            return (
                                f"❌ El comercio {analysis['store_info']['store_id']} de {analysis['store_info']['company_name']} está desactivado actualmente.",
                                None
                            )
                    else:
                        return (
                            "Para poder verificar el estado del comercio necesito dos datos importantes:\n\n"
                            "1️⃣ El ID del comercio (por ejemplo: 100005336)\n"
                            "2️⃣ El nombre de la empresa (por ejemplo: soprole)\n\n"
                            "¿Podrías proporcionarme esta información? 🤔",
                            ["company_name", "store_id"]
                        )

                # For general queries, return GPT's response
                return (analysis["response_text"], None)

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
