"""
Application Flask pour visualiser les activités Strava avec leurs traces GPS
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import time
from dotenv import load_dotenv
from supabase import create_client

# Charger les variables d'environnement
load_dotenv()

# DEBUG : Vérifier que les variables sont bien chargées
print("\n" + "="*50)
print("DEBUG - Variables d'environnement")
print("="*50)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY: {SUPABASE_KEY[:30]}..." if SUPABASE_KEY else "SUPABASE_KEY: None")
print("="*50 + "\n")

app = Flask(__name__)
CORS(app)

# Configuration Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/')
def index():
    """Page d'accueil avec la liste des activités"""
    print(f"\n>>> Route / appelée")
    print(f">>> Passage de supabase_url: {SUPABASE_URL}")
    print(f">>> Passage de supabase_key: {'Present' if SUPABASE_KEY else 'Missing'}\n")
    
    # Injecter les clés Supabase dans le template pour le JavaScript
    # cache_buster force le rechargement du JavaScript
    return render_template(
        'index.html',
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY,
        cache_buster=int(time.time())
    )


@app.route('/api/activities')
def get_activities():
    """Récupère toutes les activités de 2026"""
    try:
        response = supabase.table("strava_activities").select("*").gte(
            "start_date_local", "2026-01-01"
        ).lte(
            "start_date_local", "2026-12-31"
        ).order("start_date_local", desc=True).execute()

        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/activity/<int:strava_id>')
def get_activity(strava_id):
    """Récupère les détails d'une activité"""
    try:
        response = supabase.table("strava_activities").select("*").eq(
            "strava_id", strava_id
        ).execute()

        if response.data:
            return jsonify(response.data[0])
        else:
            return jsonify({"error": "Activity not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/activity/<int:strava_id>/streams')
def get_activity_streams(strava_id):
    """Récupère tous les streams GPS d'une activité (pagination pour dépasser la limite de 1000 lignes)"""
    try:
        all_data = []
        batch_size = 1000
        offset = 0

        while True:
            response = supabase.table("strava_activity_streams").select("*").eq(
                "strava_id", strava_id
            ).order("stream_index").range(offset, offset + batch_size - 1).execute()

            all_data.extend(response.data)

            if len(response.data) < batch_size:
                break
            offset += batch_size

        return jsonify(all_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Récupère les statistiques globales"""
    try:
        # Total activités 2026
        activities_response = supabase.table("strava_activities").select(
            "strava_id", count="exact"
        ).gte("start_date_local", "2026-01-01").lte(
            "start_date_local", "2026-12-31"
        ).execute()

        # Total distance
        distance_response = supabase.table("strava_activities").select(
            "distance"
        ).gte("start_date_local", "2026-01-01").lte(
            "start_date_local", "2026-12-31"
        ).execute()

        total_distance = sum(a['distance'] for a in distance_response.data if a['distance']) / 1000  # en km

        # Total dénivelé
        elevation_response = supabase.table("strava_activities").select(
            "total_elevation_gain"
        ).gte("start_date_local", "2026-01-01").lte(
            "start_date_local", "2026-12-31"
        ).execute()

        total_elevation = sum(a['total_elevation_gain'] for a in elevation_response.data if a['total_elevation_gain'])

        # Temps total
        time_response = supabase.table("strava_activities").select(
            "moving_time"
        ).gte("start_date_local", "2026-01-01").lte(
            "start_date_local", "2026-12-31"
        ).execute()

        total_time = sum(a['moving_time'] for a in time_response.data if a['moving_time']) / 3600  # en heures

        return jsonify({
            "total_activities": activities_response.count,
            "total_distance_km": round(total_distance, 2),
            "total_elevation_m": round(total_elevation, 2),
            "total_time_hours": round(total_time, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("\n=== Application Strava Viewer ===")
    print("Ouvrez votre navigateur sur : http://localhost:5003")
    print("Appuyez sur Ctrl+C pour arrêter le serveur\n")
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", port=5003)