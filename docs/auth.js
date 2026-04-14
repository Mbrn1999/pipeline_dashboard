// === Auth helpers partages entre toutes les pages ===

const SUPABASE_CONFIG = {
    url: 'https://rwbkodvpqnwryqjusful.supabase.co',
    key: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3YmtvZHZwcW53cnlxanVzZnVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3OTUxNzcsImV4cCI6MjA4NTM3MTE3N30.empUzcIkZtcwS9mE-mC5tyVRCIM5EV1wenEDhJoFqco'
};

const STRAVA_CLIENT_ID = '127701';
const STRAVA_CLIENT_SECRET = '9f1162a228490cceb05e4677a9562bcfad296d59';

let supabaseClient = null;

function initSupabase() {
    if (supabaseClient) return supabaseClient;
    const { createClient } = supabase;
    supabaseClient = createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.key);
    window.supabaseClient = supabaseClient;
    return supabaseClient;
}

async function requireAuth() {
    const client = initSupabase();
    const { data: { session } } = await client.auth.getSession();
    if (!session) {
        window.location.href = 'index.html';
        throw new Error('Not authenticated');
    }
    window.currentUserId = session.user.id;
    window.currentUserEmail = session.user.email;
    return session.user;
}

async function logout() {
    const client = initSupabase();
    await client.auth.signOut();
    window.location.href = 'index.html';
}

async function getUserStravaTokens() {
    const { data, error } = await supabaseClient
        .from('user_strava_tokens')
        .select('*')
        .eq('user_id', window.currentUserId)
        .single();
    if (error || !data) return null;
    return data;
}

async function getStravaAccessToken() {
    const tokens = await getUserStravaTokens();
    if (!tokens) throw new Error('Strava non connecte. Connectez votre compte Strava.');

    // Token encore valide (avec 60s de marge)
    if (tokens.expires_at > Math.floor(Date.now() / 1000) + 60) {
        return tokens.access_token;
    }

    // Refresh le token
    const res = await fetch('https://www.strava.com/oauth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: STRAVA_CLIENT_ID,
            client_secret: STRAVA_CLIENT_SECRET,
            refresh_token: tokens.refresh_token,
            grant_type: 'refresh_token'
        })
    });
    const data = await res.json();
    if (!data.access_token) throw new Error('Impossible de rafraichir le token Strava');

    // Sauvegarder les nouveaux tokens
    await supabaseClient
        .from('user_strava_tokens')
        .update({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            expires_at: data.expires_at
        })
        .eq('user_id', window.currentUserId);

    return data.access_token;
}

function connectStrava() {
    const redirectUri = encodeURIComponent('https://sentier-sante.hosterfy.net/strava/dashboard.html');
    const scope = 'read,activity:read_all,activity:write';
    window.location.href = `https://www.strava.com/oauth/authorize?client_id=${STRAVA_CLIENT_ID}&response_type=code&redirect_uri=${redirectUri}&approval_prompt=force&scope=${scope}`;
}

async function handleStravaCallback(code) {
    const res = await fetch('https://www.strava.com/oauth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: STRAVA_CLIENT_ID,
            client_secret: STRAVA_CLIENT_SECRET,
            code: code,
            grant_type: 'authorization_code'
        })
    });
    const data = await res.json();
    if (!data.access_token) throw new Error('Erreur OAuth Strava: ' + (data.message || 'Inconnu'));

    await supabaseClient
        .from('user_strava_tokens')
        .upsert({
            user_id: window.currentUserId,
            strava_athlete_id: data.athlete?.id,
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            expires_at: data.expires_at
        }, { onConflict: 'user_id' });

    return data;
}
