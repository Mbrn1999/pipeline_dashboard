"""
Script de diagnostic pour vérifier la dernière activité et ses streams GPS
"""
import os
import sys
import requests
from dotenv import load_dotenv
from supabase import create_client

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Charger les variables d'environnement
load_dotenv()

# Configuration
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_access_token():
    """Récupère un access token"""
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
        return response.json()["access_token"]
    return None


def main():
    print("=== Diagnostic de la dernière activité ===\n")

    # 1. Récupérer l'access token
    print("1. Récupération de l'access token...")
    access_token = get_access_token()
    if not access_token:
        print("❌ Impossible de récupérer l'access token")
        return
    print("✓ Access token obtenu\n")

    # 2. Récupérer la dernière activité de Strava
    print("2. Récupération de la dernière activité sur Strava...")
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"page": 1, "per_page": 1}

    response = requests.get(activities_url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Erreur: {response.text}")
        return

    activities = response.json()
    if not activities:
        print("❌ Aucune activité trouvée")
        return

    activity = activities[0]
    print(f"✓ Activité trouvée:")
    print(f"  - ID: {activity['id']}")
    print(f"  - Nom: {activity['name']}")
    print(f"  - Date: {activity['start_date_local']}")
    print(f"  - Type: {activity['sport_type']}")
    print(f"  - Distance: {activity['distance']/1000:.2f} km")
    print()

    # 3. Vérifier si l'activité a des streams GPS sur Strava
    print("3. Vérification des streams GPS sur Strava...")
    streams_url = f"https://www.strava.com/api/v3/activities/{activity['id']}/streams"
    params = {"keys": "latlng", "key_by_type": "true"}

    response = requests.get(streams_url, headers=headers, params=params)

    if response.status_code == 404:
        print("❌ Cette activité n'a PAS de données GPS sur Strava")
        print("   → L'activité a probablement été créée manuellement")
        print("   → Il n'y a rien à importer")
        return
    elif response.status_code != 200:
        print(f"❌ Erreur lors de la récupération des streams: {response.text}")
        return

    streams = response.json()
    if "latlng" in streams and streams["latlng"]["data"]:
        gps_points = len(streams["latlng"]["data"])
        print(f"✓ L'activité a {gps_points} points GPS sur Strava")
    else:
        print("❌ Pas de données GPS disponibles")
        return
    print()

    # 4. Vérifier si l'activité est dans Supabase
    print("4. Vérification dans Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Vérifier la table strava_activities
    try:
        result = supabase.table("strava_activities").select("*").eq(
            "strava_id", activity['id']
        ).execute()

        if result.data:
            print(f"✓ Activité présente dans strava_activities")
        else:
            print(f"❌ Activité NON présente dans strava_activities")
            print(f"   → Lancez strava_to_supabase.py pour l'importer")
    except Exception as e:
        print(f"❌ Erreur: {e}")

    # Vérifier la table strava_activity_streams
    try:
        result = supabase.table("strava_activity_streams").select(
            "stream_index", count="exact"
        ).eq("strava_id", activity['id']).execute()

        if result.count and result.count > 0:
            print(f"✓ {result.count} points GPS présents dans strava_activity_streams")
        else:
            print(f"❌ Aucun point GPS dans strava_activity_streams")
            print(f"   → Lancez strava_streams_to_supabase.py pour importer les traces")
    except Exception as e:
        print(f"❌ Erreur: {e}")

    print("\n✅ Diagnostic terminé")


if __name__ == "__main__":
    main()
