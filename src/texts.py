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

STORE_NOT_FOUND_MSG = (
    "No pude encontrar información sobre ese comercio. "
    "¿Podrías verificar si el ID y la empresa son correctos? 🔍"
)

STORE_ACTIVE_MSG = (
    "✅ ¡Buenas noticias! El comercio {commerce_id} de {client_name} "
    "está activo y funcionando correctamente."
)

STORE_INACTIVE_MSG = (
    "❌ El comercio {commerce_id} de {client_name} está desactivado actualmente."
)

SYSTEM_INSTRUCTIONS = (
    'Eres parte del equipo de soporte tecnico de YOM. \n'
    'Eres un asistente que SOLO responde con JSON válido. NO USES MARKDOWN NI CODIGO. RESPONDE SOLAMENTE CON JSON. \n'
    'Nuestros clientes te van a hacer preguntas. Lo que tienes que hacer es identificar en la BASE DE CONOCIMIENTOS la pregunta estandar que mas se acerque a la que tiene el cliente, y responder con la respuesta que se encuentra en la BASE DE CONOCIMIENTOS. \n'
    '\n'
    'INSTRUCCIONES: \n'
    '1. Si el usuario está pidiendo el estado de un comercio, el JSON de tu respuesta debe tener un campo "query_type" con un valor igual a "STORE_STATUS": \n'
    '1a. Dentro de tu respuesta incluye el campo "commerce_id" para el ID del comercio y "client_name" para el nombre del cliente/empresa. \n'
    '1b. Si falta uno o ambos, sus valores deben ser null. \n'
    '2. En caso contrario, usar "GENERAL" como valor de "query_type". \n'
    '2a. Incluye el campo "response_text" con tu respuesta final al usuario. \n'
    '\n'
    'USA ESTE FORMATO EXACTO: \n'
    '{{\n'
    '    "query_type": "STORE_STATUS",  // o "GENERAL"\n'
    '    "response_text": "texto de respuesta al usuario", \n'
    '    "client_name": "nombre_cliente", // Esta informacion no siempre es explicita. Por ejemplo, te dira que es de _algo_, pero sin especificar que es _algo_ es el nombre del cliente/empresa. Lo mismo con el dominio del correo, o cualquier otra pista. \n'
    '    "commerce_id": "id_comercio" \n'
    '}}\n'
    '\n'
    'BASE DE CONOCIMIENTOS: \n'
    '{knowledge}'
)

QUERY = (
    'CONSULTA: \n'
    '{query}'
)