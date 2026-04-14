"""
Import du fichier CSV d'entraînement vers Supabase.

- Rows avec lien Strava → training lié à strava_activity_id + commentaire
- Rows sans lien Strava mais avec sport → training avec sport_type, distance/temps, commentaire
- Colonne "Sensation Semaine" (col 3) → annotation agenda_events (type "day") sur la date
- Les doublons (même date + même clé) sont ignorés

Usage:
    poetry run python3 scripts/import_csv.py
    poetry run python3 scripts/import_csv.py --dry-run   # Affiche sans insérer
"""

import csv
import re
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_t_KEY")  # service role key

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "Training  - Programme complet.csv")
STRAVA_ATHLETE_ID = 6122795

DRY_RUN = "--dry-run" in sys.argv

MOIS = {
    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
}


def parse_date_fr(date_str):
    """'lundi 9 novembre 2020' → datetime"""
    parts = date_str.strip().split()
    if len(parts) < 4:
        return None
    try:
        day = int(parts[1])
        month = MOIS.get(parts[2].lower())
        year = int(parts[3])
        if not month:
            return None
        return datetime(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_strava_ids(strava_str):
    """Extrait les IDs d'activité depuis les URLs Strava"""
    return [int(m) for m in re.findall(r'strava\.com/activities/(\d+)', strava_str)]


def parse_distance_time(km_tps_str):
    """
    Parse '10 km' → (10.0, None)
    Parse '2h30' → (None, 150)
    Parse '3h' → (None, 180)
    Retourne (planned_distance_km, planned_time_min)
    """
    s = km_tps_str.strip()
    km_match = re.search(r'(\d+\.?\d*)\s*km', s, re.IGNORECASE)
    if km_match:
        return float(km_match.group(1)), None
    time_match = re.match(r'(\d+)h(\d*)', s, re.IGNORECASE)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2)) if time_match.group(2) else 0
        return None, hours * 60 + minutes
    return None, None


def load_existing(supabase, user_id):
    """Charge les trainings et annotations existants pour détecter les doublons"""
    print("🔍 Chargement des données existantes...")

    # Trainings existants : clé = (date, strava_activity_id) ou (date, sport_type)
    # clé → {"id": ..., "planned_distance": ..., "planned_time": ...}
    existing_trainings = {}
    page = 0
    while True:
        result = supabase.table("trainings") \
            .select("id,date,strava_activity_id,sport_type,planned_distance,planned_time") \
            .eq("user_id", user_id) \
            .range(page * 1000, (page + 1) * 1000 - 1) \
            .execute()
        if not result.data:
            break
        for t in result.data:
            key = (t["date"], t.get("strava_activity_id"), t.get("sport_type"))
            existing_trainings[key] = {
                "id": t["id"],
                "planned_distance": t.get("planned_distance"),
                "planned_time": t.get("planned_time"),
            }
        if len(result.data) < 1000:
            break
        page += 1

    # Annotations existantes : clé = (start_datetime[:10], title)
    existing_annotations = set()
    page = 0
    while True:
        result = supabase.table("agenda_events") \
            .select("start_datetime,title") \
            .eq("user_id", user_id) \
            .range(page * 1000, (page + 1) * 1000 - 1) \
            .execute()
        if not result.data:
            break
        for a in result.data:
            date_part = a["start_datetime"][:10]
            existing_annotations.add((date_part, a["title"]))
        if len(result.data) < 1000:
            break
        page += 1

    print(f"  {len(existing_trainings)} trainings existants")
    print(f"  {len(existing_annotations)} annotations existantes")
    return existing_trainings, existing_annotations


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Récupérer le user_id
    result = supabase.table("user_strava_tokens") \
        .select("user_id") \
        .eq("strava_athlete_id", STRAVA_ATHLETE_ID) \
        .single() \
        .execute()

    if not result.data:
        print(f"❌ Aucun utilisateur trouvé pour strava_athlete_id={STRAVA_ATHLETE_ID}")
        sys.exit(1)

    user_id = result.data["user_id"]
    print(f"✓ User ID: {user_id}")

    existing_trainings, existing_annotations = load_existing(supabase, user_id)

    # Lire le CSV
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    trainings = []
    trainings_to_update = []  # [{id, planned_distance, planned_time}]
    annotations = []
    skipped_date = 0
    skipped_dup = 0

    for i, row in enumerate(rows[1:], start=2):
        while len(row) < 9:
            row.append("")

        date_str = row[0].strip()
        if not date_str:
            skipped_date += 1
            continue

        date = parse_date_fr(date_str)
        if not date:
            print(f"  ⚠ Ligne {i}: date non parseable '{date_str}'")
            skipped_date += 1
            continue

        date_iso = date.strftime("%Y-%m-%d")
        sensation = row[3].strip()
        sport = row[4].strip()
        km_tps = row[6].strip()
        commentaire = row[7].strip()
        strava_str = row[8].strip()

        # Annotation "Sensation Semaine" → agenda_events
        if sensation:
            key = (date_iso, sensation)
            if key not in existing_annotations:
                annotations.append({
                    "user_id": user_id,
                    "event_type": "day",
                    "title": sensation,
                    "start_datetime": f"{date_iso}T00:00:00",
                    "end_datetime": f"{date_iso}T23:59:59",
                    "all_day": True
                })
                existing_annotations.add(key)
            else:
                skipped_dup += 1

        # Training avec lien Strava
        distance, time_min = parse_distance_time(km_tps) if km_tps else (None, None)
        strava_ids = parse_strava_ids(strava_str)
        if strava_ids:
            for strava_id in strava_ids:
                key = (date_iso, strava_id, None)
                existing = existing_trainings.get(key)
                if existing is None:
                    # Vérifier si un training existe déjà sur cette date sans strava_id (même sport)
                    existing_no_strava = existing_trainings.get((date_iso, None, sport)) if sport else None
                    if existing_no_strava and existing_no_strava["id"] is not None:
                        # Mettre à jour le training existant pour lier l'activité Strava
                        update = {
                            "id": existing_no_strava["id"],
                            "strava_activity_id": strava_id,
                            "sport_type": None,
                        }
                        if existing_no_strava["planned_distance"] is None and existing_no_strava["planned_time"] is None:
                            update["planned_distance"] = distance
                            update["planned_time"] = time_min
                        trainings_to_update.append(update)
                        # Remplacer la clé dans le dict
                        del existing_trainings[(date_iso, None, sport)]
                        existing_trainings[key] = {"id": existing_no_strava["id"], "planned_distance": distance, "planned_time": time_min}
                    else:
                        trainings.append({
                            "user_id": user_id,
                            "date": date_iso,
                            "title": commentaire or None,
                            "strava_activity_id": strava_id,
                            "sport_type": None,
                            "planned_distance": distance,
                            "planned_time": time_min
                        })
                        existing_trainings[key] = {"id": None, "planned_distance": distance, "planned_time": time_min}
                elif (distance is not None or time_min is not None) and \
                     existing["planned_distance"] is None and existing["planned_time"] is None:
                    trainings_to_update.append({
                        "id": existing["id"],
                        "planned_distance": distance,
                        "planned_time": time_min
                    })
                else:
                    skipped_dup += 1
            continue

        # Training sans lien Strava (données CSV)
        if sport:
            key = (date_iso, None, sport)
            existing = existing_trainings.get(key)
            if existing is None:
                trainings.append({
                    "user_id": user_id,
                    "date": date_iso,
                    "title": commentaire or None,
                    "strava_activity_id": None,
                    "sport_type": sport,
                    "planned_distance": distance,
                    "planned_time": time_min
                })
                existing_trainings[key] = {"id": None, "planned_distance": distance, "planned_time": time_min}
            elif (distance is not None or time_min is not None) and \
                 existing["planned_distance"] is None and existing["planned_time"] is None:
                trainings_to_update.append({
                    "id": existing["id"],
                    "planned_distance": distance,
                    "planned_time": time_min
                })
            else:
                skipped_dup += 1

    print(f"\n📊 Résumé:")
    print(f"  Trainings à insérer : {len(trainings)}")
    print(f"  Trainings à mettre à jour (km/temps manquants) : {len(trainings_to_update)}")
    print(f"  Annotations à insérer : {len(annotations)}")
    print(f"  Doublons ignorés : {skipped_dup}")
    print(f"  Lignes sans date : {skipped_date}")

    if DRY_RUN:
        print("\n🔍 Mode dry-run — rien n'est inséré.")
        print("\nExemples trainings:")
        for t in trainings[:5]:
            print(f"  {t}")
        print("\nExemples updates:")
        for t in trainings_to_update[:5]:
            print(f"  {t}")
        print("\nExemples annotations:")
        for a in annotations[:5]:
            print(f"  {a}")
        return

    # Insérer les trainings par batch
    errors = 0
    if trainings:
        print("\n📤 Insertion des trainings...")
        for i in range(0, len(trainings), 50):
            batch = trainings[i:i+50]
            try:
                supabase.table("trainings").insert(batch).execute()
                print(f"  ✓ Batch {i//50 + 1}: {len(batch)} trainings")
            except Exception as e:
                print(f"  ✗ Batch {i//50 + 1}: {e}")
                errors += 1

    # Mettre à jour les trainings avec km/temps manquants
    if trainings_to_update:
        print("\n✏️  Mise à jour des trainings existants...")
        updated = 0
        for t in trainings_to_update:
            if t["id"] is None:
                continue
            try:
                update_data = {}
                if "strava_activity_id" in t:
                    update_data["strava_activity_id"] = t["strava_activity_id"]
                    update_data["sport_type"] = t["sport_type"]
                if "planned_distance" in t:
                    update_data["planned_distance"] = t["planned_distance"]
                    update_data["planned_time"] = t["planned_time"]
                supabase.table("trainings").update(update_data).eq("id", t["id"]).execute()
                updated += 1
            except Exception as e:
                print(f"  ✗ Update id={t['id']}: {e}")
                errors += 1
        print(f"  ✓ {updated} trainings mis à jour")

    # Insérer les annotations par batch
    if annotations:
        print("\n📤 Insertion des annotations...")
        for i in range(0, len(annotations), 50):
            batch = annotations[i:i+50]
            try:
                supabase.table("agenda_events").insert(batch).execute()
                print(f"  ✓ Batch {i//50 + 1}: {len(batch)} annotations")
            except Exception as e:
                print(f"  ✗ Batch {i//50 + 1}: {e}")
                errors += 1

    print(f"\n{'✅' if errors == 0 else '⚠'} Import terminé — {errors} erreur(s)")


if __name__ == "__main__":
    main()
