import os
import re
import json
import logging
import random
from typing import Dict, Optional, List, Tuple
import pandas as pd
import openai
from src.services.mongodb import MongoDBService

logger = logging.getLogger(__name__)

class SupportSystem:
    def __init__(self, knowledge_base_csv: str, knowledge_base_json: str = None):
        """Initialize the support system with multiple knowledge bases"""
        self.primary_knowledge_base = self._load_knowledge_base(knowledge_base_csv)
        self.secondary_knowledge_base = self._load_json_knowledge_base(knowledge_base_json) if knowledge_base_json else None
        self.openai_client = openai
        self.openai_client.api_key = self._get_env_variable('OPENAI_API_KEY')
        self.mongo_service = MongoDBService()

    def _get_env_variable(self, var_name: str) -> str:
        """Safely get environment variable"""
        value = os.getenv(var_name)
        if not value:
            logger.error(f"Environment variable '{var_name}' not defined")
            return "dummy_value_for_testing"
        return value

    def _load_knowledge_base(self, csv_path: str) -> pd.DataFrame:
        """Load knowledge base from CSV"""
        try:
            # Attempt to load the CSV
            if csv_path and os.path.exists(csv_path):
                df = pd.read_csv(csv_path, encoding='utf-8')
                logger.info(f"Successfully loaded knowledge base with {len(df)} entries")
                # Log first few entries for debugging
                logger.debug("First few knowledge base entries:")
                for _, row in df.head().iterrows():
                    logger.debug(f"Heading: {row['Heading']}")
                    logger.debug(f"Content: {row['Content']}\n")
                return df
            else:
                # For testing/development, create a minimal knowledge base
                logger.warning(f"CSV file not found at {csv_path}, creating minimal knowledge base")
                data = {
                    'Heading': ['La aplicación no permite ingresar pedidos'],
                    'Content': ['1. Asegúrate que la orden cumple con el monto mínimo (si existe) o los descuentos no superan el máximo\n2. Asegúrate de tener sincronizada la aplicación\n3. Asegúrate de tener buena señal de internet, de lo contrario las ordenes quedarán pendientes de procesar hasta que tengas buena señal']
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

    def _is_store_status_query(self, query: str) -> bool:
        """
        Check if the query is about store status using multiple methods
        """
        query_lower = query.lower().strip()
        
        # Direct patterns
        store_status_patterns = [
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
        
        pattern_match = any(pattern in query_lower for pattern in store_status_patterns)
        
        # Check for store ID pattern
        has_store_id = bool(re.search(r'\b\d{5,10}\b', query))
        
        # Check for business keywords
        business_keywords = ['comercio', 'tienda', 'negocio', 'local', 'soprole']
        has_business_word = any(keyword in query_lower for keyword in business_keywords)
        
        logger.info(f"Store status detection: pattern_match={pattern_match}, has_store_id={has_store_id}, has_business_word={has_business_word}")
        
        # If we have a store ID and a business keyword, it's likely a store query
        if has_store_id and has_business_word:
            return True
            
        # Otherwise, rely on pattern matching
        return pattern_match

    async def _extract_store_info(self, query: str) -> Dict:
        """Extract store information using pattern matching and GPT"""
        try:
            prompt = f"""Extrae la información del comercio de esta consulta de soporte.

Consulta: {query}

INSTRUCCIONES:
1. Extrae el nombre de la empresa y el ID del comercio.
2. Para consultas sobre comercios, necesitamos:
   - company_name: nombre de la empresa (en minúsculas)
   - store_id: ID del comercio

Si encuentras la información, responde con un JSON que incluya:
{{
    "is_store_query": true,
    "company_name": "nombre_empresa",
    "store_id": "id_comercio"
}}

Si no encuentras la información, responde:
{{
    "is_store_query": false,
    "company_name": null,
    "store_id": null
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un extractor de información preciso. Responde solo con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            logger.info(f"OpenAI extraction response: {content}")
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error extracting store info: {e}")
            return {
                "is_store_query": False,
                "company_name": None,
                "store_id": None
            }

    async def _get_general_response(self, query: str) -> Tuple[str, None]:
        """Generate general response using knowledge base"""
        try:
            # First, try to find relevant knowledge base entries
            relevant_entries = []
            if not self.primary_knowledge_base.empty:
                for _, row in self.primary_knowledge_base.iterrows():
                    if row['Heading'].lower() in query.lower() or query.lower() in row['Heading'].lower():
                        relevant_entries.append(f"Pregunta: {row['Heading']}\nRespuesta: {row['Content']}")

            # Build the prompt with knowledge base context
            knowledge_base_context = "\n\n".join(relevant_entries) if relevant_entries else ""
            
            prompt = f"""Como asistente de soporte de YOM, usa esta información de la base de conocimientos para responder la consulta:

CONOCIMIENTO RELEVANTE:
{knowledge_base_context}

CONSULTA DEL USUARIO:
{query}

INSTRUCCIONES:
- Si hay información relevante en la base de conocimientos, úsala para dar una respuesta específica y detallada.
- Si no hay información relevante, proporciona una respuesta general y sugiere contactar al soporte técnico.
- Mantén un tono amigable y profesional.
- Estructura la respuesta de manera clara y fácil de seguir."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente de soporte amigable para YOM. Respondes en español de manera clara y útil."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content, None
            
        except Exception as e:
            logger.error(f"Error getting general response: {e}")
            return "Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con soporte directamente.", None

    async def process_query(self, query: str, user_name: Optional[str] = None) -> Tuple[str, Optional[List[str]]]:
        """Process incoming queries and generate responses"""
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

        # Check if it's a store status query
        is_store_query = self._is_store_status_query(query)
        logger.info(f"Is store query: {is_store_query}")
        
        if is_store_query:
            logger.info("Processing store status query...")
            # Extract store information
            store_info = await self._extract_store_info(query)
            logger.info(f"Extracted store info: {store_info}")
            
            if not store_info["company_name"] or not store_info["store_id"]:
                logger.info("Missing store information in query")
                return (
                    "Para poder verificar el estado del comercio necesito dos datos importantes:\n\n"
                    "1️⃣ El ID del comercio (por ejemplo: 100005336)\n"
                    "2️⃣ El nombre de la empresa (por ejemplo: soprole)\n\n"
                    "¿Podrías proporcionarme esta información? 🤔",
                    ["company_name", "store_id"]
                )
            
            # Check store status in MongoDB
            logger.info(f"Checking MongoDB status for company: {store_info['company_name']}, store_id: {store_info['store_id']}")
            store_status = self.mongo_service.check_store_status(
                store_info["company_name"],
                store_info["store_id"]
            )
            logger.info(f"MongoDB store status result: {store_status}")
            
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
        logger.info("Getting general response...")
        response = await self._get_general_response(query)
        return response