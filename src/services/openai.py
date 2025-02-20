import logging
import json
import openai
from src.config import Config

logger = logging.getLogger(__name__)
class OpenAIAPI:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY

    def analyze_query(self, system_instructions, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": query}
                ],
            )
            content = response.choices[0].message.content.strip()
            content = content.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(content)
            return analysis
        except Exception as e:
            logger.error(f"Error calling OpenAI or parsing response: {str(e)}", exc_info=True)
            raise
