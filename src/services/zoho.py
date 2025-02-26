import logging
from src.config import Config
import requests

logger = logging.getLogger(__name__)

class ZohoAPI:
    def __init__(self):
        self.client_id = Config.ZOHO_CLIENT_ID
        self.client_secret = Config.ZOHO_CLIENT_SECRET
        self.refresh_token = Config.ZOHO_REFRESH_TOKEN
        self.token_url = Config.ZOHO_TOKEN_URL
        self.desk_domain = Config.ZOHO_DESK_DOMAIN
        self.org_id = Config.ZOHO_ORG_ID
        self.department_id = Config.ZOHO_DEPARTMENT_ID
        self.access_token = self._fetch_access_token()
        self.headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "orgId": self.org_id,
            "Content-Type": "application/json"
        }

    def _fetch_access_token(self):
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        response = requests.post(self.token_url, data=token_data)
        token_json = response.json()
        access_token = token_json.get("access_token")
        logger.info(f"New Access Token: {access_token}")
        return access_token

    def send_message(self, ticket_id, message):
        logger.info(f"Sending message: {message}")
        comment_url = f"{self.desk_domain}/api/v1/tickets/{ticket_id}/comments"
        comment_data = {
            "content": message,
            "isPublic": False
        }
        response = requests.post(comment_url, json=comment_data, headers=self.headers)
        return response.json()

    def create_ticket(self, subject, description):
        logger.info(f"Creating ticket with subject: {subject}")
        ticket_data = {
            "departmentId": self.department_id,
            "contact" : {
                "firstName": "Nombre",
                "lastName": "Apellido",
            },
            "subject": subject,
            "description": description
        }
        ticket_url = f"{self.desk_domain}/api/v1/tickets"
        response = requests.post(ticket_url, json=ticket_data, headers=self.headers)
        return response.json()
