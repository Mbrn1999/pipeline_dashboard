-- Table pour stocker les activités Strava
-- À exécuter dans l'éditeur SQL de Supabase

CREATE TABLE IF NOT EXISTS strava_activities (
    id BIGSERIAL PRIMARY KEY,
    strava_id BIGINT UNIQUE NOT NULL,
    name TEXT,
    sport_type TEXT,
    distance NUMERIC,
    moving_time INTEGER,
    elapsed_time INTEGER,
    total_elevation_gain NUMERIC,
    start_date TIMESTAMPTZ,
    start_date_local TIMESTAMPTZ,
    average_speed NUMERIC,
    max_speed NUMERIC,
    average_heartrate NUMERIC,
    max_heartrate NUMERIC,
    elev_high NUMERIC,
    elev_low NUMERIC,
    kudos_count INTEGER,
    achievement_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_strava_activities_strava_id ON strava_activities(strava_id);
CREATE INDEX IF NOT EXISTS idx_strava_activities_start_date ON strava_activities(start_date_local);
CREATE INDEX IF NOT EXISTS idx_strava_activities_sport_type ON strava_activities(sport_type);

-- Trigger pour mettre à jour automatiquement updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_strava_activities_updated_at
    BEFORE UPDATE ON strava_activities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();