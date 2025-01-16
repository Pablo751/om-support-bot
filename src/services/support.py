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
        """Initialize the support system with knowledge bases"""
        self.primary_knowledge_base = self._load_knowledge_base(knowledge_base_csv)
        self.openai_client = openai
        self.openai_client.api_key = self._get_env_variable('OPENAI_API_KEY')
        self.mongo_service = MongoDBService()

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
            prompt = f"""Analiza esta consulta de soporte y proporciona la respuesta adecuada.

CONSULTA: {query}

BASE DE CONOCIMIENTOS:
{knowledge_base_context}

INSTRUCCIONES:

1. PRIMERO: Clasifica el tipo de consulta:
   A. CONSULTA DE ESTADO DE COMERCIO: Si preguntan sobre el estado/activación de un comercio específico.
   B. CONSULTA GENERAL: Cualquier otra pregunta o problema.

2. SEGUNDO: Según el tipo de consulta:

   Si es CONSULTA DE ESTADO DE COMERCIO:
   - Extrae el ID del comercio y nombre de empresa si están presentes
   - Si falta información, pide los datos necesarios
   - Si tienes toda la información, indica que verificarás el estado

   Si es CONSULTA GENERAL:
   - Busca información relevante en la base de conocimientos
   - Proporciona una respuesta detallada usando esa información
   - Si no hay información relevante, da una respuesta general útil

Responde con un JSON estructurado así:
{{
    "query_type": "STORE_STATUS" o "GENERAL",
    "response_type": "STORE_CHECK" o "MISSING_INFO" o "GENERAL_RESPONSE",
    "store_info": {{
        "company_name": string o null,
        "store_id": string o null
    }},
    "knowledge_base_refs": [índices de entradas relevantes o array vacío],
    "response_text": "texto de respuesta al usuario",
    "confidence": número entre 0 y 1
}}

EJEMPLOS:

Para "¿Está activo el comercio 100005336 de soprole?":
{{
    "query_type": "STORE_STATUS",
    "response_type": "STORE_CHECK",
    "store_info": {{
        "company_name": "soprole",
        "store_id": "100005336"
    }},
    "knowledge_base_refs": [],
    "response_text": "Verificaré el estado del comercio 100005336 de soprole.",
    "confidence": 0.95
}}

Para "Estado de mi comercio":
{{
    "query_type": "STORE_STATUS",
    "response_type": "MISSING_INFO",
    "store_info": {{
        "company_name": null,
        "store_id": null
    }},
    "knowledge_base_refs": [],
    "response_text": "Para poder verificar el estado del comercio necesito dos datos importantes:\\n\\n1️⃣ El ID del comercio (por ejemplo: 100005336)\\n2️⃣ El nombre de la empresa (por ejemplo: soprole)\\n\\n¿Podrías proporcionarme esta información? 🤔",
    "confidence": 0.9
}}"""

            # Get GPT's analysis and response
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente de soporte preciso para YOM. Analizas consultas y proporcionas respuestas detalladas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            analysis = json.loads(response.choices[0].message.content)
            logger.info(f"GPT Analysis: {analysis}")

            # Handle response based on analysis
            if analysis["query_type"] == "STORE_STATUS":
                if analysis["response_type"] == "STORE_CHECK":
                    # Check store status in MongoDB
                    store_status = self.mongo_service.check_store_status(
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
                else:  # MISSING_INFO
                    return (analysis["response_text"], ["company_name", "store_id"])

            # For general queries, return GPT's response
            return (analysis["response_text"], None)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return ("Lo siento, hubo un error procesando tu consulta. ¿Podrías reformularla?", None)
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return ("Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con soporte directamente.", None)
