"""
Script pour récupérer les traces GPX (streams) de toutes les activités Strava
et les envoyer dans Supabase
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
import time

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


def get_all_strava_activities(access_token, year=2026):
    """
    Récupère toutes les activités Strava de l'utilisateur pour une année donnée
    """
    import datetime

    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Calculer les timestamps pour l'année demandée
    start_date = datetime.datetime(year, 1, 1, 0, 0, 0)
    end_date = datetime.datetime(year, 12, 31, 23, 59, 59)

    after_timestamp = int(start_date.timestamp())
    before_timestamp = int(end_date.timestamp())

    all_activities = []
    page = 1
    per_page = 200

    while True:
        params = {
            "page": page,
            "per_page": per_page,
            "after": after_timestamp,
            "before": before_timestamp
        }

        response = requests.get(activities_url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Erreur lors de la récupération des activités: {response.text}")
            break

        activities = response.json()

        if not activities:
            break

        all_activities.extend(activities)
        print(f"Page {page}: {len(activities)} activités récupérées")
        page += 1

    print(f"Total: {len(all_activities)} activités de {year} récupérées")
    return all_activities


def get_activity_streams(activity_id, access_token):
    """
    Récupère les streams (données GPS) d'une activité spécifique
    """
    streams_url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Types de streams à récupérer
    stream_types = [
        "latlng",      # Coordonnées latitude/longitude
        "altitude",    # Altitude
        "time",        # Temps relatif en secondes
        "distance",    # Distance cumulée
        "heartrate",   # Fréquence cardiaque
        "velocity_smooth",  # Vitesse lissée
        "grade_smooth",     # Pente lissée
        "cadence",     # Cadence
        "watts",       # Puissance
        "temp"         # Température
    ]

    params = {
        "keys": ",".join(stream_types),
        "key_by_type": "true"
    }

    response = requests.get(streams_url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        # Certaines activités n'ont pas de streams (ex: activités manuelles)
        return None
    else:
        print(f"Erreur {response.status_code} pour l'activité {activity_id}: {response.text}")
        return None


def format_streams(activity_id, streams_data):
    """
    Formate les streams pour l'insertion dans Supabase
    Retourne une liste de points
    """
    if not streams_data or "latlng" not in streams_data:
        return []

    latlng_data = streams_data.get("latlng", {}).get("data", [])
    if not latlng_data:
        return []

    # Récupérer tous les autres streams
    altitude_data = streams_data.get("altitude", {}).get("data", [])
    time_data = streams_data.get("time", {}).get("data", [])
    distance_data = streams_data.get("distance", {}).get("data", [])
    heartrate_data = streams_data.get("heartrate", {}).get("data", [])
    velocity_data = streams_data.get("velocity_smooth", {}).get("data", [])
    grade_data = streams_data.get("grade_smooth", {}).get("data", [])
    cadence_data = streams_data.get("cadence", {}).get("data", [])
    watts_data = streams_data.get("watts", {}).get("data", [])
    temp_data = streams_data.get("temp", {}).get("data", [])

    formatted_points = []

    for i, latlng in enumerate(latlng_data):
        point = {
            "strava_id": activity_id,
            "stream_index": i,
            "latitude": latlng[0] if latlng else None,
            "longitude": latlng[1] if latlng else None,
            "altitude": altitude_data[i] if i < len(altitude_data) else None,
            "time": time_data[i] if i < len(time_data) else None,
            "distance": distance_data[i] if i < len(distance_data) else None,
            "heartrate": heartrate_data[i] if i < len(heartrate_data) else None,
            "velocity_smooth": velocity_data[i] if i < len(velocity_data) else None,
            "grade_smooth": grade_data[i] if i < len(grade_data) else None,
            "cadence": cadence_data[i] if i < len(cadence_data) else None,
            "watts": watts_data[i] if i < len(watts_data) else None,
            "temp": temp_data[i] if i < len(temp_data) else None,
        }
        formatted_points.append(point)

    return formatted_points


def send_streams_to_supabase(activity_id, activity_name, streams_points, supabase):
    """
    Envoie les points de trace d'une activité dans Supabase
    """
    if not streams_points:
        return 0, 0

    success_count = 0
    error_count = 0

    # Envoyer par lots de 1000 points (limite Supabase)
    batch_size = 1000

    for i in range(0, len(streams_points), batch_size):
        batch = streams_points[i:i + batch_size]

        try:
            response = supabase.table("strava_activity_streams").upsert(
                batch,
                on_conflict="strava_id,stream_index"
            ).execute()

            success_count += len(batch)

        except Exception as e:
            error_count += len(batch)
            print(f"  ✗ Erreur batch {i//batch_size + 1} pour activité {activity_id}: {e}")

    return success_count, error_count


def main():
    """
    Fonction principale
    """
    print("=== Script Strava Streams (GPX) → Supabase (2026 uniquement) ===\n")

    # Vérifier les variables d'environnement
    if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
        print("❌ Erreur: Variables Strava manquantes dans .env")
        return

    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Erreur: Variables Supabase manquantes dans .env")
        return

    # 1. Récupérer un access_token
    print("1. Récupération de l'access token...")
    access_token = get_access_token()
    if not access_token:
        return
    print("   ✓ Access token obtenu\n")

    # 2. Récupérer toutes les activités de 2026
    print("2. Récupération des activités Strava de 2026...")
    activities = get_all_strava_activities(access_token, year=2026)
    if not activities:
        print("   Aucune activité trouvée en 2026")
        return
    print(f"   ✓ {len(activities)} activités de 2026 récupérées\n")

    # 3. Créer le client Supabase
    print("3. Connexion à Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("   ✓ Connecté à Supabase\n")

    # 4. Récupérer et envoyer les streams pour chaque activité
    print(f"4. Récupération et envoi des traces GPX...")
    print(f"   (Cela peut prendre du temps pour {len(activities)} activités)\n")

    total_points = 0
    total_activities_with_streams = 0
    total_activities_without_streams = 0
    total_errors = 0

    for idx, activity in enumerate(activities, 1):
        activity_id = activity["id"]
        activity_name = activity["name"]
        activity_date = activity["start_date_local"]

        print(f"[{idx}/{len(activities)}] '{activity_name}' ({activity_date})")

        # Récupérer les streams
        streams_data = get_activity_streams(activity_id, access_token)

        if streams_data is None:
            print(f"  → Pas de trace GPS disponible")
            total_activities_without_streams += 1
        else:
            # Formater les streams
            streams_points = format_streams(activity_id, streams_data)

            if not streams_points:
                print(f"  → Pas de données GPS")
                total_activities_without_streams += 1
            else:
                # Envoyer à Supabase
                success, errors = send_streams_to_supabase(
                    activity_id, activity_name, streams_points, supabase
                )

                if errors > 0:
                    print(f"  ✓ {success} points envoyés, {errors} erreurs")
                    total_errors += errors
                else:
                    print(f"  ✓ {success} points GPS envoyés")

                total_points += success
                total_activities_with_streams += 1

        # Pause pour respecter les limites de l'API Strava
        # (100 requêtes toutes les 15 minutes, 1000 par jour)
        if idx % 50 == 0:
            print("\n  ⏸ Pause de 10 secondes pour respecter les limites API...\n")
            time.sleep(10)

    print("\n--- Résumé ---")
    print(f"Activités traitées: {len(activities)}")
    print(f"Activités avec traces GPS: {total_activities_with_streams}")
    print(f"Activités sans traces GPS: {total_activities_without_streams}")
    print(f"Points GPS envoyés: {total_points:,}")
    print(f"Erreurs: {total_errors}")

    print("\n✅ Script terminé!")


if __name__ == "__main__":
    main()