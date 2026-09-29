import requests
import os

AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']
FOOTBALL_DATA_KEY = os.environ['FOOTBALL_DATA_KEY']

AIRTABLE_HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_TOKEN}',
    'Content-Type': 'application/json'
}

COMPETITION_CODE = 'PL'
SEASON = '2026'

def get_fixtures():
    url = f'https://api.football-data.org/v4/competitions/{COMPETITION_CODE}/matches?season={SEASON}'
    resp = requests.get(url, headers={'X-Auth-Token': FOOTBALL_DATA_KEY})
    resp.raise_for_status()
    return resp.json()['matches']

def get_airtable_fixtures():
    records = []
    offset = None
    while True:
        params = {'pageSize': 100}
        if offset:
            params['offset'] = offset
        resp = requests.get(
            f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Fixtures',
            headers=AIRTABLE_HEADERS,
            params=params
        )
        data = resp.json()
        records.extend(data.get('records', []))
        offset = data.get('offset')
        if not offset:
            break
    return {r['fields'].get('Fixture ID'): r['id'] for r in records}

def upsert_fixtures(matches, existing):
    # Only sync GW1-19 to stay under Airtable record limit
    matches = [m for m in matches if m.get('matchday', 99) <= 19]
    
    updated = 0
    created = 0
    
    for match in matches:
        fixture_id = match['id']
        fields = {
            'Fixture ID': fixture_id,
            'Home Team': match['homeTeam']['name'],
            'Away Team': match['awayTeam']['name'],
            'Date': match['utcDate'],
            'Status': match['status'],
            'Matchday': match.get('matchday'),
        }
        
        if fixture_id in existing:
            # Update existing record
            resp = requests.patch(
                f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Fixtures/{existing[fixture_id]}',
                headers=AIRTABLE_HEADERS,
                json={'fields': fields}
            )
            updated += 1
        else:
            # Create new record
            resp = requests.post(
                f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Fixtures',
                headers=AIRTABLE_HEADERS,
                json={'fields': fields}
            )
            created += 1
            
        if resp.status_code not in (200, 201):
            print(f"Error on fixture {fixture_id}: {resp.text}")
    
    print(f"Done — Updated: {updated}, Created: {created}")

if __name__ == '__main__':
    print("Fetching fixtures from football-data.org...")
    matches = get_fixtures()
    print(f"Got {len(matches)} matches")
    
    print("Fetching existing Airtable fixtures...")
    existing = get_airtable_fixtures()
    print(f"Found {len(existing)} existing records")
    
    print("Upserting fixtures...")
    upsert_fixtures(matches, existing)
