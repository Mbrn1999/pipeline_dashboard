# CLAUDE.md — strava-backend

## Stack

- **Backend :** Python 3 + Flask (port 5003)
- **Base de données :** Supabase (PostgreSQL)
- **Package manager :** `pip` (virtualenv dans `venv/`)
- **Frontend :** HTML/JS statique dans `docs/`
- **Serveur prod :** Gunicorn

## Commandes principales

```bash
# Démarrer le serveur Flask
python app.py
# ou
./start.sh

# Synchronisation Strava → Supabase
python strava_sync.py              # 7 derniers jours
python strava_sync.py --days 30    # N derniers jours
python strava_sync.py --all        # Tout synchroniser
python strava_sync.py activities   # Activités seulement
python strava_sync.py laps         # Laps seulement
python strava_sync.py streams      # Traces GPS seulement

# Diagnostic
python scripts/check_latest_activity.py
```

## Architecture

```
app.py                        # Flask API + routes
strava_sync.py                # Script de sync unifié (principal)
strava_to_supabase.py         # Sync activités
strava_streams_to_supabase.py # Sync traces GPS (lent : ~40-60 min pour 2000 activités)
strava_laps_to_supabase.py    # Sync laps
docs/                         # Frontend HTML/JS
  auth.js                     # Helpers Supabase auth (partagé)
  dashboard.html              # Dashboard activités
  map.html                    # Visualisation carte
  journal.html                # Journal d'activités
table sql/                    # Scripts SQL Supabase
  create_table.sql
  create_streams_table.sql
  migration_multi_user.sql
scripts/
  login.py                    # FastAPI helper pour obtenir les tokens Strava
```

## Tables Supabase

- `strava_activities` — données des activités (distance, durée, FC, etc.)
- `strava_activity_streams` — points GPS par activité (index, lat/lon, altitude, etc.)
- `strava_laps` — données de laps/segments
- `user_strava_tokens` — tokens OAuth par utilisateur (multi-user)

## Variables d'environnement (.env)

```
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_t_KEY=      # service role key (admin)
FLASK_DEBUG=false
```

## Routes API Flask

| Route | Description |
|-------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/activities` | Toutes les activités de l'année |
| `GET /api/activity/<id>` | Détail d'une activité |
| `GET /api/activity/<id>/streams` | Points GPS (paginé, 1000/page) |
| `GET /api/activity/<id>/laps` | Données de laps |
| `GET /api/stats` | Stats agrégées (total distance, dénivelé, temps) |

## Règles importantes

- **Ne jamais committer `.env`** — il contient des credentials réels
- **Les scripts sont idempotents** — upsert sur `strava_id`, safe à relancer
- **Rate limiting Strava :** 100 req/15min, 1000 req/jour — les scripts le respectent
- **Migrations SQL :** s'exécutent directement dans l'éditeur SQL Supabase (idempotentes avec `IF NOT EXISTS`)
- **Multi-user :** migration disponible dans `table sql/migration_multi_user.sql`

## Conventions

- Code et commentaires en français
- Pas de build/bundling — Python et HTML directs
- Frontend utilise Supabase JS client directement pour les requêtes
- Flask injecte les credentials Supabase dans les templates HTML
