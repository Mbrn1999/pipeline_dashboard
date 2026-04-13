# strava-backend

Synchronise vos activités Strava dans une base Supabase et expose un dashboard personnel.

## Stack

- **Backend :** Python 3 + Flask (port 5003)
- **Base de données :** Supabase (PostgreSQL)
- **Frontend :** HTML/JS statique dans `docs/`
- **Auth :** Supabase Auth (email/password + OAuth Strava)
- **Package manager :** Poetry

## Installation

### 1. Dépendances Python

```bash
# Installer Poetry si besoin
pip install poetry

# Installer les dépendances du projet
poetry install

# Activer l'environnement (Poetry 2.x)
eval "$(poetry env activate)"
# ou lancer directement sans activer
poetry run python3 app.py
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
FLASK_DEBUG=false
```

### 3. Obtenir les credentials Strava

1. Créez une app sur [strava.com/settings/api](https://www.strava.com/settings/api)
2. Notez `Client ID` et `Client Secret`
3. Lancez le helper OAuth pour obtenir le `refresh_token` :

```bash
cd scripts
uvicorn login:app --reload --port 8001
```

Ouvrez [http://localhost:8001/login](http://localhost:8001/login), autorisez l'app Strava, récupérez le `refresh_token` dans la réponse JSON.

### 4. Créer les tables Supabase

Dans l'éditeur SQL de votre projet Supabase, exécutez dans l'ordre :

1. `table sql/create_table.sql` — table `strava_activities`
2. `table sql/create_streams_table.sql` — table `strava_activity_streams`
3. *(optionnel)* `table sql/migration_multi_user.sql` — support multi-utilisateurs (RLS)

## Utilisation

### Démarrer le serveur

```bash
./start.sh
# ou
python app.py
```

Le frontend est disponible dans `docs/` (à ouvrir directement dans un navigateur ou servir via un serveur statique).

### Synchronisation Strava → Supabase

```bash
# Sync des 7 derniers jours (défaut)
python strava_sync.py

# Sync des N derniers jours
python strava_sync.py --days 30

# Sync complète (toutes les activités)
python strava_sync.py --all

# Sync par type de données
python strava_sync.py activities   # Activités seulement
python strava_sync.py laps         # Laps seulement
python strava_sync.py streams      # Traces GPS (~40-60 min pour 2000 activités)
```

Les scripts sont idempotents — safe à relancer, pas de doublons (upsert sur `strava_id`).

### Synchronisation automatique (cron)

```bash
# Exemple : sync quotidienne à 7h
0 7 * * * cd /chemin/vers/strava-backend && ./venv/bin/python strava_sync.py
```

## API Flask

| Route | Description |
|-------|-------------|
| `GET /api/activities` | Toutes les activités de l'année |
| `GET /api/activity/<id>` | Détail d'une activité |
| `GET /api/activity/<id>/streams` | Points GPS (paginé, 1000/page) |
| `GET /api/activity/<id>/laps` | Données de laps |
| `GET /api/stats` | Stats agrégées (distance totale, dénivelé, temps) |

## Données synchronisées

### strava_activities

`strava_id`, `name`, `sport_type`, `distance`, `moving_time`, `elapsed_time`, `total_elevation_gain`, `start_date`, `start_date_local`, `average_speed`, `max_speed`, `average_heartrate`, `max_heartrate`, `elev_high`, `elev_low`, `kudos_count`, `achievement_count`

### strava_activity_streams (GPS)

`latitude`, `longitude`, `altitude`, `time`, `distance`, `heartrate`, `velocity_smooth`, `grade_smooth`, `cadence`, `watts`, `temp`

## Diagnostic

```bash
python scripts/check_latest_activity.py
```

Vérifie que la dernière activité Strava est bien présente dans Supabase (activités + streams).

## Limitations API Strava

- 100 requêtes / 15 min
- 1000 requêtes / jour

`strava_sync.py` respecte automatiquement ces limites avec des pauses adaptées.

## Dépannage

**Variables Strava manquantes** → vérifiez `.env`, pas d'espaces autour du `=`

**Token invalide** → relancez le flow OAuth via `scripts/login.py`

**Table inexistante** → exécutez les scripts SQL dans l'ordre indiqué ci-dessus

**Upsert échoue** → vérifiez la contrainte unique sur `strava_id` dans la table
