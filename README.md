# Strava to Supabase - Guide d'utilisation

Ce script récupère toutes vos activités Strava et les envoie dans une base de données Supabase.

## 📋 Prérequis

1. Un compte Strava avec des activités
2. Un compte Supabase (gratuit)
3. Python 3.7+ installé

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Créer la table Supabase

1. Allez sur votre dashboard Supabase : https://app.supabase.com
2. Sélectionnez votre projet
3. Cliquez sur "SQL Editor" dans le menu de gauche
4. Créez une nouvelle query
5. Copiez-collez le contenu du fichier `create_table.sql`
6. Exécutez la query (bouton "Run" ou Ctrl+Enter)

### 3. Obtenir vos credentials Strava

#### A. Client ID et Client Secret

1. Allez sur https://www.strava.com/settings/api
2. Créez une nouvelle application (si ce n'est pas déjà fait)
3. Notez votre `Client ID` et `Client Secret`

#### B. Refresh Token

**Option 1 : Utiliser le serveur FastAPI existant**

1. Lancez le serveur :
```bash
uvicorn main:app --reload --port 8001
```

2. Ouvrez votre navigateur et allez sur :
```
http://localhost:8001/login
```

3. Copiez l'URL retournée et collez-la dans votre navigateur

4. Autorisez l'application Strava

5. Vous serez redirigé vers `http://localhost:8001/callback?code=...`

6. La réponse JSON contient votre `refresh_token` - copiez-le !

**Option 2 : Obtenir le token manuellement**

1. Construisez cette URL (remplacez `VOTRE_CLIENT_ID`) :
```
https://www.strava.com/oauth/authorize?client_id=VOTRE_CLIENT_ID&response_type=code&redirect_uri=http://localhost:8001/callback&approval_prompt=auto&scope=read,activity:read_all
```

2. Collez l'URL dans votre navigateur et autorisez

3. Vous serez redirigé vers une URL qui contient un `code=...`

4. Utilisez ce code pour obtenir le refresh_token :
```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=VOTRE_CLIENT_ID \
  -d client_secret=VOTRE_CLIENT_SECRET \
  -d code=LE_CODE_RECU \
  -d grant_type=authorization_code
```

5. La réponse contient votre `refresh_token`

### 4. Obtenir vos credentials Supabase

1. Allez sur votre dashboard Supabase : https://app.supabase.com
2. Sélectionnez votre projet
3. Cliquez sur l'icône "Settings" (roue dentée) en bas à gauche
4. Cliquez sur "API" dans le menu
5. Copiez :
   - **URL** (sous "Project URL")
   - **anon/public key** (sous "Project API keys")

### 5. Configurer le fichier .env

Modifiez le fichier `.env` avec vos valeurs :

```env
STRAVA_CLIENT_ID=127701
STRAVA_CLIENT_SECRET=votre_client_secret_ici
STRAVA_REFRESH_TOKEN=votre_refresh_token_ici

# Supabase
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_KEY=votre_cle_supabase_ici
```

## ▶️ Utilisation

Lancez simplement le script :

```bash
python strava_to_supabase.py
```

Le script va :
1. Se connecter à Strava
2. Récupérer toutes vos activités (pagination automatique)
3. Les formater correctement
4. Les envoyer dans Supabase (avec gestion des doublons)

## 📊 Données récupérées

Pour chaque activité, le script récupère :
- **strava_id** : ID unique Strava
- **name** : Nom de l'activité
- **sport_type** : Type de sport (Run, Ride, Swim, etc.)
- **distance** : Distance en mètres
- **moving_time** : Temps en mouvement (secondes)
- **elapsed_time** : Temps total (secondes)
- **total_elevation_gain** : Dénivelé positif (mètres)
- **start_date** : Date/heure de début (UTC)
- **start_date_local** : Date/heure de début (locale)
- **average_speed** : Vitesse moyenne (m/s)
- **max_speed** : Vitesse max (m/s)
- **average_heartrate** : Fréquence cardiaque moyenne
- **max_heartrate** : Fréquence cardiaque max
- **elev_high** : Altitude max
- **elev_low** : Altitude min
- **kudos_count** : Nombre de kudos
- **achievement_count** : Nombre de réalisations

## 🔄 Synchronisation automatique

Pour synchroniser automatiquement vos activités, vous pouvez :

1. **Créer un cron job** (Linux/Mac) :
```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne pour exécuter tous les jours à 8h
0 8 * * * cd /chemin/vers/strava-backend && /usr/bin/python3 strava_to_supabase.py
```

2. **Créer une tâche planifiée** (Windows) :
- Ouvrez le Planificateur de tâches
- Créez une nouvelle tâche
- Configurez-la pour exécuter `python strava_to_supabase.py`

## ⚠️ Limitations

- L'API Strava a des limites de taux : 100 requêtes toutes les 15 minutes, 1000 par jour
- Le script utilise la pagination (200 activités par page) pour optimiser les requêtes
- Les doublons sont automatiquement gérés (basé sur `strava_id`)

## 🐛 Dépannage

**Erreur : Variables Strava manquantes**
- Vérifiez que votre fichier `.env` contient toutes les variables
- Assurez-vous qu'il n'y a pas d'espaces autour du `=`

**Erreur : Impossible de récupérer le token**
- Vérifiez votre `STRAVA_REFRESH_TOKEN`
- Régénérez un nouveau refresh_token si nécessaire

**Erreur Supabase : table does not exist**
- Assurez-vous d'avoir exécuté le script SQL `create_table.sql` dans Supabase

**Erreur : upsert failed**
- Vérifiez que la table a bien une contrainte unique sur `strava_id`

## 🗺️ Récupérer les traces GPX (coordonnées GPS)

En plus des informations de base des activités, vous pouvez récupérer toutes les traces GPS détaillées.

### 1. Créer la table des traces

Dans l'éditeur SQL de Supabase :
1. Créez une nouvelle query
2. Copiez-collez le contenu du fichier `create_streams_table.sql`
3. Exécutez la query

### 2. Lancer le script GPX

```bash
./venv/bin/python strava_streams_to_supabase.py
```

Ce script va :
- Récupérer les coordonnées GPS de chaque point de toutes vos activités
- Envoyer les données dans la table `strava_activity_streams`

**Attention :** Ce processus est long car il fait une requête API par activité.
- Pour 2000 activités, cela prend environ 40-60 minutes
- Le script respecte automatiquement les limites de l'API Strava (100 req/15min)

### Données GPX récupérées

Pour chaque point GPS :
- **latitude/longitude** : Coordonnées GPS
- **altitude** : Altitude en mètres
- **time** : Temps depuis le début (secondes)
- **distance** : Distance cumulée (mètres)
- **heartrate** : Fréquence cardiaque
- **velocity_smooth** : Vitesse lissée (m/s)
- **grade_smooth** : Pente lissée (%)
- **cadence** : Cadence (tours/min)
- **watts** : Puissance (watts)
- **temp** : Température (°C)

### Utilisation des données GPS

Une fois les données importées, vous pouvez :
- Afficher les traces sur une carte
- Analyser les variations d'altitude
- Étudier l'évolution de la vitesse/cardio sur le parcours
- Créer des heatmaps de vos zones d'entraînement
- Exporter en GPX pour d'autres outils

Exemple de requête SQL pour récupérer une trace :
```sql
SELECT latitude, longitude, altitude, time, heartrate
FROM strava_activity_streams
WHERE strava_id = 123456789
ORDER BY stream_index;
```

## 📝 Notes

- Les scripts sont idempotents : vous pouvez les relancer sans créer de doublons
- Les timestamps sont en UTC dans Strava, utilisez `start_date_local` pour l'heure locale
- Pour convertir les distances : diviser par 1000 pour avoir des kilomètres
- Pour convertir les temps : diviser par 60 pour avoir des minutes, par 3600 pour des heures
- Toutes les activités n'ont pas de traces GPS (ex: activités manuelles, natation en piscine)