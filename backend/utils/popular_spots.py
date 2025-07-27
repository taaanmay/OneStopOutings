class PopularSpots:
    spots = {
        "Museum": [
            {"type": "Museum", "name": "National Museum of Ireland - Archaeology", "cost": 0, "duration": 90},
            {"type": "Museum", "name": "National Gallery of Ireland", "cost": 0, "duration": 120},
            {"type": "Museum", "name": "Irish Museum of Modern Art (IMMA)", "cost": 0, "duration": 120},
            {"type": "Museum", "name": "EPIC The Irish Emigration Museum", "cost": 21, "duration": 90},
            {"type": "Museum", "name": "Dublinia", "cost": 15, "duration": 90},
            {"type": "Museum", "name": "Little Museum of Dublin", "cost": 15, "duration": 60},
            # --- New from logs ---
            {"type": "Museum", "name": "Kilmainham Gaol Museum", "cost": 8, "duration": 180},
            {"type": "Museum", "name": "Kilmainham Gaol", "cost": 8, "duration": 120},
        ],
        "Activity": [
            {"type": "Activity", "name": "Guinness Storehouse", "cost": 30, "duration": 150},
            {"type": "Activity", "name": "Trinity College & Book of Kells", "cost": 18, "duration": 90},
            {"type": "Activity", "name": "Dublin Castle", "cost": 8, "duration": 90},
            {"type": "Activity", "name": "Kilmainham Gaol", "cost": 8, "duration": 90},
            {"type": "Activity", "name": "St. Patrick's Cathedral", "cost": 9, "duration": 60},
            {"type": "Activity", "name": "Phoenix Park Walk", "cost": 0, "duration": 120},
            # --- New from logs ---
            {"type": "Activity", "name": "Marsh's Library", "cost": 5, "duration": 90},
            {"type": "Activity", "name": "Grafton Street Shopping", "cost": 0, "duration": 180},
            {"type": "Activity", "name": "Shopping at Brown Thomas", "cost": 200, "duration": 180},
            {"type": "Activity", "name": "Explore Grafton Street Shopping", "cost": 0, "duration": 120},
            {"type": "Activity", "name": "St. Stephen's Green Park", "cost": 0, "duration": 90},
            {"type": "Activity", "name": "Hugh Lane Gallery", "cost": 0, "duration": 120},
            {"type": "Activity", "name": "Designer Exchange", "cost": 0, "duration": 180},
        ],
        "Food": [
            {"type": "Lunch", "name": "Boojum (Burritos)", "cost": 12, "duration": 60},
            {"type": "Lunch", "name": "Bunsen (Burgers)", "cost": 15, "duration": 60},
            {"type": "Dinner", "name": "The Winding Stair (Irish)", "cost": 60, "duration": 120},
            {"type": "Dinner", "name": "Pi Pizza", "cost": 20, "duration": 75},
            {"type": "Breakfast", "name": "The Fumbally", "cost": 18, "duration": 60},
            {"type": "Treat", "name": "Murphy's Ice Cream", "cost": 5, "duration": 20},
            # --- New from logs ---
            {"type": "Food Tour", "name": "Dublin Delicious Food Tour", "cost": 85, "duration": 180},
            {"type": "Dinner", "name": "The Winding Stair", "cost": 120, "duration": 90},
            {"type": "Lunch", "name": "Fallon & Byrne", "cost": 50, "duration": 90},
            {"type": "Lunch", "name": "Leo Burdock's Fish and Chips", "cost": 20, "duration": 60},
            {"type": "Breakfast", "name": "Brother Hubbard North", "cost": 25, "duration": 60},
            {"type": "Lunch", "name": "Loose Canon Cheese and Wine", "cost": 40, "duration": 90},
            {"type": "Dinner", "name": "Etto", "cost": 75, "duration": 90},
            {"type": "Breakfast", "name": "Gertrude", "cost": 15, "duration": 60},
            {"type": "Lunch", "name": "Eatyard", "cost": 20, "duration": 90},
            {"type": "Food", "name": "Token", "cost": 15, "duration": 60},
            {"type": "Food Experience", "name": "Chapter One: A Literary Gastronomic Journey", "cost": 120, "duration": 180},
            {"type": "Food", "name": "Teeling Whiskey Distillery Tour", "cost": 20, "duration": 90},
            {"type": "Food Experience", "name": "Dublin Food Surprises - Secret Food Tour", "cost": 85, "duration": 180},
            {"type": "Food Experience", "name": "Viking Splash Tours - Duck Boat City & Food Tour Combo", "cost": 35, "duration": 120},
        ],
        "Pub": [
            {"type": "Pub", "name": "The Temple Bar Pub", "cost": 20, "duration": 90},
            {"type": "Pub", "name": "The Brazen Head", "cost": 15, "duration": 90},
            {"type": "Pub", "name": "Kehoe's Pub", "cost": 15, "duration": 90},
            {"type": "Pub", "name": "The Long Hall", "cost": 15, "duration": 90},
            {"type": "Pub", "name": "Palace Bar", "cost": 15, "duration": 90},
        ],
        # --- New Categories and Items from logs ---
        "Shopping": [
            {"type": "Morning", "name": "Designer Exchange (Luxury Resale)", "cost": 250, "duration": 120},
            {"type": "Afternoon", "name": "Jenny Vander Vintage", "cost": 30, "duration": 90},
            {"type": "Shopping", "name": "Dublin Flea Market", "cost": 0, "duration": 120},
            {"type": "Shopping", "name": "Dublin Vintage Factory", "cost": 30, "duration": 120},
            {"type": "Shopping", "name": "Jam Art Factory", "cost": 25, "duration": 120},
        ],
        "Entertainment": [
            {"type": "Dinner & Show", "name": "The Brazen Head (Traditional Irish Music)", "cost": 70, "duration": 180},
            {"type": "Evening Entertainment", "name": "The Cobblestone", "cost": 15, "duration": 120},
        ],
        "Landmark": [
             {"type": "Landmark", "name": "Kilmainham Gaol", "cost": 8, "duration": 120},
        ],
        "Historical Site": [
            {"type": "Historical Site", "name": "Trinity College & The Book of Kells", "cost": 18, "duration": 120},
        ]
    }
