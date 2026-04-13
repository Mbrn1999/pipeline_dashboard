# CLAUDE.md — strava-backend

## Stack

- **Scripts Python :** Python 3 (sync Strava → Supabase)
- **Base de données :** Supabase (PostgreSQL)
- **Package manager :** Poetry (`pyproject.toml` + `poetry.lock`)
- **Frontend :** HTML/JS statique dans `docs/` — hébergé sur domaine, accès direct Supabase JS + API Strava
- **Auth :** Supabase Auth (email/password + OAuth Strava)

> Pas de serveur backend — le frontend appelle directement Supabase et l'API Strava.

## Structure du projet

```
strava-backend/
├── strava_sync.py                # Script de sync unifié (SEUL script de sync)
├── pyproject.toml                # Dépendances Poetry
├── poetry.lock                   # Lock file (committer)
├── requirements.txt              # Compat pip (référence)
├── .env                          # Credentials (jamais committer)
│
├── docs/                         # Frontend statique (hébergé sur domaine)
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

# Activer le venv (Poetry 2.x)
eval "$(poetry env activate)"

# Synchronisation Strava → Supabase
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

## Variables d'environnement (.env)

```
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=
SUPABASE_URL=
SUPABASE_KEY=      # anon/public key
SUPABASE_t_KEY=    # service role key (scripts Python uniquement)
```

## Architecture

Le frontend (`docs/`) est hébergé statiquement (domaine) et communique directement avec :
- **Supabase JS** — lecture des données (activités, streams, laps)
- **API Strava** — accès direct depuis le navigateur (token OAuth stocké dans Supabase)

Les scripts Python servent uniquement à la **synchronisation** Strava → Supabase. Ils tournent en local ou en cron.

- `auth.js` : initialise le client Supabase, gère login/logout et le flow OAuth Strava
- La `SUPABASE_KEY` (anon key) dans `auth.js` est publique par conception — RLS protège les données
- `SUPABASE_t_KEY` (service role) et `STRAVA_CLIENT_SECRET` : scripts Python uniquement, jamais dans le frontend

## Règles importantes

- **Ne jamais committer `.env`** — credentials réels
- **Ne jamais exposer `SUPABASE_t_KEY` côté frontend**
- **Les scripts sont idempotents** — upsert sur `strava_id`, safe à relancer
- **Rate limiting Strava :** 100 req/15 min, 1000 req/jour — `strava_sync.py` le respecte
- **Migrations SQL :** s'exécutent dans l'éditeur SQL Supabase (idempotentes avec `IF NOT EXISTS`)

## Conventions

- Code et commentaires en français
- Pas de build/bundling — Python et HTML directs
- Pas de mock en tests — les tests doivent toucher une vraie base
