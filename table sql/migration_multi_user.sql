-- =============================================================
-- Migration : Multi-utilisateur avec Supabase Auth
-- A executer dans le SQL Editor de Supabase (dans l'ordre)
-- Utilise IF NOT EXISTS pour eviter les erreurs si deja execute
-- =============================================================

-- 1. Table des tokens Strava par utilisateur
CREATE TABLE IF NOT EXISTS user_strava_tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    strava_athlete_id BIGINT,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);
CREATE INDEX IF NOT EXISTS idx_user_strava_tokens_user_id ON user_strava_tokens(user_id);

-- 2. Ajouter user_id a toutes les tables existantes
ALTER TABLE strava_activities ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_strava_activities_user_id ON strava_activities(user_id);

ALTER TABLE strava_activity_streams ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_streams_user_id ON strava_activity_streams(user_id);

ALTER TABLE strava_laps ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_laps_user_id ON strava_laps(user_id);

ALTER TABLE trainings ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_trainings_user_id ON trainings(user_id);

ALTER TABLE training_weeks ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_training_weeks_user_id ON training_weeks(user_id);

ALTER TABLE agenda_events ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_agenda_events_user_id ON agenda_events(user_id);

-- 3. Supprimer les foreign keys qui dependent des anciennes contraintes UNIQUE
ALTER TABLE strava_activity_streams DROP CONSTRAINT IF EXISTS strava_activity_streams_strava_id_fkey;
ALTER TABLE strava_laps DROP CONSTRAINT IF EXISTS fk_strava_laps_activity;

-- 4. Mettre a jour les contraintes UNIQUE (multi-user)
ALTER TABLE strava_activities DROP CONSTRAINT IF EXISTS strava_activities_strava_id_key;
ALTER TABLE strava_activities DROP CONSTRAINT IF EXISTS strava_activities_user_strava_id_key;
ALTER TABLE strava_activities ADD CONSTRAINT strava_activities_user_strava_id_key UNIQUE(user_id, strava_id);

ALTER TABLE strava_activity_streams DROP CONSTRAINT IF EXISTS strava_activity_streams_strava_id_stream_index_key;
ALTER TABLE strava_activity_streams DROP CONSTRAINT IF EXISTS strava_activity_streams_user_strava_stream_key;
ALTER TABLE strava_activity_streams ADD CONSTRAINT strava_activity_streams_user_strava_stream_key UNIQUE(user_id, strava_id, stream_index);

ALTER TABLE strava_laps DROP CONSTRAINT IF EXISTS strava_laps_lap_id_key;
ALTER TABLE strava_laps DROP CONSTRAINT IF EXISTS strava_laps_user_lap_id_key;
ALTER TABLE strava_laps ADD CONSTRAINT strava_laps_user_lap_id_key UNIQUE(user_id, lap_id);

-- 4. Activer RLS sur toutes les tables
ALTER TABLE strava_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE strava_activity_streams ENABLE ROW LEVEL SECURITY;
ALTER TABLE strava_laps ENABLE ROW LEVEL SECURITY;
ALTER TABLE trainings ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_weeks ENABLE ROW LEVEL SECURITY;
ALTER TABLE agenda_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_strava_tokens ENABLE ROW LEVEL SECURITY;

-- 5. Politiques RLS (chaque user voit/modifie uniquement ses donnees)
-- DROP IF EXISTS pour eviter les doublons

-- strava_activities
DROP POLICY IF EXISTS "Users can view own activities" ON strava_activities;
DROP POLICY IF EXISTS "Users can insert own activities" ON strava_activities;
DROP POLICY IF EXISTS "Users can update own activities" ON strava_activities;
DROP POLICY IF EXISTS "Users can delete own activities" ON strava_activities;
CREATE POLICY "Users can view own activities" ON strava_activities FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own activities" ON strava_activities FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own activities" ON strava_activities FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own activities" ON strava_activities FOR DELETE USING (auth.uid() = user_id);

-- strava_activity_streams
DROP POLICY IF EXISTS "Users can view own streams" ON strava_activity_streams;
DROP POLICY IF EXISTS "Users can insert own streams" ON strava_activity_streams;
DROP POLICY IF EXISTS "Users can update own streams" ON strava_activity_streams;
DROP POLICY IF EXISTS "Users can delete own streams" ON strava_activity_streams;
CREATE POLICY "Users can view own streams" ON strava_activity_streams FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own streams" ON strava_activity_streams FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own streams" ON strava_activity_streams FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own streams" ON strava_activity_streams FOR DELETE USING (auth.uid() = user_id);

-- strava_laps
DROP POLICY IF EXISTS "Users can view own laps" ON strava_laps;
DROP POLICY IF EXISTS "Users can insert own laps" ON strava_laps;
DROP POLICY IF EXISTS "Users can update own laps" ON strava_laps;
DROP POLICY IF EXISTS "Users can delete own laps" ON strava_laps;
CREATE POLICY "Users can view own laps" ON strava_laps FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own laps" ON strava_laps FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own laps" ON strava_laps FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own laps" ON strava_laps FOR DELETE USING (auth.uid() = user_id);

-- trainings
DROP POLICY IF EXISTS "Users can view own trainings" ON trainings;
DROP POLICY IF EXISTS "Users can insert own trainings" ON trainings;
DROP POLICY IF EXISTS "Users can update own trainings" ON trainings;
DROP POLICY IF EXISTS "Users can delete own trainings" ON trainings;
CREATE POLICY "Users can view own trainings" ON trainings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own trainings" ON trainings FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own trainings" ON trainings FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own trainings" ON trainings FOR DELETE USING (auth.uid() = user_id);

-- training_weeks
DROP POLICY IF EXISTS "Users can view own training_weeks" ON training_weeks;
DROP POLICY IF EXISTS "Users can insert own training_weeks" ON training_weeks;
DROP POLICY IF EXISTS "Users can update own training_weeks" ON training_weeks;
DROP POLICY IF EXISTS "Users can delete own training_weeks" ON training_weeks;
CREATE POLICY "Users can view own training_weeks" ON training_weeks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own training_weeks" ON training_weeks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own training_weeks" ON training_weeks FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own training_weeks" ON training_weeks FOR DELETE USING (auth.uid() = user_id);

-- agenda_events
DROP POLICY IF EXISTS "Users can view own events" ON agenda_events;
DROP POLICY IF EXISTS "Users can insert own events" ON agenda_events;
DROP POLICY IF EXISTS "Users can update own events" ON agenda_events;
DROP POLICY IF EXISTS "Users can delete own events" ON agenda_events;
CREATE POLICY "Users can view own events" ON agenda_events FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own events" ON agenda_events FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own events" ON agenda_events FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own events" ON agenda_events FOR DELETE USING (auth.uid() = user_id);

-- user_strava_tokens
DROP POLICY IF EXISTS "Users can view own tokens" ON user_strava_tokens;
DROP POLICY IF EXISTS "Users can insert own tokens" ON user_strava_tokens;
DROP POLICY IF EXISTS "Users can update own tokens" ON user_strava_tokens;
DROP POLICY IF EXISTS "Users can delete own tokens" ON user_strava_tokens;
CREATE POLICY "Users can view own tokens" ON user_strava_tokens FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own tokens" ON user_strava_tokens FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own tokens" ON user_strava_tokens FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own tokens" ON user_strava_tokens FOR DELETE USING (auth.uid() = user_id);


-- =============================================================
-- APRES inscription du premier utilisateur :
-- Remplacer XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX par l'UUID
-- du premier user (visible dans Supabase > Authentication > Users)
-- =============================================================

-- UPDATE strava_activities SET user_id = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' WHERE user_id IS NULL;
-- UPDATE strava_activity_streams SET user_id = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' WHERE user_id IS NULL;
-- UPDATE strava_laps SET user_id = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' WHERE user_id IS NULL;
-- UPDATE trainings SET user_id = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' WHERE user_id IS NULL;
-- UPDATE training_weeks SET user_id = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' WHERE user_id IS NULL;
-- UPDATE agenda_events SET user_id = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' WHERE user_id IS NULL;

-- Puis rendre user_id obligatoire :
-- ALTER TABLE strava_activities ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE strava_activity_streams ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE strava_laps ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE trainings ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE training_weeks ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE agenda_events ALTER COLUMN user_id SET NOT NULL;
