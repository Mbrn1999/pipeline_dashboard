# strava-backend

Scripts Python pour synchroniser les activités Strava dans Supabase.  
Le frontend (`docs/`) est hébergé séparément sur un domaine et accède directement à Supabase et à l'API Strava.

## Stack

- **Scripts :** Python 3 (sync Strava → Supabase)
- **Base de données :** Supabase (PostgreSQL)
- **Package manager :** Poetry
- **Frontend :** HTML/JS statique dans `docs/` — hébergé sur domaine

## Installation

### 1. Dépendances Python

```bash
pip install poetry
poetry install
```

### 2. Variables d'environnement

Créez un fichier `.env` à la racine :

```env
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=

SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_KEY=votre_anon_key
SUPABASE_t_KEY=votre_service_role_key
```

### 3. Obtenir les credentials Strava

1. Créez une app sur [strava.com/settings/api](https://www.strava.com/settings/api)
2. Notez `Client ID` et `Client Secret`
3. Lancez le helper OAuth pour obtenir le `refresh_token` :

```bash
cd scripts
poetry run uvicorn login:app --reload --port 8001
```

Ouvrez [http://localhost:8001/login](http://localhost:8001/login), autorisez l'app Strava, récupérez le `refresh_token` dans la réponse JSON.

### 4. Créer les tables Supabase

Dans l'éditeur SQL de votre projet Supabase, exécutez dans l'ordre :

1. `table sql/create_table.sql` — table `strava_activities`
2. `table sql/create_streams_table.sql` — table `strava_activity_streams`
3. *(optionnel)* `table sql/migration_multi_user.sql` — support multi-utilisateurs (RLS)

## Synchronisation Strava → Supabase

```bash
# 7 derniers jours (défaut)
poetry run python3 strava_sync.py

# N derniers jours
poetry run python3 strava_sync.py --days 30

# Tout synchroniser
poetry run python3 strava_sync.py --all

# Par type de données
poetry run python3 strava_sync.py activities   # Activités seulement
poetry run python3 strava_sync.py laps         # Laps seulement
poetry run python3 strava_sync.py streams      # Traces GPS (~40-60 min pour 2000 activités)
```

Les scripts sont idempotents — safe à relancer, pas de doublons (upsert sur `strava_id`).

### Synchronisation automatique (cron)

```bash
# Sync quotidienne à 7h
0 7 * * * cd /chemin/vers/strava-backend && poetry run python3 strava_sync.py
```

## Données synchronisées

### strava_activities

`strava_id`, `name`, `sport_type`, `distance`, `moving_time`, `elapsed_time`, `total_elevation_gain`, `start_date`, `start_date_local`, `average_speed`, `max_speed`, `average_heartrate`, `max_heartrate`, `elev_high`, `elev_low`, `kudos_count`, `achievement_count`

### strava_activity_streams (GPS)

`latitude`, `longitude`, `altitude`, `time`, `distance`, `heartrate`, `velocity_smooth`, `grade_smooth`, `cadence`, `watts`, `temp`

## Diagnostic

```bash
poetry run python3 scripts/check_latest_activity.py
```

Vérifie que la dernière activité Strava est bien présente dans Supabase (activités + streams).

## Limitations API Strava

- 100 requêtes / 15 min
- 1000 requêtes / jour

`strava_sync.py` respecte automatiquement ces limites.

## Dépannage

**Variables manquantes** → vérifiez `.env`, pas d'espaces autour du `=`

**Token invalide** → relancez le flow OAuth via `scripts/login.py`

**Table inexistante** → exécutez les scripts SQL dans l'ordre indiqué ci-dessus

**Upsert échoue** → vérifiez la contrainte unique sur `strava_id` dans la table
