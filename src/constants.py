# src/constants.py
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Greeting messages
GREETING_MESSAGES = [
    "¡Hola! 👋",
    "¡Hey! 🎉",
    "¡Bienvenido/a! 👋"
]

# MongoDB Collections
COLLECTION_COMMERCES = "commerces"
DATABASE_NAME = "yom-production"

# Error Messages
ERROR_MESSAGES = {
    "store_not_found": "No pude encontrar información sobre ese comercio. ¿Podrías verificar si el ID y la empresa son correctos? 🔍",
    "missing_store_info": (
        "Para poder verificar el estado del comercio necesito dos datos importantes:\n\n"
        "1️⃣ El ID del comercio (por ejemplo: 100005336)\n"
        "2️⃣ El nombre de la empresa (por ejemplo: soprole)\n\n"
        "¿Podrías proporcionarme esta información? 🤔"
    ),
    "internal_error": "Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con soporte directamente a través de ayuda.yom.ai"
}

# Status Patterns
STORE_STATUS_PATTERNS = [
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

# Basic Greetings
BASIC_GREETINGS = ['hola', 'hello', 'hi', 'buenos dias', 'buenas tardes', 'buenas noches']