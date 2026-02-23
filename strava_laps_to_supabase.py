"""
Script pour récupérer les TOURS (laps) de toutes les activités Strava 2026
et les envoyer dans Supabase
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


def get_strava_activities_2026(access_token):
    """
    Récupère toutes les activités Strava de 2026
    """
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Dates pour filtrer 2026
    after_timestamp = int(datetime(2026, 1, 1).timestamp())
    before_timestamp = int(datetime(2027, 1, 1).timestamp())

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
        print(f"Page {page}: {len(activities)} activités 2026 récupérées")
        page += 1

    print(f"Total: {len(all_activities)} activités 2026 récupérées")
    return all_activities


def get_activity_laps(activity_id, access_token):
    """
    Récupère tous les tours (laps) d'une activité Strava
    
    Args:
        activity_id: ID Strava de l'activité
        access_token: Token d'authentification Strava
    
    Returns:
        Liste des tours de l'activité
    """
    laps_url = f"https://www.strava.com/api/v3/activities/{activity_id}/laps"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(laps_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            laps = response.json()
            print(f"   📍 {len(laps)} tour(s) récupéré(s) pour activité {activity_id}")
            return laps
        elif response.status_code == 404:
            print(f"   ⚠️  Activité {activity_id} non trouvée (404)")
            return []
        else:
            print(f"   ❌ Erreur {response.status_code} pour activité {activity_id}")
            return []
    
    except Exception as e:
        print(f"   ❌ Exception pour activité {activity_id}: {e}")
        return []


def format_lap(lap, activity_strava_id):
    """
    Formate un tour Strava pour l'insertion dans Supabase
    
    Args:
        lap: Données brutes du tour depuis l'API Strava
        activity_strava_id: ID Strava de l'activité parente
    
    Returns:
        Dict formaté pour Supabase
    """
    return {
        "lap_id": lap["id"],  # ID unique du tour
        "activity_id": activity_strava_id,  # Clé étrangère vers strava_activities
        "name": lap.get("name", ""),
        "lap_index": lap.get("lap_index", 0),  # Numéro du tour (1, 2, 3...)
        "distance": lap.get("distance", 0.0),  # Distance du tour en mètres
        "moving_time": lap.get("moving_time", 0),  # Temps en mouvement (secondes)
        "elapsed_time": lap.get("elapsed_time", 0),  # Temps écoulé (secondes)
        "total_elevation_gain": lap.get("total_elevation_gain", 0.0),  # Dénivelé (m)
        "start_date": lap.get("start_date"),
        "start_date_local": lap.get("start_date_local"),
        "average_speed": lap.get("average_speed"),  # Vitesse moyenne (m/s)
        "max_speed": lap.get("max_speed"),  # Vitesse max (m/s)
        "average_heartrate": lap.get("average_heartrate"),  # BPM moyen
        "max_heartrate": lap.get("max_heartrate"),  # BPM max
        "average_cadence": lap.get("average_cadence"),  # Cadence moyenne
        "pace_zone": lap.get("pace_zone"),  # Zone d'allure
        "start_index": lap.get("start_index"),  # Index de début dans les streams
        "end_index": lap.get("end_index"),  # Index de fin dans les streams
    }


def send_laps_to_supabase(all_laps):
    """
    Envoie tous les tours dans Supabase
    
    Args:
        all_laps: Liste de tous les tours formatés
    """
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    success_count = 0
    error_count = 0

    for lap_data in all_laps:
        try:
            # Utilise upsert pour éviter les doublons (basé sur lap_id)
            response = supabase.table("strava_laps").upsert(
                lap_data,
                on_conflict="lap_id"
            ).execute()

            success_count += 1
            activity_id = lap_data["activity_id"]
            lap_index = lap_data["lap_index"]
            distance = lap_data["distance"] / 1000  # Conversion en km
            print(f"   ✓ Tour {lap_index} de l'activité {activity_id} ({distance:.2f} km) envoyé")

        except Exception as e:
            error_count += 1
            print(f"   ✗ Erreur pour le tour {lap_data.get('lap_id')}: {e}")

    print(f"\n--- Résumé des tours ---")
    print(f"Succès: {success_count}")
    print(f"Erreurs: {error_count}")
    print(f"Total: {len(all_laps)}")


def main():
    """
    Fonction principale : récupère tous les tours de toutes les activités 2026
    """
    print("=== Script Strava LAPS 2026 → Supabase ===\n")

    # Vérifier les variables d'environnement
    if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
        print("❌ Erreur: Variables Strava manquantes dans .env")
        return

    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Erreur: Variables Supabase manquantes dans .env")
        return

    # 1. Récupérer l'access token
    print("1. Récupération de l'access token...")
    access_token = get_access_token()
    if not access_token:
        return
    print("   ✓ Access token obtenu\n")

    # 2. Récupérer toutes les activités 2026
    print("2. Récupération des activités 2026...")
    activities = get_strava_activities_2026(access_token)
    if not activities:
        print("   Aucune activité 2026 trouvée")
        return
    print(f"   ✓ {len(activities)} activités 2026 récupérées\n")

    # 3. Récupérer les tours de chaque activité
    print("3. Récupération des tours (laps) pour chaque activité...")
    all_laps = []
    
    for i, activity in enumerate(activities, 1):
        activity_id = activity["id"]
        activity_name = activity["name"]
        activity_date = activity["start_date_local"]
        
        print(f"\n[{i}/{len(activities)}] '{activity_name}' ({activity_date})")
        
        # Récupérer les tours de cette activité
        laps = get_activity_laps(activity_id, access_token)
        
        if laps:
            # Formater chaque tour
            for lap in laps:
                formatted_lap = format_lap(lap, activity_id)
                all_laps.append(formatted_lap)
        else:
            print(f"   ℹ️  Aucun tour pour cette activité")

    print(f"\n✅ Total de tours récupérés : {len(all_laps)}")

    if not all_laps:
        print("\n⚠️  Aucun tour à envoyer dans Supabase")
        return

    # 4. Envoyer tous les tours dans Supabase
    print("\n4. Envoi des tours vers Supabase...")
    send_laps_to_supabase(all_laps)

    print("\n✅ Script terminé!")


if __name__ == "__main__":
    main()