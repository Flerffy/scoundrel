import json
import os

class Persistence:
    def __init__(self, filename='data/scores.json'):
        self.filename = filename
        self.data = self.load_data()

    def load_data(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                return json.load(file)
        return {'high_score': 0, 'games_played': 0}

    def save_data(self):
        with open(self.filename, 'w') as file:
            json.dump(self.data, file)

    def update_high_score(self, score):
        if score > self.data['high_score']:
            self.data['high_score'] = score
            self.save_data()

    def increment_games_played(self):
        self.data['games_played'] += 1
        self.save_data()