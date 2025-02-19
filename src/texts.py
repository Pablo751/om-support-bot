TECHNICAL_ISSUE_MSG = (
    "Lo siento, estoy experimentando dificultades técnicas."
    "Por favor, contacta con soporte directamente."
)

STORE_STATUS_MISSING_MSG = (
    "Para poder verificar el estado del comercio necesito dos datos importantes:\n"
    "1️⃣ El ID del comercio (p.ej.: 100005336)\n"
    "2️⃣ El nombre de la empresa (p.ej.: soprole)\n\n"
    "¿Podrías proporcionarme esta información? 🤔"
)

STORE_NOT_FOUND_MSG = (
    "No pude encontrar información sobre ese comercio. "
    "¿Podrías verificar si el ID y la empresa son correctos? 🔍"
)

STORE_ACTIVE_MSG = (
    "✅ ¡Buenas noticias! El comercio {store_id} de {company_name} "
    "está activo y funcionando correctamente."
)

STORE_INACTIVE_MSG = (
    "❌ El comercio {store_id} de {company_name} está desactivado actualmente."
)

SYSTEM_INSTRUCTIONS = (
    'Eres un asistente que SOLO responde con JSON válido. '
    ''
    'NO USES MARKDOWN NI CODIGO. RESPONDE SOLAMENTE CON JSON.'
    ''
    'Analiza esta consulta de soporte y determina el tipo de consulta.'
    ''
    'INSTRUCCIONES:'
    '1. Si el usuario está pidiendo el estado de un comercio, revisa si proporcionó:'
    '- Un ID de comercio (STORE_ID) que sea numérico.'
    '- Un NOMBRE de la empresa (COMPANY_NAME).'
    '2. Si faltan uno o ambos, el "query_type" debe ser "STORE_STATUS_MISSING".'
    '3. Si sí proporcionó ambos, usa "STORE_STATUS".'
    '4. De lo contrario, "query_type": "GENERAL".'
    '5. "response_text": tu respuesta final al usuario.'
    '6. "store_info": si es STORE_STATUS o STORE_STATUS_MISSING, incluye los datos extraídos; si no hay datos, pon null.'
    ''
    'USA ESTE FORMATO EXACTO:'
    '{'
    '    "query_type": "STORE_STATUS",  // o "STORE_STATUS_MISSING" o "GENERAL"'
    '    "store_info": {'
    '        "company_name": "nombre_empresa o null",'
    '        "store_id": "id_comercio o null"'
    '    },'
    '    "response_text": "texto de respuesta al usuario"'
    '}'
)

KNOWLEDGE = (
    'BASE DE CONOCIMIENTOS:'
    '{knowledge}'
)

QUERY = (
    'CONSULTA: {query}'
)