# game_logic.py

from games_data import games
from database import *

def schedule_game(available_teams: list):
    """
    Schedules a match based on teams with the least 'Games_played'.
    Returns a tuple with two teams.
    """
    sorted_teams = sorted(available_teams, key=lambda t: (t["Games_played"] or 0))
    if len(sorted_teams) >= 2:
        return sorted_teams[0], sorted_teams[1]
    return None

def calculate_handicap(team: dict, game_type: str):
    """
    Returns the handicap for a given sport based on the team's win streak.
    If the win streak is 0, returns ["No Handicap"].
    Otherwise, if win streak is n, returns the nth handicap (index n-1) from the game's definition.
    If the team is marked as King (team["king"] is True), the returned handicap is prefixed with "King/Queen".
    """
    win_streak = get_team_win_streak(team["id"], game_type)
    if team.get("king"):
        if win_streak < 4:
            win_streak = win_streak + 1
    game_info = get_game_by_name(game_type)
    if not game_info:
        return ["No Handicap"]

    # Build a list of handicap levels from the game definition.
    levels = [
        game_info["handicap1"],
        game_info["handicap2"],
        game_info["handicap3"],
        game_info["handicap4"]
    ]
    
    # If win_streak is less than 1, no handicap is applied.
    if win_streak < 1:
        return ["No Handicap"]

    # Calculate index (win_streak - 1), but cap it to the last available level.
    index = win_streak - 1
    if index >= len(levels):
        index = len(levels) - 1

    handicap = levels[index]
    
    return [handicap]