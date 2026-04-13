# CLAUDE.md — strava-backend

## Stack

- **Backend :** Python 3 + Flask (port 5003)
- **Base de données :** Supabase (PostgreSQL)
- **Package manager :** Poetry (`pyproject.toml` + `poetry.lock`)
- **Frontend :** HTML/JS statique dans `docs/` (accès direct au client Supabase JS)
- **Auth :** Supabase Auth (email/password + OAuth Strava)
- **Serveur prod :** Gunicorn

## Structure du projet

```
strava-backend/
├── app.py                        # Flask API (/api/*)
├── strava_sync.py                # Script de sync unifié (SEUL script de sync)
├── start.sh                      # Lance app.py via le venv
├── pyproject.toml                # Dépendances Poetry
├── poetry.lock                   # Lock file (committer)
├── requirements.txt              # Kept pour référence / compat pip
├── .env                          # Credentials (jamais committer)
│
├── docs/                         # Frontend statique (production)
│   ├── index.html                # Page de login
│   ├── dashboard.html            # Dashboard principal
│   ├── journal.html              # Journal d'activités
│   ├── settings.html             # Paramètres utilisateur
│   ├── gpx-creator.html          # Outil création GPX
│   └── auth.js                   # Helpers auth Supabase (partagé)
│
├── scripts/
│   ├── login.py                  # FastAPI — obtenir les tokens Strava (OAuth)
│   └── check_latest_activity.py  # Diagnostic : vérifie la dernière activité
│
└── table sql/
    ├── create_table.sql           # Schéma strava_activities
    ├── create_streams_table.sql   # Schéma strava_activity_streams
    └── migration_multi_user.sql   # Migration multi-user (RLS + user_id)
```

## Commandes principales

```bash
# Installer les dépendances
poetry install

# Activer le venv (Poetry 2.x — pas de `poetry shell`)
eval "$(poetry env activate)"

# Démarrer le serveur Flask
poetry run python3 app.py
# ou
./start.sh

# Synchronisation Strava → Supabase (script unique)
poetry run python3 strava_sync.py              # 7 derniers jours (défaut)
poetry run python3 strava_sync.py --days 30    # N derniers jours
poetry run python3 strava_sync.py --all        # Tout synchroniser

# Sync par type de données
poetry run python3 strava_sync.py activities   # Activités seulement
poetry run python3 strava_sync.py laps         # Laps seulement
poetry run python3 strava_sync.py streams      # Traces GPS (~40-60 min pour 2000 activités)

# Obtenir les tokens Strava (première configuration)
cd scripts && poetry run uvicorn login:app --reload --port 8001
# → ouvrir http://localhost:8001/login

# Diagnostic
poetry run python3 scripts/check_latest_activity.py
```

## Tables Supabase

| Table | Description |
|-------|-------------|
| `strava_activities` | Données des activités (distance, durée, FC, dénivelé…) |
| `strava_activity_streams` | Points GPS par activité (lat/lon, altitude, cadence…) |
| `strava_laps` | Données de laps/segments |
| `user_strava_tokens` | Tokens OAuth Strava par utilisateur |

## Routes API Flask

| Route | Description |
|-------|-------------|
| `GET /api/activities` | Toutes les activités de l'année (paginé) |
| `GET /api/activity/<id>` | Détail d'une activité |
| `GET /api/activity/<id>/streams` | Points GPS (paginé, 1000/page) |
| `GET /api/activity/<id>/laps` | Données de laps |
| `GET /api/stats` | Stats agrégées (total distance, dénivelé, temps) |

## Variables d'environnement (.env)

```
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=
SUPABASE_URL=
SUPABASE_KEY=          # anon/public key
SUPABASE_t_KEY=        # service role key (admin, backend only)
FLASK_DEBUG=false
```

## Architecture frontend

Le frontend (`docs/`) accède **directement** à Supabase via le client JS — il ne passe pas par Flask pour les données. Flask ne sert que les routes `/api/*` (stats agrégées).

- `auth.js` : initialise le client Supabase, gère login/logout et le flow OAuth Strava
- Les credentials Supabase (`SUPABASE_KEY` anon key) sont dans `auth.js` — c'est normal, cette clé est publique par conception
- Le `STRAVA_CLIENT_SECRET` et `SUPABASE_t_KEY` ne doivent **jamais** être dans le frontend

## Règles importantes

- **Ne jamais committer `.env`** — credentials réels
- **Ne jamais exposer `SUPABASE_t_KEY` (service role) côté frontend**
- **Les scripts sont idempotents** — upsert sur `strava_id`, safe à relancer
- **Rate limiting Strava :** 100 req/15 min, 1000 req/jour — `strava_sync.py` le respecte
- **Migrations SQL :** s'exécutent dans l'éditeur SQL Supabase (idempotentes avec `IF NOT EXISTS`)
- **`strava_sync.py` est le seul script de sync** — les anciens scripts individuels ont été supprimés

## Conventions

- Code et commentaires en français
- Pas de build/bundling — Python et HTML directs
- Frontend utilise Supabase JS client directement (pas de proxy Flask)
- Pas de mock en tests — les tests doivent toucher une vraie base
