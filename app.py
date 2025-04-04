import streamlit as st
from database import *
from game_logic import schedule_game, calculate_handicap
from token_data import tokens as token_definitions


menu = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "Schedule Game",
        "Submit Scores",
        "Non-Game Rules",
        "Leave Location",
        "Token Management",
        "Available Games",
        "Rules",
        "Admin Panel",
    ]
)

if menu == "Home":
    
    # --- Leaderboard ---
    st.markdown("## Leaderboard")
    teams = get_all_teams()
    # Sort teams by score (descending)
    teams_sorted = sorted(teams, key=lambda t: t.get("Score", 0), reverse=True)
    leaderboard = []
    for team in teams_sorted:
        name = team["team_name"]
        if team.get("king"):
            name += " 👑"
        leaderboard.append({
            "Team": name,
            "Score": team.get("Score", 0),
            "Games Played": team.get("Games_played", 0)
        })
    st.table(leaderboard)
    
    # --- Non-Game Rules ---
    st.markdown("## Current Non-Game Rules")
    # Retrieve all non-game rules from the database; if no helper exists, you could also call get_non_game_rule()
    rules = get_all_non_game_rules()  # This function should return a list of rules
    if rules:
        for rule in rules:
            st.write(f"**Rule:** {rule['rule']}  —  **Penalty:** {rule['penalty']}")
            st.subheader("Log a Rule Break")
        # Allow user to choose which rule was broken
        if rules:
            rule_options = {f"{rule['rule']} (Penalty: {rule['penalty']})": rule for rule in rules}
            selected_rule_desc = st.selectbox("Select the rule that was broken", list(rule_options.keys()))
            selected_rule = rule_options[selected_rule_desc]
        else:
            selected_rule = None
            # List all teams for selection
        if teams:
            team_options = {team["team_name"]: team for team in teams}
            selected_team_name = st.selectbox("Select the team that broke the rule", list(team_options.keys()))
            rule_break_team = team_options[selected_team_name]
        else:
            rule_break_team = None

        if st.button("Log Rule Break"):
            if selected_rule is None or rule_break_team is None:
                st.error("Please select both a rule and a team.")
            else:
                penalty = selected_rule["penalty"]
                current_score = rule_break_team.get("Score") or 0
                new_score = current_score - penalty
                update_team_score(rule_break_team["id"], new_score)
                st.success(f"Logged rule break: {rule_break_team['team_name']}'s score deducted by {penalty} points.")
    else:
        st.info("No non-game rules set.")




    # --- Tokens In Play ---
    st.markdown("## Tokens In Play")
    tokens_found = False
    teams = get_all_teams()
    for team in teams:
        team_tokens = get_team_tokens(team["id"])
        if team_tokens and any(count > 0 for count in team_tokens.values()):
            tokens_found = True
            st.subheader(f"Team: {team['team_name']} (ID: {team['id']})")
            for token_name, count in team_tokens.items():
                if count > 0:
                    st.write(f"**{token_name}:** {count} available")
                    token_info = token_definitions.get(token_name, {})
                    st.write(f"**Benefit:** {token_info.get('benefit', 'No benefit info available')}")
            st.markdown("---")
    if not tokens_found:
        st.info("No tokens available for any team.")

# ------------------- Schedule Game -------------------
elif menu == "Schedule Game":
    st.header("Schedule a Match")
    # Retrieve game definitions from the database and build a list of game names
    all_games = get_all_games()
    game_names = [game["name"] for game in all_games]
    selected_sport = st.selectbox("Select a Sport", game_names)
    
    if st.button("Schedule Match"):
        # Retrieve game definition for the selected sport
        game_info = get_game_by_name(selected_sport)
        if game_info["type"] == "Single Play":
            # For single play games, do not schedule a two-team match.
            # Instead, insert a record indicating the game is ongoing.
            new_match_id = insert_scheduled_match(selected_sport, None, None, [], [])
            st.success(f"{selected_sport} Ongoing (Match ID: {new_match_id})")
        else:
            # For Multi Play games, schedule a match between teams.
            persistent_matches = get_scheduled_matches()
            scheduled_team_ids = {
                m["team1_id"] for m in persistent_matches if m["team1_id"] is not None
            } | {m["team2_id"] for m in persistent_matches if m["team2_id"] is not None}
            teams = get_all_teams()
            available_teams = [team for team in teams if team["id"] not in scheduled_team_ids]

            if len(available_teams) < 2:
                st.warning("Not enough teams available for scheduling a new match. Please submit scores from previous matches to free up teams.")
            else:
                match = schedule_game(available_teams)
                if match:
                    team1, team2 = match
                    handicap1 = calculate_handicap(team1, game_type=selected_sport)
                    handicap2 = calculate_handicap(team2, game_type=selected_sport)
                    new_match_id = insert_scheduled_match(selected_sport, team1["id"], team2["id"], handicap1, handicap2)
                    st.success(f"Match scheduled! (Match ID: {new_match_id})")
                else:
                    st.info("No match scheduled.")

    # Display all scheduled matches from the database
    matches = get_scheduled_matches()
    st.subheader("Currently Scheduled Matches")
    if matches:
        teams = get_all_teams()
        for m in matches:
            st.write("**Match ID:**", m["id"])
            st.write("**Sport:**", m["sport"])
            if m["team1_id"] is None:
                # Single Play game ongoing record
                st.write(f"{m['sport']} Ongoing")
            else:
                team1 = next((t for t in teams if t["id"] == m["team1_id"]), {"team_name": "Unknown"})
                team2 = next((t for t in teams if t["id"] == m["team2_id"]), {"team_name": "Unknown"})
                st.write("**Team 1:**", team1["team_name"], " | Handicap:",
                         m["handicap1"][0] if m["handicap1"] and m["handicap1"][0] else "None")
                st.write("**Team 2:**", team2["team_name"], " | Handicap:",
                         m["handicap2"][0] if m["handicap2"] and m["handicap2"][0] else "None")
            st.markdown("---")
    else:
        st.info("No scheduled matches available.")
    
    # Option to cancel a scheduled match
    st.subheader("Cancel a Scheduled Match")
    if matches:
        cancel_options = {}
        # Use the same team cache if available
        teams = get_all_teams()
        for m in matches:
            if m["team1_id"] is None:
                desc = f"{m['sport']} Ongoing (Match ID: {m['id']})"
            else:
                team1 = next((t for t in teams if t["id"] == m["team1_id"]), {"team_name": "Unknown"})
                team2 = next((t for t in teams if t["id"] == m["team2_id"]), {"team_name": "Unknown"})
                desc = f"{m['sport']}: {team1['team_name']} vs {team2['team_name']} (Match ID: {m['id']})"
            cancel_options[desc] = m["id"]
        selected_cancel = st.selectbox("Select a match to cancel", list(cancel_options.keys()))
        cancel_match_id = cancel_options[selected_cancel]
        if st.button("Cancel Scheduled Match"):
            delete_scheduled_match(cancel_match_id)
            st.success(f"Match {cancel_match_id} canceled successfully.")

elif menu == "Submit Scores":
    st.header("Submit Match Scores")
    
    # Retrieve scheduled matches from the database
    matches = get_scheduled_matches()
    
    if not matches:
        st.info("There are no scheduled matches at the moment.")
    else:
        # Create a dictionary mapping a descriptive key to the match record
        match_options = {}
        teams_all = get_all_teams()  # Cache team list for efficiency
        for m in matches:
            team1 = next((t for t in teams_all if t["id"] == m["team1_id"]), {"team_name": "Unknown"})
            team2 = next((t for t in teams_all if t["id"] == m["team2_id"]), {"team_name": "Unknown"})
            desc = f"{m['sport']}: {team1['team_name']} vs {team2['team_name']} (ID: {m['id']})"
            match_options[desc] = m["id"]

        selected_desc = st.selectbox("Select a Scheduled Match", list(match_options.keys()))
        match_id = match_options[selected_desc]
        selected_match = next((m for m in matches if m["id"] == match_id), None)

        if selected_match:
            # Retrieve game definition to determine type and point value
            game_info = get_game_by_name(selected_match["sport"])
            if not game_info:
                st.error("Game definition not found!")
            elif game_info["type"] == "Multi Play":
                st.write("**Match Details:**")
                # Retrieve team details
                team1 = next((t for t in teams_all if t["id"] == selected_match["team1_id"]), {"team_name": "Unknown"})
                team2 = next((t for t in teams_all if t["id"] == selected_match["team2_id"]), {"team_name": "Unknown"})
                st.write(f"Sport: {selected_match['sport']}")
                st.write(f"Team 1: {team1['team_name']} | Handicap:",
                         selected_match['handicap1'][0] if selected_match['handicap1'] else "None")
                st.write(f"Team 2: {team2['team_name']} | Handicap:",
                         selected_match['handicap2'][0] if selected_match['handicap2'] else "None")
                col1, col2 = st.columns(2)
                with col1:
                    team1_score = st.number_input(f"{team1['team_name']} Score", min_value=0, step=1)
                with col2:
                    team2_score = st.number_input(f"{team2['team_name']} Score", min_value=0, step=1)

                if st.button("Submit Scores for Match"):
                    sport = selected_match["sport"]
                    # Award points based on game points (not raw score)
                    if team1_score > team2_score:
                        tokens_team1 = get_team_tokens(team1["id"])
                        if tokens_team1.get("Comeback", 0) > 0:
                            points_awarded = 2 * game_info["points"]
                            update_team_token(team1["id"], "Comeback", tokens_team1.get("Comeback", 0) - 1)
                            st.info(f"{team1['team_name']} used a Comeback token for double points!")
                        else:
                            points_awarded = game_info["points"]
                        new_score = (team1["Score"] or 0) + points_awarded
                        update_team_score(team1["id"], new_score)
                    elif team2_score > team1_score:
                        tokens_team2 = get_team_tokens(team2["id"])
                        if tokens_team2.get("Comeback", 0) > 0:
                            points_awarded = 2 * game_info["points"]
                            update_team_token(team2["id"], "Comeback", tokens_team2.get("Comeback", 0) - 1)
                            st.info(f"{team2['team_name']} used a Comeback token for double points!")
                        else:
                            points_awarded = game_info["points"]
                        new_score = (team2["Score"] or 0) + points_awarded
                        update_team_score(team2["id"], new_score)
                    
                    # Increase games played for both teams.
                    update_team_field(team1["id"], "Games_played", (team1["Games_played"] or 0) + 1)
                    update_team_field(team2["id"], "Games_played", (team2["Games_played"] or 0) + 1)
                    
                    # Update win streaks and award other tokens.
                    if team1_score > team2_score:
                        new_win_streak_team1 = get_team_win_streak(team1["id"], sport) + 1
                        set_team_win_streak(team1["id"], sport, new_win_streak_team1)
                        set_team_win_streak(team2["id"], sport, 0)
                        if new_win_streak_team1 == 3:
                            tokens = get_team_tokens(team1["id"])
                            new_wizard = tokens.get("Wizard", 0) + 1
                            update_team_token(team1["id"], "Wizard", new_wizard)
                        margin = team1_score - team2_score
                        if margin <= 2:
                            overtime = team2.get("Overtime_Games_Lost") or 0
                            overtime += 1
                            update_team_field(team2["id"], "Overtime_Games_Lost", overtime)
                            if overtime >= 2:
                                tokens = get_team_tokens(team2["id"])
                                new_duel = tokens.get("Duel", 0) + 1
                                update_team_token(team2["id"], "Duel", new_duel)
                                update_team_field(team2["id"], "Overtime_Games_Lost", 0)
                        if team2_score == 0:
                            tokens = get_team_tokens(team2["id"])
                            new_peasant = tokens.get("Peasant", 0) + 1
                            update_team_token(team2["id"], "Peasant", new_peasant)
                        lose_streak_team2 = team2.get("Lose_Streak") or 0
                        lose_streak_team2 += 1
                        update_team_field(team2["id"], "Lose_Streak", lose_streak_team2)
                        if lose_streak_team2 >= 3:
                            tokens = get_team_tokens(team2["id"])
                            new_comeback = tokens.get("Comeback", 0) + 1
                            update_team_token(team2["id"], "Comeback", new_comeback)
                            update_team_field(team2["id"], "Lose_Streak", 0)
                    elif team2_score > team1_score:
                        new_win_streak_team2 = get_team_win_streak(team2["id"], sport) + 1
                        set_team_win_streak(team2["id"], sport, new_win_streak_team2)
                        set_team_win_streak(team1["id"], sport, 0)
                        if new_win_streak_team2 == 3:
                            tokens = get_team_tokens(team2["id"])
                            new_wizard = tokens.get("Wizard", 0) + 1
                            update_team_token(team2["id"], "Wizard", new_wizard)
                        margin = team2_score - team1_score
                        if margin <= 2:
                            overtime = team1.get("Overtime_Games_Lost") or 0
                            overtime += 1
                            update_team_field(team1["id"], "Overtime_Games_Lost", overtime)
                            if overtime >= 2:
                                tokens = get_team_tokens(team1["id"])
                                new_duel = tokens.get("Duel", 0) + 1
                                update_team_token(team1["id"], "Duel", new_duel)
                                update_team_field(team1["id"], "Overtime_Games_Lost", 0)
                        if team1_score == 0:
                            tokens = get_team_tokens(team1["id"])
                            new_peasant = tokens.get("Peasant", 0) + 1
                            update_team_token(team1["id"], "Peasant", new_peasant)
                        lose_streak_team1 = team1.get("Lose_Streak") or 0
                        lose_streak_team1 += 1
                        update_team_field(team1["id"], "Lose_Streak", lose_streak_team1)
                        if lose_streak_team1 >= 3:
                            tokens = get_team_tokens(team1["id"])
                            new_comeback = tokens.get("Comeback", 0) + 1
                            update_team_token(team1["id"], "Comeback", new_comeback)
                            update_team_field(team1["id"], "Lose_Streak", 0)
                    
                    # Insert completed match into PastGames table.
                    insert_past_game(sport, team1["team_name"], team2["team_name"], team1_score, team2_score)
                    
                    # Remove the match from the ScheduledMatches table.
                    delete_scheduled_match(selected_match["id"])
                    
                    st.success("Match scores submitted, tokens updated, win streak updated, match cleared, and record saved to past games!")
            
            elif game_info["type"] == "Single Play":
                if selected_match["sport"] == "Mini Golf":
                    st.subheader("Mini Golf Score Submission")
                    # Hardcoded list of individuals (winners)
                    players = ["Cassidy", "Brian", "Sydney", "Zach", "Nick", "Alex", "Diya", "Brendan", "Anwesh", "Dane"]
                    first_place = st.selectbox("Select 1st Place", players)
                    second_place = st.selectbox("Select 2nd Place", [p for p in players if p != first_place])
                    third_place = st.selectbox("Select 3rd Place", [p for p in players if p not in [first_place, second_place]])
                    
                    if st.button("Submit Mini Golf Scores"):
                        teams_all = get_all_teams()
                        first_awarded = False
                        second_awarded = False
                        third_awarded = False
                        for team in teams_all:
                            points_to_add = 0
                            # Check if the individual's name appears in the team's name.
                            # Since team names are in the format "Anwesh-Dane", the team can earn multiple awards.
                            if first_place in team["team_name"]:
                                points_to_add += 60
                            if second_place in team["team_name"]:
                                points_to_add += 35
                            if third_place in team["team_name"]:
                                points_to_add += 20
                            if points_to_add > 0:
                                current_score = team.get("Score") or 0
                                update_team_score(team["id"], current_score + points_to_add)
                                # Increase Games_played only once per team.
                                update_team_field(team["id"], "Games_played", (team["Games_played"] or 0) + 1)

                        # Log the result in the PastGames table (you can adjust how you want to record three placements)
                        # Here we combine first and second place into the "team1" field and put third place in "team2" for reference.
                        insert_past_game(selected_match["sport"], f"1st: {first_place}, 2nd: {second_place}", f"3rd: {third_place}", 60, 35)
                        delete_scheduled_match(selected_match["id"])
                        st.success("Mini Golf scores submitted, points awarded, and record saved to past games!")
                else:
                    st.subheader("Single Play Score Submission")
                    teams_all = get_all_teams()  # Refresh team list if needed
                    first_place = st.selectbox("Select 1st Place Team", [team["team_name"] for team in teams_all])
                    second_place = st.selectbox("Select 2nd Place Team", [team["team_name"] for team in teams_all if team["team_name"] != first_place])
                    if st.button("Submit Single Play Scores"):
                        team1 = next((t for t in teams_all if t["team_name"] == first_place), None)
                        team2 = next((t for t in teams_all if t["team_name"] == second_place), None)
                        if team1 and team2:
                            points_first = game_info["points"]
                            points_second = int(0.5 * game_info["points"])
                            update_team_score(team1["id"], (team1["Score"] or 0) + points_first)
                            update_team_score(team2["id"], (team2["Score"] or 0) + points_second)
                            update_team_field(team1["id"], "Games_played", (team1["Games_played"] or 0) + 1)
                            update_team_field(team2["id"], "Games_played", (team2["Games_played"] or 0) + 1)
                            insert_past_game(selected_match["sport"], team1["team_name"], team2["team_name"], points_first, points_second)
                            delete_scheduled_match(selected_match["id"])
                            st.success("Single play scores submitted, points awarded, and record saved to past games!")
                        else:
                            st.error("Error: Could not find selected teams.")

elif menu == "Non-Game Rules":
    st.header("Non-Game Rules")
    
    # Retrieve all current non-game rules
    rules = get_all_non_game_rules()  # Returns a list of rules
    if rules:
        st.subheader("Current Rules:")
        for rule in rules:
            st.write(f"**Rule:** {rule['rule']}  —  **Penalty:** {rule['penalty']}")
    else:
        st.info("No non-game rules set.")
    
    st.markdown("---")
    st.subheader("Add a New Non-Game Rule")
    new_rule = st.text_input("Enter a new non-game rule")
    new_penalty = st.number_input("Penalty points for breaking the rule", step=1)
    
    # Determine eligible teams:
    # - Teams with a "Peasant" token are eligible to add a rule.
    # - If none have a Peasant token, then eligible teams are those with king = True.
    teams = get_all_teams()
    eligible_teams = []
    for team in teams:
        tokens = get_team_tokens(team["id"])
        if tokens.get("Peasant", 0) > 0:
            eligible_teams.append(team)
    if not eligible_teams:
        eligible_teams = [team for team in teams if team.get("king")]
    
    if eligible_teams:
        team_options = {team["team_name"]: team for team in eligible_teams}
        selected_team_name = st.selectbox("Select Team to Add Rule", list(team_options.keys()))
        selected_team = team_options[selected_team_name]
    else:
        st.warning("No eligible teams available to add a rule.")
        selected_team = None

    if st.button("Add Rule"):
        if not new_rule:
            st.error("Please enter a valid rule.")
        elif selected_team is None:
            st.error("No eligible team selected to add the rule.")
        else:
            tokens = get_team_tokens(selected_team["id"])
            if tokens.get("Peasant", 0) > 0:
                new_count = tokens.get("Peasant", 0) - 1
                update_team_token(selected_team["id"], "Peasant", new_count)
                st.info(f"{selected_team['team_name']} used a Peasant token to add the rule.")
            else:
                st.info(f"{selected_team['team_name']} (King) added the rule.")
            set_non_game_rule(new_rule, new_penalty)
            st.success("Non-game rule added!")
    
    st.markdown("---")
    st.subheader("Log a Rule Break")
    # Allow user to choose which rule was broken
    if rules:
        rule_options = {f"{rule['rule']} (Penalty: {rule['penalty']})": rule for rule in rules}
        selected_rule_desc = st.selectbox("Select the rule that was broken", list(rule_options.keys()))
        selected_rule = rule_options[selected_rule_desc]
    else:
        selected_rule = None

    # List all teams for selection
    if teams:
        team_options = {team["team_name"]: team for team in teams}
        selected_team_name = st.selectbox("Select the team that broke the rule", list(team_options.keys()))
        rule_break_team = team_options[selected_team_name]
    else:
        rule_break_team = None

    if st.button("Log Rule Break"):
        if selected_rule is None or rule_break_team is None:
            st.error("Please select both a rule and a team.")
        else:
            penalty = selected_rule["penalty"]
            current_score = rule_break_team.get("Score") or 0
            new_score = current_score - penalty
            update_team_score(rule_break_team["id"], new_score)
            st.success(f"Logged rule break: {rule_break_team['team_name']}'s score deducted by {penalty} points.")

elif menu == "Leave Location":
    st.header("Leave Current Location")
    if st.button("Leave Location"):
        teams = get_all_teams()
        sorted_teams = sorted(teams, key=lambda t: t["Score"] or 0, reverse=True)
        if sorted_teams:
            new_king = sorted_teams[0]  # Only the top team becomes king.
            for team in teams:
                is_king = (team["id"] == new_king["id"])
                update_team_field(team["id"], "king", is_king)
            # Reset non-game rules upon leaving location.
            reset_non_game_rules()
            st.success(f"Location left. New King is: {new_king['team_name']}. Non-game rules have been reset.")
        else:
            st.warning("No teams found to determine King.")

elif menu == "Token Management":
    st.header("Token Management")
    tokens_found = False
    teams = get_all_teams()
    # Loop over each team and retrieve its tokens from the database.
    # Exclude the "Comeback" token since that is auto‐applied.
    for team in teams:
        team_tokens = get_team_tokens(team["id"])
        # Filter out "Comeback" tokens
        filtered_tokens = {k: v for k, v in team_tokens.items() if k != "Comeback" and v > 0}
        if filtered_tokens:
            tokens_found = True
            st.subheader(f"Team: {team['team_name']} (ID: {team['id']})")
            for token_name, count in filtered_tokens.items():
                st.write(f"**{token_name}:** {count} available")
                token_info = token_definitions.get(token_name, {})
                st.write(f"**Benefit:** {token_info.get('benefit', 'No benefit info available')}")
                # For Duel token, schedule a duel match instead of direct usage.
                if token_name == "Duel":
                    if st.button(f"Use {token_name} for {team['team_name']}", key=f"use_{token_name}_{team['id']}"):
                        # Deduct one Duel token.
                        new_count = count - 1
                        update_team_token(team["id"], token_name, new_count)
                        # Retrieve current king (team with king == True)
                        all_teams = get_all_teams()
                        kings = [t for t in all_teams if t.get("king")]
                        if not kings:
                            st.error("No current king available for a duel.")
                        else:
                            current_king = kings[0]
                            # Schedule a Duel match (Single Play type) with 5 points.
                            duel_match_id = insert_scheduled_match("Duel", current_king["id"], team["id"], [], [])
                            st.success(f"Duel scheduled! (Match ID: {duel_match_id})")
                else:
                    if st.button(f"Use {token_name} for {team['team_name']}", key=f"use_{token_name}_{team['id']}"):
                        new_count = count - 1
                        update_team_token(team["id"], token_name, new_count)
                        st.success(f"Used {token_name} for {team['team_name']}.")
            st.markdown("---")
    if not tokens_found:
        st.info("No tokens available for any team.")
    st.subheader("Token Definitions")
    for token_name, info in token_definitions.items():
        st.write(f"**{token_name}**")
        st.write(f"**How to Earn:** {info.get('earn', '')}")
        st.write(f"**Benefit:** {info.get('benefit', '')}")
        st.markdown("---")

# ------------------- Available Games -------------------
elif menu == "Available Games":
    st.header("Available Games")
    st.subheader("Add New Game")
    new_game_name = st.text_input("Game Name")
    new_game_points = st.number_input("Points", min_value=0, step=1)
    new_game_type = st.text_input("Game Type (e.g., Multi Play)")
    new_handicap1 = st.text_input("Handicap Level 1")
    new_handicap2 = st.text_input("Handicap Level 2")
    new_handicap3 = st.text_input("Handicap Level 3")
    new_handicap4 = st.text_input("Handicap Level 4")
    if st.button("Add Game"):
        if new_game_name and new_game_points and new_game_type and new_handicap1 and new_handicap2 and new_handicap3 and new_handicap4:
            new_game_id = insert_game(new_game_name, new_game_points, new_game_type,
                                       new_handicap1, new_handicap2, new_handicap3, new_handicap4)
            st.success(f"Game '{new_game_name}' added successfully with ID {new_game_id}!")
        else:
            st.error("Please fill in all fields.")

    st.subheader("Existing Games")
    all_games = get_all_games()
    if all_games:
        for game in all_games:
            st.write(f"**{game['name']}** - Points: {game['points']}, Type: {game['type']}")
            st.write("Handicaps:", game["handicap1"], "|", game["handicap2"], "|", game["handicap3"], "|", game["handicap4"])
            st.markdown("---")
    else:
        st.info("No games found.")

if menu == "Rules":
    st.header("Rules")
    
    st.subheader("Teams")
    st.markdown("""
    - **Cassidy and Brian**  
    - **Sydney and Zach**  
    - **Nick and Alex**  
    - **Diya and Brendan**  
    - **Anwesh and Dane**
    """)
    
    st.subheader("Times")
    st.markdown("""
    - **Opening Ceremony:** 12pm  
      **Location:** 380 River St
    - **Lunch and games:** 2pm  
      **Location:** Craft Food Hall
    - **Arcade Games:** 4pm  
      **Game Underground**
    - **Dinner and Pickleball:** 6pm  
      **Location:** PKL
    - **Mini Golf:** 9pm  
      **Location:** Puttshack
    """)
    
    st.subheader("Potential Games")
    st.markdown("""
    Multi play means we’ll schedule as many games as we can but everyone might not play the same amount of games, and you get points for each game.  
    Single Play means everyone will get a chance and there will be a 1st place and 2nd place for the 2 highest scores. For air hockey (singles only), we’ll alternate team members per point.
    """)
    
    st.markdown("""
    | Game                  | Mode & Points                                                       |
    |-----------------------|---------------------------------------------------------------------|
    | Pool                  | Multi Play - 25 per win                                               |
    | Table Tennis          | Multi Play - 15 per win                                               |
    | Shuffleboard          | Multi Play - 15 per win                                               |
    | Foosball              | Multi Play - 15 per win                                               |
    | Pickleball            | Multi Play - 25 per win                                               |
    | Air Hockey (Singles)  | Multi Play - 15 per win                                               |
    | Pinball (Duos)        | Single Play - Duos! 40 for 1st (overall), 20 for 2nd                    |
    | Arcade Basketball     | Single Play - Duos! 40 for 1st (overall), 20 for 2nd                    |
    | Beer Pong             | Multi Play - 25                                                       |
    | Spikeball             | Multi Play - 15 per win                                               |
    | Kanjam                | Multi Play - 15 per win                                               |
    | Mini Golf             | Single Play - Individual event, 60 for 1st, 35 for 2nd, 20 for 3rd       |
    """)
    
    st.subheader("Handicaps")
    st.markdown("Every time you win a multi play game once, you get a handicap from the list below. There are 4 levels per game and you receive level 1 after 1 win and level 2 after 2 wins. They can be cumulative if mentioned.")
    
    st.markdown("##### Pool")
    st.markdown("""
    - Be on one leg when you play your shot  
    - 1 + must call pocket before taking shot and it doesn’t count  
    - Play with non dominant hands  
    - 1 + 2 + 3  
    """)
    
    st.markdown("##### Table Tennis")
    st.markdown("""
    - Can only use one side of your paddle  
    - Play with non dominant hands  
    - 1 + 2  
    - Play with your phones  
    """)
    
    st.markdown("##### Shuffleboard")
    st.markdown("""
    - Play with non dominant hands  
    - Play with 3 pucks instead of 4  
    - 1 + 2  
    - Play with 2 pucks  
    """)
    
    st.markdown("##### Foosball")
    st.markdown("""
    - Play with 1 hand only  
    - Goalie is injured  
    - Play with non-dominant hands only  
    - 2 + 3  
    """)
    
    st.markdown("##### Spikeball")
    st.markdown("""
    - Must spin twice before every serve  
    - Can never leave the ground with both feet  
    - Non dominant hands only  
    - 1 + 2 + 3  
    """)
    
    st.markdown("##### Pickleball")
    st.markdown("""
    - Have to start grunting on every shot  
    - 1 + Opponent gets a second serve  
    - Play with non dominant hands  
    - 1 + 2 + 3  
    """)
    
    st.markdown("##### Air Hockey")
    st.markdown("""
    - 1 foot per point  
    - Non dominant hands only  
    - 1 + 2  
    - Upside down paddle  
    """)
    
    st.markdown("##### Beer Pong")
    st.markdown("""
    - Opponent gets a free rack  
    - 1 + Throw on one foot  
    - Play with non dominant hand  
    - 1 + 2 + 3  
    """)
    
    st.markdown("##### Kanjam")
    st.markdown("""
    - Non dominant hand for slammer  
    - Non dominant hand for thrower  
    - 1 + 2  
    - 2 points per 3 pointer  
    - No handicaps for single play games  
    """)
    
    st.subheader("King and Queen")
    st.markdown("""
    - Every time you leave a location, the team on top of the scores table becomes King and Queen (a location can have multiple games)  
    - King and Queen get to make a non-game related rule; breaking this can incur a 1 or 2 point penalty depending on the rule.  
    - King and Queen play the next game they’re scheduled for with the 1st level handicap of that game.  
    """)
    
    st.subheader("Tokens")
    st.markdown("##### Duel Token")
    st.markdown("""
    - **How to Earn:** A team gets a duel token if they reach overtime in a game 2 times. (Overtime is defined as losing a game by 2 points or less.)  
    - **Benefit:** Challenge the current kings and queens to any reasonable duel. Powers transfer instantly. The winning team gets 5 points from the other team and makes a new non-game rule.
    """)
    
    st.markdown("##### Peasant Token")
    st.markdown("""
    - **How to Earn:** Lose a game without earning a point.  
    - **Benefit:** Get to add a non-game rule.
    """)
    
    st.markdown("##### Comeback Token")
    st.markdown("""
    - **How to Earn:** Lose 3 consecutive games.  
    - **Benefit:** Your next win earns you double points.
    """)
    
    st.markdown("##### Wizard Token")
    st.markdown("""
    - **How to Earn:** Win a game with a level 3 handicap.  
    - **Benefit:** Immunity from King’s rules for the current King.
    """)
    
    st.subheader("Non Game Rules")
    st.markdown("""
    - Can be made by current Kings and Queens.  
    - Can also be made by a team using a Peasant Token.  
    - Resets after every location.
    """)

# ------------------- Admin Panel -------------------
elif menu == "Admin Panel":
    st.header("Admin Panel")
    admin_password = st.text_input("Enter Admin Password", type="password")
    if st.button("Clear Database"):
        if admin_password == "coldpalm":
            clear_database()
            st.success("Database cleared successfully!")
        else:
            st.error("Incorrect password. Database not cleared.")
    st.markdown("---")
    if st.button("Reset Teams Stats"):
        if admin_password == "coldpalm":
            reset_teams_stats()
            st.success("Teams table stats have been reset successfully!")
        else:
            st.error("Incorrect password. Teams stats not reset.")
    st.markdown("---")
    st.header("Override Team Points")
    teams = get_all_teams()
    team_options = {team["team_name"]: team for team in teams}
    team_name = st.selectbox("Select Team", list(team_options.keys()), key="override_team")
    adjustment = st.number_input("Adjustment (negative to remove points)", step=1)
    if st.button("Apply Override"):
        if admin_password == "coldpalm":
            team = team_options[team_name]
            new_score = (team["Score"] or 0) + adjustment
            update_team_score(team["id"], new_score)
            st.success(f"{team_name}'s score updated to {new_score}.")
        else:
            st.error("Incorrect password. Cannot override points.")
