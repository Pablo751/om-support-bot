import logging
import json
import openai
from src.config import Config

def summarize_knowledge(knowledge, query):
    messages = [
        {"role": "system", "content": "Devuelve la BASE DE CONOCIMIENTOS, pero borrando todas las preguntas que no sean relevantes para la consulta actual."},
        {"role": "user", "content": f"CONSULTA: {query}\n\n{knowledge}"}
    ]
    summary_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    summarized_knowledge = summary_response.choices[0].message.content
    return summarized_knowledge

logger = logging.getLogger(__name__)
class OpenAIAPI:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY

    def analyze_query(self, system_instructions, knowledge, query):
        try:
            knowledge = summarize_knowledge(knowledge, query)
            messages = [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": knowledge},
                {"role": "user", "content": query}
            ]
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
            content = response.choices[0].message.content.strip()
            content = content.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(content)
            return analysis
        except Exception as e:
            logger.error(f"Error calling OpenAI or parsing response: {str(e)}", exc_info=True)
            raise
