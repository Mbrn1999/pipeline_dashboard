-- Table pour stocker les traces GPX (streams) des activités Strava
-- À exécuter dans l'éditeur SQL de Supabase

CREATE TABLE IF NOT EXISTS strava_activity_streams (
    id BIGSERIAL PRIMARY KEY,
    strava_id BIGINT NOT NULL,
    stream_index INTEGER NOT NULL,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    altitude NUMERIC(8, 2),
    time INTEGER,
    distance NUMERIC(10, 2),
    heartrate NUMERIC(5, 1),
    velocity_smooth NUMERIC(8, 4),
    grade_smooth NUMERIC(6, 2),
    cadence INTEGER,
    watts INTEGER,
    temp INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Contrainte unique pour éviter les doublons
    UNIQUE(strava_id, stream_index),

    -- Clé étrangère vers la table des activités
    FOREIGN KEY (strava_id) REFERENCES strava_activities(strava_id) ON DELETE CASCADE
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_streams_strava_id ON strava_activity_streams(strava_id);
CREATE INDEX IF NOT EXISTS idx_streams_location ON strava_activity_streams(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_streams_time ON strava_activity_streams(strava_id, time);

-- Activer PostGIS pour les requêtes géospatiales avancées (optionnel)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- Ajouter une colonne géométrie pour PostGIS (optionnel)
-- ALTER TABLE strava_activity_streams ADD COLUMN geom geometry(Point, 4326);
-- CREATE INDEX IF NOT EXISTS idx_streams_geom ON strava_activity_streams USING GIST(geom);