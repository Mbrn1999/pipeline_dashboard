from fastapi import FastAPI
import os
from dotenv import load_dotenv
import requests



# Charger les variables depuis .env
load_dotenv()
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")


# ✅ On crée l'objet FastAPI AVANT les routes
app = FastAPI()

# Route racine simple pour tester
@app.get("/")
def root():
    return {"status": "ok"}

# Route login Strava
@app.get("/login")
def login():
    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        "&redirect_uri=http://localhost:8001/callback"
        "&approval_prompt=auto"
        "&scope=read,activity:read_all"
    )
    return {"auth_url": auth_url}




@app.get("/callback")
def callback(code: str):
    """
    Cette route reçoit le code Strava après autorisation
    et récupère le access_token et refresh_token.
    """
    token_url = "https://www.strava.com/oauth/token"
    response = requests.post(
        token_url,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
    )
    # Retourne le JSON reçu de Strava
    return response.json()