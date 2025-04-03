# games_data.py
# This file stores game definitions including point values and handicap levels.

games = {
    "Pool": {
        "points": 25,
        "type": "Multi Play",
        "handicaps": [
            "Be on one leg when you play your shot",             # Level 1
            "Must call pocket before taking shot and it doesn’t count",  # Level 2
            "Play with non dominant hands",                      # Level 3
            "Cumulative: 1 + 2 + 3"                                # Level 4
        ]
    },
    "Table Tennis": {
        "points": 15,
        "type": "Multi Play",
        "handicaps": [
            "Can only use one side of your paddle",              # Level 1
            "Play with non dominant hands",                      # Level 2
            "Play with your phones",                             # Level 3
            "Cumulative: 1 + 2"                                  # Level 4
        ]
    },
    "Shuffleboard": {
        "points": 15,
        "type": "Multi Play",
        "handicaps": [
            "Play with non dominant hands",                      # Level 1
            "Play with 3 pucks instead of 4",                    # Level 2
            "Play with 2 pucks",                                 # Level 3
            "Cumulative: 1 + 2"                                  # Level 4
        ]
    },
    "Foosball": {
        "points": 15,
        "type": "Multi Play",
        "handicaps": [
            "Play with 1 hand only",                             # Level 1
            "Goalie is injured",                                 # Level 2
            "Play with non-dominant hands only",                 # Level 3
            "Cumulative: 2 + 3"                                  # Level 4
        ]
    },
    "Spikeball": {
        "points": 15,
        "type": "Multi Play",
        "handicaps": [
            "Must spin before every serve",                    # Level 1
            "Can never leave the ground with both feet",       # Level 2
            "Non dominant hands only",                         # Level 3
            "Cumulative: 1 + 2 + 3"                              # Level 4
        ]
    },
    "Pickleball": {
        "points": 25,
        "type": "Multi Play",
        "handicaps": [
            "Have to start grunting on every shot",            # Level 1
            "Opponent gets a second serve",                    # Level 2
            "Play with non dominant hands",                    # Level 3
            "Cumulative: 1 + 2 + 3"                             # Level 4
        ]
    },
    "Air Hockey": {
        "points": 15,
        "type": "Multi Play",
        "handicaps": [
            "1 foot per point",                                # Level 1
            "Non dominant hands only",                         # Level 2
            "Upside down paddle",                              # Level 3
            "Cumulative: 1 + 2"                                 # Level 4
        ]
    },
    "Beer Pong": {
        "points": 25,
        "type": "Multi Play",
        "handicaps": [
            "Opponents gets a free rack",                      # Level 1
            "Throw on one foot",                               # Level 2
            "Play with non dominant hand",                     # Level 3
            "Cumulative: 1 + 2 + 3"                             # Level 4
        ]
    },
    "Kanjam": {
        "points": 15,
        "type": "Multi Play",
        "handicaps": [
            "Non dominant hand for slammer",                 # Level 1
            "Non dominant hand for thrower",                 # Level 2
            "2 points per 3 pointer",                        # Level 3
            "Cumulative: 1 + 2"                              # Level 4
        ]
    },
}