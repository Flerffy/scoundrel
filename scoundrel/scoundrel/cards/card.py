class Card:
    def __init__(self, card_type, value):
        self.card_type = card_type
        self.value = value

    def get_value(self):
        return self.value

    def get_type(self):
        return self.card_type

    def __str__(self):
        return f"{self.card_type} Card: {self.value} points"