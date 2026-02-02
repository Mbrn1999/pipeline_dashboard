"""
Script pour récupérer toutes les activités Strava et les envoyer dans Supabase
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Charger les variables d'environnement
load_dotenv()

# Configuration Strava
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_access_token():
    """
    Récupère un nouveau access_token en utilisant le refresh_token
    """
    token_url = "https://www.strava.com/oauth/token"

    response = requests.post(
        token_url,
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
    )

    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        print(f"Erreur lors de la récupération du token: {response.text}")
        return None


def get_all_strava_activities(access_token):
    """
    Récupère toutes les activités Strava de l'utilisateur
    """
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    all_activities = []
    page = 1
    per_page = 200  # Maximum autorisé par Strava

    while True:
        params = {
            "page": page,
            "per_page": per_page
        }

        response = requests.get(activities_url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Erreur lors de la récupération des activités: {response.text}")
            break

        activities = response.json()

        if not activities:  # Plus d'activités à récupérer
            break

        all_activities.extend(activities)
        print(f"Page {page}: {len(activities)} activités récupérées")
        page += 1

    print(f"Total: {len(all_activities)} activités récupérées")
    return all_activities


def format_activity(activity):
    """
    Formate une activité Strava pour l'insertion dans Supabase
    """
    return {
        "strava_id": activity["id"],
        "name": activity["name"],
        "sport_type": activity.get("sport_type", activity.get("type")),
        "distance": activity["distance"],  # en mètres
        "moving_time": activity["moving_time"],  # en secondes
        "elapsed_time": activity["elapsed_time"],  # en secondes
        "total_elevation_gain": activity["total_elevation_gain"],  # en mètres
        "start_date": activity["start_date"],
        "start_date_local": activity["start_date_local"],
        "average_speed": activity.get("average_speed"),  # en m/s
        "max_speed": activity.get("max_speed"),  # en m/s
        "average_heartrate": activity.get("average_heartrate"),
        "max_heartrate": activity.get("max_heartrate"),
        "elev_high": activity.get("elev_high"),
        "elev_low": activity.get("elev_low"),
        "kudos_count": activity.get("kudos_count", 0),
        "achievement_count": activity.get("achievement_count", 0),
    }


def send_to_supabase(activities):
    """
    Envoie les activités formatées dans Supabase
    """
    # Créer le client Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    success_count = 0
    error_count = 0

    for activity in activities:
        try:
            formatted_activity = format_activity(activity)

            # Utilise upsert pour éviter les doublons (basé sur strava_id)
            response = supabase.table("strava_activities").upsert(
                formatted_activity,
                on_conflict="strava_id"
            ).execute()

            success_count += 1
            print(f"✓ Activité '{activity['name']}' ({activity['start_date_local']}) envoyée")

        except Exception as e:
            error_count += 1
            print(f"✗ Erreur pour l'activité {activity['id']}: {e}")

    print(f"\n--- Résumé ---")
    print(f"Succès: {success_count}")
    print(f"Erreurs: {error_count}")
    print(f"Total: {len(activities)}")


def main():
    """
    Fonction principale
    """
    print("=== Script Strava → Supabase ===\n")

    # Vérifier les variables d'environnement
    if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
        print("❌ Erreur: Variables Strava manquantes dans .env")
        print("   Vérifiez: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN")
        return

    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Erreur: Variables Supabase manquantes dans .env")
        print("   Vérifiez: SUPABASE_URL, SUPABASE_KEY")
        return

    # 1. Récupérer un access_token
    print("1. Récupération de l'access token...")
    access_token = get_access_token()
    if not access_token:
        return
    print("   ✓ Access token obtenu\n")

    # 2. Récupérer toutes les activités
    print("2. Récupération des activités Strava...")
    activities = get_all_strava_activities(access_token)
    if not activities:
        print("   Aucune activité trouvée")
        return
    print(f"   ✓ {len(activities)} activités récupérées\n")

    # 3. Envoyer vers Supabase
    print("3. Envoi vers Supabase...")
    send_to_supabase(activities)

    print("\n✅ Script terminé!")


if __name__ == "__main__":
    main()