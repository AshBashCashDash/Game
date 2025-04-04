import json
import os
from sqlalchemy import create_engine, text

password = os.environ.get("SUPABASE_PASSWORD")
DATABASE_URL = f"postgresql://postgres.nbhpzqbsbmlkimvffdin:{password}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"



# Create an engine to connect to the database.
engine = create_engine(DATABASE_URL)

def clear_database():
    """
    Clears the ScheduledMatches and TeamTokens tables.
    WARNING: This will remove all scheduled matches and token records.
    """
    query1 = text('TRUNCATE public."ScheduledMatches" RESTART IDENTITY CASCADE')
    query2 = text('TRUNCATE public."TeamTokens" RESTART IDENTITY CASCADE')
    query3 = text('TRUNCATE public."TeamHandicaps" RESTART IDENTITY CASCADE')
    query4 = text('TRUNCATE public."NonGameRule" RESTART IDENTITY CASCADE')
    query5 = text('TRUNCATE public."PastGames" RESTART IDENTITY CASCADE')
    with engine.begin() as conn:
        conn.execute(query1)
        conn.execute(query2)
        conn.execute(query3)
        conn.execute(query4)
        conn.execute(query5)
    return True

def reset_teams_stats():
    """
    Resets all integer columns in the Teams table (Score, Games_played, Lose_Streak,
    Overtime_Games_Lost, current_game_win_streak) to 0. Leaves team_name and id unchanged.
    """
    query = text('''
        UPDATE public."Teams"
        SET "Score" = 0,
            "Games_played" = 0,
            "Lose_Streak" = 0,
            "Overtime_Games_Lost" = 0,
            "king" = CASE WHEN id = 7 THEN TRUE ELSE FALSE END
    ''')
    with engine.begin() as conn:
        conn.execute(query)
    return True

def get_all_teams():
    """
    Retrieves all teams from the public.Teams table.
    """
    with engine.connect() as conn:
        result = conn.execute(text('SELECT * FROM public."Teams"'))
        teams = [dict(row._mapping) for row in result]
    return teams

def update_team_score(team_id: int, new_score: int):
    """
    Updates the team's score in the public.Teams table.
    """
    with engine.begin() as conn:
        conn.execute(
            text('UPDATE public."Teams" SET "Score" = :new_score WHERE id = :team_id'),
            {"new_score": new_score, "team_id": team_id}
        )
    return True

def update_team_field(team_id: int, field_name: str, value):
    allowed_fields = {"Games_played", "Lose_Streak", "Overtime_Games_Lost", "current_game_win_streak", "king"}
    if field_name not in allowed_fields:
        raise ValueError("Field not allowed for update")
    query = text(f'UPDATE public."Teams" SET "{field_name}" = :value WHERE id = :team_id')
    with engine.begin() as conn:
        conn.execute(query, {"value": value, "team_id": team_id})
    return True


def get_team_tokens(team_id: int):
    """
    Retrieve all tokens for a given team as a dictionary.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT token_name, count FROM public."TeamTokens" WHERE team_id = :team_id'),
            {"team_id": team_id}
        )
        tokens = {row._mapping["token_name"]: row._mapping["count"] for row in result}
    return tokens

def update_team_token(team_id: int, token_name: str, new_count: int):
    """
    Update the token count for a given team and token type.
    If a record doesn't exist, insert a new one.
    """
    with engine.begin() as conn:
        conn.execute(
            text('''
                INSERT INTO public."TeamTokens" (team_id, token_name, count)
                VALUES (:team_id, :token_name, :new_count)
                ON CONFLICT (team_id, token_name)
                DO UPDATE SET count = :new_count
            '''),
            {"team_id": team_id, "token_name": token_name, "new_count": new_count}
        )
    return True

def insert_scheduled_match(sport: str, team1_id: int, team2_id: int, handicap1: list, handicap2: list):
    """
    Inserts a scheduled match record into the ScheduledMatches table.
    Returns the newly created match's ID.
    """
    query = text('''
        INSERT INTO public."ScheduledMatches" (sport, team1_id, team2_id, handicap1, handicap2)
        VALUES (:sport, :team1_id, :team2_id, :handicap1, :handicap2)
        RETURNING id
    ''')
    with engine.begin() as conn:
        result = conn.execute(query, {
            "sport": sport,
            "team1_id": team1_id,
            "team2_id": team2_id,
            "handicap1": json.dumps(handicap1),
            "handicap2": json.dumps(handicap2)
        })
        inserted_id = result.scalar()  # gets the generated id
    return inserted_id

def get_scheduled_matches():
    """
    Retrieves all scheduled matches from the ScheduledMatches table.
    Converts the handicap fields from JSON (if needed) to Python lists.
    """
    query = text('SELECT * FROM public."ScheduledMatches" ORDER BY created_at DESC')
    with engine.connect() as conn:
        result = conn.execute(query)
        matches = []
        for row in result:
            match = dict(row._mapping)
            # Convert handicap1 if it's a string; otherwise assume it's already a list or None
            if match.get('handicap1'):
                if isinstance(match['handicap1'], str):
                    match['handicap1'] = json.loads(match['handicap1'])
                # Else, assume it's already a list (or other structure) and leave it as-is
            else:
                match['handicap1'] = []
            
            if match.get('handicap2'):
                if isinstance(match['handicap2'], str):
                    match['handicap2'] = json.loads(match['handicap2'])
                # Else, assume it's already a list
            else:
                match['handicap2'] = []
            
            matches.append(match)
    return matches

def delete_scheduled_match(match_id: int):
    """
    Deletes a scheduled match from the ScheduledMatches table.
    """
    query = text('DELETE FROM public."ScheduledMatches" WHERE id = :match_id')
    with engine.begin() as conn:
        conn.execute(query, {"match_id": match_id})
    return True

def insert_past_game(sport: str, team1_name: str, team2_name: str, team1_score: int, team2_score: int):
    """
    Inserts a completed game's details into the PastGames table.
    """
    query = text('''
        INSERT INTO public."PastGames" (sport, team1, team2, team1_score, team2_score)
        VALUES (:sport, :team1, :team2, :team1_score, :team2_score)
    ''')
    with engine.begin() as conn:
        conn.execute(query, {
            "sport": sport,
            "team1": team1_name,
            "team2": team2_name,
            "team1_score": team1_score,
            "team2_score": team2_score
        })
    return True

def get_team_win_streak(team_id: int, sport: str) -> int:
    """
    Retrieves the current win streak for a team in a specific sport.
    """
    query = text('SELECT win_streak FROM public."TeamHandicaps" WHERE team_id = :team_id AND sport = :sport')
    with engine.connect() as conn:
        result = conn.execute(query, {"team_id": team_id, "sport": sport})
        row = result.fetchone()
        if row:
            return row._mapping["win_streak"]
        else:
            return 0

def set_team_win_streak(team_id: int, sport: str, win_streak: int) -> bool:
    """
    Updates (or inserts) the win streak for a team in a given sport.
    """
    query = text('''
        INSERT INTO public."TeamHandicaps" (team_id, sport, win_streak)
        VALUES (:team_id, :sport, :win_streak)
        ON CONFLICT (team_id, sport)
        DO UPDATE SET win_streak = :win_streak
    ''')
    with engine.begin() as conn:
        conn.execute(query, {"team_id": team_id, "sport": sport, "win_streak": win_streak})
    return True

def get_non_game_rule():
    """
    Retrieves the current non-game rule (the most recent entry).
    """
    query = text('SELECT rule, penalty FROM public."NonGameRule" ORDER BY updated_at DESC LIMIT 1')
    with engine.connect() as conn:
        result = conn.execute(query)
        row = result.fetchone()
        if row:
            return {"rule": row._mapping["rule"], "penalty": row._mapping["penalty"]}
        else:
            return {"rule": "No rule yet", "penalty": 0}

def set_non_game_rule(rule: str, penalty: int):
    """
    Inserts a new non-game rule into the database.
    """
    query = text('INSERT INTO public."NonGameRule" (rule, penalty) VALUES (:rule, :penalty)')
    with engine.begin() as conn:
        conn.execute(query, {"rule": rule, "penalty": penalty})
    return True

def get_all_non_game_rules():
    """
    Retrieves all non-game rules from the NonGameRule table.
    """
    query = text('SELECT rule, penalty FROM public."NonGameRule" ORDER BY updated_at DESC')
    with engine.connect() as conn:
        result = conn.execute(query)
        rules = [dict(row._mapping) for row in result]
    return rules

def reset_non_game_rules():
    """
    Deletes all entries from the NonGameRule table.
    """
    query = text('DELETE FROM public."NonGameRule"')
    with engine.begin() as conn:
        conn.execute(query)
    return True

def get_game_by_name(name: str):
    """
    Retrieves a game definition from the Games table by its name.
    """
    query = text('SELECT * FROM public."Games" WHERE name = :name')
    with engine.connect() as conn:
        result = conn.execute(query, {"name": name})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None

def insert_game(name: str, points: int, game_type: str, handicap1: str, handicap2: str, handicap3: str, handicap4: str):
    """
    Inserts a new game definition into the Games table.
    Returns the new game's id.
    """
    query = text('''
        INSERT INTO public."Games" (name, points, type, handicap1, handicap2, handicap3, handicap4)
        VALUES (:name, :points, :game_type, :handicap1, :handicap2, :handicap3, :handicap4)
        RETURNING id
    ''')
    with engine.begin() as conn:
        result = conn.execute(query, {
            "name": name,
            "points": points,
            "game_type": game_type,
            "handicap1": handicap1,
            "handicap2": handicap2,
            "handicap3": handicap3,
            "handicap4": handicap4
        })
        return result.scalar()
    
def get_all_games():
    """
    Retrieves all game definitions from the Games table.
    """
    query = text('SELECT * FROM public."Games" ORDER BY name ASC')
    with engine.connect() as conn:
        result = conn.execute(query)
        games_list = [dict(row._mapping) for row in result]
    return games_list