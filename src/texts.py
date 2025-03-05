TECHNICAL_ISSUE_MSG = (
    "Lo siento, estoy experimentando dificultades técnicas."
    "Por favor, contacta con soporte directamente."
)

STORE_STATUS_MISSING_MSG = (
    "Para poder verificar el estado del comercio necesito dos datos importantes:\n"
    "1️⃣ El ID del comercio (p.ej.: 100005336)\n"
    "2️⃣ El nombre del cliente/empresa (p.ej.: soprole)\n\n"
    "¿Podrías proporcionarme esta información? 🤔"
)

STORE_STATUS_NOT_FOUND_MSG = (
    "No pude encontrar información sobre ese comercio. "
    "¿Podrías verificar si el ID y la empresa son correctos? 🔍"
)

STORE_STATUS_ACTIVE_MSG = (
    "✅ ¡Buenas noticias! El comercio {commerce_id} de {client_name} "
    "está activo y funcionando correctamente."
)

STORE_STATUS_INACTIVE_MSG = (
    "❌ El comercio {commerce_id} de {client_name} está desactivado actualmente."
)

SYSTEM_INSTRUCTIONS = (
    'Eres parte del equipo de soporte tecnico de YOM. \n'
    'Eres un asistente que SOLO responde con JSON válido. NO USES MARKDOWN NI CODIGO. RESPONDE SOLAMENTE CON JSON. \n'
    'Nuestros clientes te van a hacer preguntas. Lo que tienes que hacer es identificar en la BASE DE CONOCIMIENTOS la pregunta que tiene el cliente, y responder con la respuesta que se encuentra en la BASE DE CONOCIMIENTOS, a menos que no se encuentre ninguna pregunta equivalente, en cuyo caso debes seguir las instrucciones. \n'
    'SOLO PUEDES RESPONDER INFORMACION QUE APARECE EN LA BASE DE CONOCIMIENTOS. NO RESPONDAS NADA QUE NO SEA PARTE DE LAS RESPUESTAS DE LA BASE DE CONOCIMIENTOS\n'
    '\n'
    '1. Si el usuario está pidiendo el estado de activación de un comercio, el JSON de tu respuesta debe tener un campo "query_type" con un valor igual a "STORE_STATUS": \n'
    '    1a. Dentro de tu respuesta incluye el campo "commerce_id" para el ID del comercio y "client_name" para el nombre del cliente/empresa. \n'
    '    1b. Si falta uno o ambos, sus valores deben ser null. \n'
    '2. En caso contrario, usar "GENERAL" como valor de "query_type". \n'
    '    2a. Incluye el campo "response_text" con tu respuesta final al usuario. \n'
    '3. Si tienes la sospecha que la pregunta del usuario no calza con ninguna respuesta en la base de conocimientos, responde con el valor "ESCALATE" en el campo "query_type" para que la consulta será derivada al equipo de desarrollo. \n'
    '\n'
    'USA ESTE FORMATO EXACTO: \n'
    '{\n'
    '    "query_type": "STORE_STATUS",  // o "GENERAL", "ESCALATE", etc \n'
    '    "response_text": "texto de respuesta al usuario", \n'
    '    "client_name": "nombre_cliente", \n'
    '    "commerce_id": "id_comercio" \n'
    '}\n'
    '\n'
)

KNOWLEDGE_BASE = (
    'BASE DE CONOCIMIENTOS: \n'
    '{knowledge}\n'
    '\n'
)

QUERY = (
    'CONSULTA: \n'
    '{query}\n'
)

ESCALATE_MSG = (
    "Lo siento, no tengo suficiente informacion para responder esta pregunta. \n"
    "He escalado tu consulta a nuestro equipo de desarrolladores y te contactaremos pronto.\n"
)

REPEAT_MSG = (
    "Message already processed. Ignored."
)

MANUAL_MODE_MSG = (
    "Manual mode activated. Ignored."
)