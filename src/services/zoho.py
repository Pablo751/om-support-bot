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
        self.access_token = self.get_access_token()

    def get_access_token(self):
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        token_response = requests.post(self.token_url, data=token_data)
        token_json = token_response.json()
        access_token = token_json.get("access_token")

        logger.info(f"New Access Token: {access_token}")
        return access_token
    
    async def send_message(self, ticket_id, response):        
        message = response.get("response_text")
        comment_url = f"{self.desk_domain}/api/v1/tickets/{ticket_id}/comments"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "orgId": self.org_id,
            "Content-Type": "application/json"
        }
        comment_data = {
            "content": message,
            "isPublic": False
        }
        comment_response = requests.post(comment_url, json=comment_data, headers=headers)
        comment_json = comment_response.json()
        return comment_json
