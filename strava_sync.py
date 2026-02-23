"""
Script unifié pour synchroniser les données Strava vers Supabase :
- Activités
- Tours (laps)
- Traces GPS (streams)

Usage:
    python strava_sync.py                    # Sync tout (7 derniers jours)
    python strava_sync.py activities         # Sync uniquement les activités
    python strava_sync.py laps              # Sync uniquement les tours
    python strava_sync.py streams           # Sync uniquement les traces GPS
    python strava_sync.py --days 30         # Sync les 30 derniers jours
    python strava_sync.py --all             # Sync toutes les activités (sans filtre date)
    python strava_sync.py laps --days 14    # Sync les tours des 14 derniers jours
"""
import os
import sys
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Charger les variables d'environnement
load_dotenv()

# Configuration Strava
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DEFAULT_DAYS = 7


# ============================================================
# Fonctions partagées
# ============================================================

def check_env():
    """Vérifie que toutes les variables d'environnement sont présentes"""
    if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
        print("❌ Erreur: Variables Strava manquantes dans .env")
        print("   Vérifiez: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN")
        return False
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Erreur: Variables Supabase manquantes dans .env")
        print("   Vérifiez: SUPABASE_URL, SUPABASE_KEY")
        return False
    return True


def get_access_token():
    """Récupère un nouveau access_token en utilisant le refresh_token"""
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Erreur lors de la récupération du token: {response.text}")
        return None


def get_strava_activities(access_token, days=None):
    """
    Récupère les activités Strava.
    Si days est spécifié, filtre les N derniers jours. Sinon récupère tout.
    """
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    all_activities = []
    page = 1
    per_page = 200

    params_base = {"per_page": per_page}
    if days is not None:
        after_date = datetime.now() - timedelta(days=days)
        params_base["after"] = int(after_date.timestamp())

    while True:
        params = {**params_base, "page": page}
        response = requests.get(activities_url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Erreur lors de la récupération des activités: {response.text}")
            break

        activities = response.json()
        if not activities:
            break

        all_activities.extend(activities)
        print(f"   Page {page}: {len(activities)} activités récupérées")
        page += 1

    label = f"des {days} derniers jours" if days else "totales"
    print(f"   Total: {len(all_activities)} activités {label}")
    return all_activities


# ============================================================
# Sync des activités
# ============================================================

def format_activity(activity):
    """Formate une activité Strava pour l'insertion dans Supabase"""
    return {
        "strava_id": activity["id"],
        "name": activity["name"],
        "sport_type": activity.get("sport_type", activity.get("type")),
        "distance": activity["distance"],
        "moving_time": activity["moving_time"],
        "elapsed_time": activity["elapsed_time"],
        "total_elevation_gain": activity["total_elevation_gain"],
        "start_date": activity["start_date"],
        "start_date_local": activity["start_date_local"],
        "average_speed": activity.get("average_speed"),
        "max_speed": activity.get("max_speed"),
        "average_heartrate": activity.get("average_heartrate"),
        "max_heartrate": activity.get("max_heartrate"),
        "elev_high": activity.get("elev_high"),
        "elev_low": activity.get("elev_low"),
        "kudos_count": activity.get("kudos_count", 0),
        "achievement_count": activity.get("achievement_count", 0),
    }


def sync_activities(access_token, days=None):
    """Récupère les activités et les envoie dans Supabase"""
    print("\n" + "=" * 50)
    label = f" ({days} derniers jours)" if days else " (tout)"
    print(f"SYNC ACTIVITÉS{label}")
    print("=" * 50)

    print("\nRécupération des activités Strava...")
    activities = get_strava_activities(access_token, days=days)
    if not activities:
        print("   Aucune activité trouvée")
        return []

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    success_count = 0
    error_count = 0

    print(f"\nEnvoi de {len(activities)} activités vers Supabase...")
    for activity in activities:
        try:
            formatted = format_activity(activity)
            supabase.table("strava_activities").upsert(
                formatted, on_conflict="strava_id"
            ).execute()
            success_count += 1
            print(f"   ✓ '{activity['name']}' ({activity['start_date_local']})")
        except Exception as e:
            error_count += 1
            print(f"   ✗ Erreur pour {activity['id']}: {e}")

    print(f"\n--- Résumé activités ---")
    print(f"Succès: {success_count} | Erreurs: {error_count} | Total: {len(activities)}")
    return activities


# ============================================================
# Sync des tours (laps)
# ============================================================

def get_activity_laps(activity_id, access_token):
    """Récupère tous les tours (laps) d'une activité Strava"""
    try:
        response = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}/laps",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return []
        else:
            print(f"   ❌ Erreur {response.status_code} pour activité {activity_id}")
            return []
    except Exception as e:
        print(f"   ❌ Exception pour activité {activity_id}: {e}")
        return []


def format_lap(lap, activity_strava_id):
    """Formate un tour Strava pour l'insertion dans Supabase"""
    return {
        "lap_id": lap["id"],
        "activity_id": activity_strava_id,
        "name": lap.get("name", ""),
        "lap_index": lap.get("lap_index", 0),
        "distance": lap.get("distance", 0.0),
        "moving_time": lap.get("moving_time", 0),
        "elapsed_time": lap.get("elapsed_time", 0),
        "total_elevation_gain": lap.get("total_elevation_gain", 0.0),
        "start_date": lap.get("start_date"),
        "start_date_local": lap.get("start_date_local"),
        "average_speed": lap.get("average_speed"),
        "max_speed": lap.get("max_speed"),
        "average_heartrate": lap.get("average_heartrate"),
        "max_heartrate": lap.get("max_heartrate"),
        "average_cadence": lap.get("average_cadence"),
        "pace_zone": lap.get("pace_zone"),
        "start_index": lap.get("start_index"),
        "end_index": lap.get("end_index"),
    }


def sync_laps(access_token, days=None):
    """Récupère les laps des activités et les envoie dans Supabase"""
    print("\n" + "=" * 50)
    label = f" ({days} derniers jours)" if days else " (tout)"
    print(f"SYNC TOURS (LAPS){label}")
    print("=" * 50)

    print(f"\nRécupération des activités...")
    activities = get_strava_activities(access_token, days=days)
    if not activities:
        print(f"   Aucune activité trouvée")
        return

    print(f"\nRécupération des tours pour {len(activities)} activités...")
    all_laps = []

    for i, activity in enumerate(activities, 1):
        activity_id = activity["id"]
        print(f"\n[{i}/{len(activities)}] '{activity['name']}' ({activity['start_date_local']})")

        laps = get_activity_laps(activity_id, access_token)
        if laps:
            for lap in laps:
                all_laps.append(format_lap(lap, activity_id))
            print(f"   📍 {len(laps)} tour(s) récupéré(s)")
        else:
            print(f"   ℹ️  Aucun tour")

    if not all_laps:
        print("\n⚠️  Aucun tour à envoyer")
        return

    print(f"\nEnvoi de {len(all_laps)} tours vers Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    success_count = 0
    error_count = 0

    for lap_data in all_laps:
        try:
            supabase.table("strava_laps").upsert(
                lap_data, on_conflict="lap_id"
            ).execute()
            success_count += 1
            distance_km = lap_data["distance"] / 1000
            print(f"   ✓ Tour {lap_data['lap_index']} activité {lap_data['activity_id']} ({distance_km:.2f} km)")
        except Exception as e:
            error_count += 1
            print(f"   ✗ Erreur tour {lap_data.get('lap_id')}: {e}")

    print(f"\n--- Résumé tours ---")
    print(f"Succès: {success_count} | Erreurs: {error_count} | Total: {len(all_laps)}")


# ============================================================
# Sync des streams (traces GPS)
# ============================================================

def get_activity_streams(activity_id, access_token):
    """Récupère les streams (données GPS) d'une activité"""
    stream_types = [
        "latlng", "altitude", "time", "distance", "heartrate",
        "velocity_smooth", "grade_smooth", "cadence", "watts", "temp"
    ]
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"keys": ",".join(stream_types), "key_by_type": "true"}
    )
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        print(f"   Erreur {response.status_code} pour activité {activity_id}: {response.text}")
        return None


def format_streams(activity_id, streams_data):
    """Formate les streams pour l'insertion dans Supabase"""
    if not streams_data or "latlng" not in streams_data:
        return []

    latlng_data = streams_data.get("latlng", {}).get("data", [])
    if not latlng_data:
        return []

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


def sync_streams(access_token, days=None):
    """Récupère les streams GPS des activités et les envoie dans Supabase"""
    print("\n" + "=" * 50)
    label = f" ({days} derniers jours)" if days else " (tout)"
    print(f"SYNC TRACES GPS (STREAMS){label}")
    print("=" * 50)

    print(f"\nRécupération des activités...")
    activities = get_strava_activities(access_token, days=days)
    if not activities:
        print(f"   Aucune activité trouvée")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"\nRécupération et envoi des traces GPS pour {len(activities)} activités...\n")

    total_points = 0
    total_with_streams = 0
    total_without_streams = 0
    total_errors = 0

    for idx, activity in enumerate(activities, 1):
        activity_id = activity["id"]
        print(f"[{idx}/{len(activities)}] '{activity['name']}' ({activity['start_date_local']})")

        streams_data = get_activity_streams(activity_id, access_token)

        if streams_data is None:
            print(f"   → Pas de trace GPS disponible")
            total_without_streams += 1
        else:
            streams_points = format_streams(activity_id, streams_data)
            if not streams_points:
                print(f"   → Pas de données GPS")
                total_without_streams += 1
            else:
                success = 0
                errors = 0
                batch_size = 1000
                for i in range(0, len(streams_points), batch_size):
                    batch = streams_points[i:i + batch_size]
                    try:
                        supabase.table("strava_activity_streams").upsert(
                            batch, on_conflict="strava_id,stream_index"
                        ).execute()
                        success += len(batch)
                    except Exception as e:
                        errors += len(batch)
                        print(f"   ✗ Erreur batch pour activité {activity_id}: {e}")

                if errors > 0:
                    print(f"   ✓ {success} points envoyés, {errors} erreurs")
                    total_errors += errors
                else:
                    print(f"   ✓ {success} points GPS envoyés")

                total_points += success
                total_with_streams += 1

        # Pause toutes les 50 activités pour respecter les limites API
        if idx % 50 == 0:
            print("\n   ⏸ Pause de 10 secondes (limites API)...\n")
            time.sleep(10)

    print(f"\n--- Résumé streams ---")
    print(f"Activités traitées: {len(activities)}")
    print(f"Avec traces GPS: {total_with_streams}")
    print(f"Sans traces GPS: {total_without_streams}")
    print(f"Points GPS envoyés: {total_points:,}")
    print(f"Erreurs: {total_errors}")


# ============================================================
# Main
# ============================================================

def parse_args():
    """Parse les arguments de la ligne de commande"""
    args = sys.argv[1:]
    valid_commands = {"activities", "laps", "streams"}

    commands = []
    days = DEFAULT_DAYS
    sync_all = False

    i = 0
    while i < len(args):
        if args[i] == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
            i += 2
        elif args[i] == "--all":
            sync_all = True
            i += 1
        elif args[i] in valid_commands:
            commands.append(args[i])
            i += 1
        else:
            print(f"Argument inconnu: {args[i]}")
            print(f"Usage: python strava_sync.py [activities] [laps] [streams] [--days N] [--all]")
            return None, None

    if not commands:
        commands = ["activities", "laps", "streams"]

    return commands, None if sync_all else days


def main():
    print("=== Strava → Supabase - Script unifié ===\n")

    if not check_env():
        return

    result = parse_args()
    if result[0] is None:
        return
    commands, days = result

    if days is not None:
        print(f"Période: {days} derniers jours")
    else:
        print("Période: toutes les activités")

    print("\n1. Récupération de l'access token...")
    access_token = get_access_token()
    if not access_token:
        return
    print("   ✓ Access token obtenu\n")

    if "activities" in commands:
        sync_activities(access_token, days=days)
    if "laps" in commands:
        sync_laps(access_token, days=days)
    if "streams" in commands:
        sync_streams(access_token, days=days)

    print("\n✅ Synchronisation terminée!")


if __name__ == "__main__":
    main()
