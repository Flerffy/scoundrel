class Game:
    def __init__(self):
        self.score = 0
        self.high_score = 0
        self.card_types_unlocked = {
            'basic': True,
            'advanced': False,
            'expert': False,
            'master': False
        }
        self.difficulty_multiplier = 1.0

    def update_score(self, points):
        self.score += points
        self.check_unlocks()

    def check_unlocks(self):
        if self.score >= 100 and not self.card_types_unlocked['advanced']:
            self.card_types_unlocked['advanced'] = True
        if self.score >= 500 and not self.card_types_unlocked['expert']:
            self.card_types_unlocked['expert'] = True
        if self.score >= 1000 and not self.card_types_unlocked['master']:
            self.card_types_unlocked['master'] = True

    def reset_game(self):
        self.score = 0

    def set_difficulty(self, difficulty):
        if difficulty == 'easy':
            self.difficulty_multiplier = 1.5
        elif difficulty == 'medium':
            self.difficulty_multiplier = 1.0
        elif difficulty == 'hard':
            self.difficulty_multiplier = 0.75

    def get_score(self):
        return self.score * self.difficulty_multiplier

    def get_high_score(self):
        return self.high_score

    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score