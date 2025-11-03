#!/usr/bin/env python3
"""
Scoundrel - A card game built with pygame
Features:
- Score system
- Unlockable card types
- Difficulty settings
"""

import pygame
import random
import json
import os
from enum import Enum


class Difficulty(Enum):
    """Difficulty levels for the game"""
    EASY = 1
    MEDIUM = 2
    HARD = 3


class CardType(Enum):
    """Types of cards available in the game"""
    BASIC = "basic"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class Card:
    """Represents a playing card"""
    
    def __init__(self, card_type, value, name):
        self.card_type = card_type
        self.value = value
        self.name = name
        self.unlocked = card_type == CardType.BASIC  # Basic cards start unlocked
    
    def __repr__(self):
        return f"{self.name} ({self.card_type.value}): {self.value}"


class ScoreSystem:
    """Manages game scoring"""
    
    def __init__(self):
        self.current_score = 0
        self.high_score = 0
        self.games_played = 0
        self.load_scores()
    
    def add_points(self, points):
        """Add points to current score"""
        self.current_score += points
        if self.current_score > self.high_score:
            self.high_score = self.current_score
    
    def reset_current_score(self):
        """Reset the current game score"""
        self.current_score = 0
        self.games_played += 1
    
    def save_scores(self):
        """Save scores to file"""
        data = {
            'high_score': self.high_score,
            'games_played': self.games_played
        }
        try:
            with open('scores.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving scores: {e}")
    
    def load_scores(self):
        """Load scores from file"""
        try:
            if os.path.exists('scores.json'):
                with open('scores.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('high_score', 0)
                    self.games_played = data.get('games_played', 0)
        except Exception as e:
            print(f"Error loading scores: {e}")


class UnlockSystem:
    """Manages unlockable card types"""
    
    def __init__(self, score_system):
        self.score_system = score_system
        self.unlock_thresholds = {
            CardType.BASIC: 0,
            CardType.ADVANCED: 100,
            CardType.EXPERT: 500,
            CardType.MASTER: 1000
        }
    
    def is_unlocked(self, card_type):
        """Check if a card type is unlocked"""
        threshold = self.unlock_thresholds.get(card_type, 0)
        return self.score_system.high_score >= threshold
    
    def get_next_unlock(self):
        """Get the next card type to unlock and points needed"""
        for card_type, threshold in sorted(self.unlock_thresholds.items(), key=lambda x: x[1]):
            if self.score_system.high_score < threshold:
                points_needed = threshold - self.score_system.high_score
                return card_type, points_needed
        return None, 0


class ScoundrelGame:
    """Main game class"""
    
    def __init__(self):
        pygame.init()
        
        # Screen setup
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Scoundrel Card Game")
        
        # Game systems
        self.score_system = ScoreSystem()
        self.unlock_system = UnlockSystem(self.score_system)
        self.difficulty = Difficulty.MEDIUM
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GREEN = (0, 255, 0)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.GRAY = (128, 128, 128)
        self.DARK_GREEN = (0, 128, 0)
        
        # Fonts
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Clock
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game state
        self.state = "menu"  # menu, playing, game_over
        self.deck = []
        self.hand = []
        self.selected_card = None
        
        # Initialize card deck
        self.init_deck()
    
    def init_deck(self):
        """Initialize the card deck"""
        self.deck = []
        
        # Basic cards (always available)
        for i in range(10):
            self.deck.append(Card(CardType.BASIC, random.randint(1, 5), f"Basic {i+1}"))
        
        # Advanced cards
        if self.unlock_system.is_unlocked(CardType.ADVANCED):
            for i in range(5):
                self.deck.append(Card(CardType.ADVANCED, random.randint(5, 10), f"Advanced {i+1}"))
        
        # Expert cards
        if self.unlock_system.is_unlocked(CardType.EXPERT):
            for i in range(3):
                self.deck.append(Card(CardType.EXPERT, random.randint(10, 15), f"Expert {i+1}"))
        
        # Master cards
        if self.unlock_system.is_unlocked(CardType.MASTER):
            for i in range(2):
                self.deck.append(Card(CardType.MASTER, random.randint(15, 20), f"Master {i+1}"))
        
        random.shuffle(self.deck)
    
    def draw_card(self):
        """Draw a card from the deck"""
        if self.deck:
            card = self.deck.pop()
            self.hand.append(card)
            return card
        return None
    
    def play_card(self, card):
        """Play a card from hand"""
        if card in self.hand:
            # Calculate points based on difficulty
            points = card.value
            if self.difficulty == Difficulty.EASY:
                points = int(points * 1.5)
            elif self.difficulty == Difficulty.HARD:
                points = int(points * 0.75)
            
            self.score_system.add_points(points)
            self.hand.remove(card)
            
            # Draw a new card
            self.draw_card()
    
    def draw_menu(self):
        """Draw the main menu"""
        self.screen.fill(self.BLACK)
        
        # Title
        title = self.font_large.render("SCOUNDREL", True, self.GREEN)
        title_rect = title.get_rect(center=(self.width // 2, 100))
        self.screen.blit(title, title_rect)
        
        # High score
        high_score_text = self.font_small.render(f"High Score: {self.score_system.high_score}", True, self.WHITE)
        high_score_rect = high_score_text.get_rect(center=(self.width // 2, 180))
        self.screen.blit(high_score_text, high_score_rect)
        
        # Games played
        games_text = self.font_small.render(f"Games Played: {self.score_system.games_played}", True, self.WHITE)
        games_rect = games_text.get_rect(center=(self.width // 2, 210))
        self.screen.blit(games_text, games_rect)
        
        # Difficulty selection
        diff_text = self.font_medium.render("Difficulty:", True, self.WHITE)
        diff_rect = diff_text.get_rect(center=(self.width // 2, 280))
        self.screen.blit(diff_text, diff_rect)
        
        # Difficulty buttons
        difficulties = [(Difficulty.EASY, "EASY"), (Difficulty.MEDIUM, "MEDIUM"), (Difficulty.HARD, "HARD")]
        y_pos = 330
        for diff, label in difficulties:
            color = self.GREEN if self.difficulty == diff else self.WHITE
            diff_option = self.font_small.render(f"[{label}]", True, color)
            diff_option_rect = diff_option.get_rect(center=(self.width // 2, y_pos))
            self.screen.blit(diff_option, diff_option_rect)
            y_pos += 40
        
        # Unlock status
        unlock_y = 470
        unlock_title = self.font_small.render("Unlocked Card Types:", True, self.WHITE)
        self.screen.blit(unlock_title, (250, unlock_y))
        
        for card_type in CardType:
            unlock_y += 25
            unlocked = self.unlock_system.is_unlocked(card_type)
            color = self.GREEN if unlocked else self.GRAY
            status = "✓" if unlocked else "✗"
            text = self.font_small.render(f"{status} {card_type.value.capitalize()}", True, color)
            self.screen.blit(text, (270, unlock_y))
        
        # Start instruction
        start_text = self.font_medium.render("Press SPACE to Start", True, self.WHITE)
        start_rect = start_text.get_rect(center=(self.width // 2, 570))
        self.screen.blit(start_text, start_rect)
    
    def draw_game(self):
        """Draw the game screen"""
        self.screen.fill(self.DARK_GREEN)
        
        # Score
        score_text = self.font_medium.render(f"Score: {self.score_system.current_score}", True, self.WHITE)
        self.screen.blit(score_text, (20, 20))
        
        # High score
        high_score_text = self.font_small.render(f"High: {self.score_system.high_score}", True, self.WHITE)
        self.screen.blit(high_score_text, (20, 60))
        
        # Difficulty
        diff_text = self.font_small.render(f"Difficulty: {self.difficulty.name}", True, self.WHITE)
        self.screen.blit(diff_text, (self.width - 200, 20))
        
        # Cards remaining
        cards_text = self.font_small.render(f"Deck: {len(self.deck)}", True, self.WHITE)
        self.screen.blit(cards_text, (self.width - 200, 50))
        
        # Draw hand
        if self.hand:
            hand_title = self.font_medium.render("Your Hand:", True, self.WHITE)
            self.screen.blit(hand_title, (50, 150))
            
            y_pos = 200
            for i, card in enumerate(self.hand):
                # Card background
                card_rect = pygame.Rect(50, y_pos, 300, 60)
                color = self.BLUE if card == self.selected_card else self.WHITE
                pygame.draw.rect(self.screen, color, card_rect)
                pygame.draw.rect(self.screen, self.BLACK, card_rect, 2)
                
                # Card text
                card_text = self.font_small.render(f"{card.name}: {card.value} pts", True, self.BLACK)
                self.screen.blit(card_text, (60, y_pos + 10))
                
                type_text = self.font_small.render(f"Type: {card.card_type.value}", True, self.BLACK)
                self.screen.blit(type_text, (60, y_pos + 35))
                
                y_pos += 80
        
        # Instructions
        inst_text = self.font_small.render("Click a card to select, ENTER to play, ESC for menu", True, self.WHITE)
        inst_rect = inst_text.get_rect(center=(self.width // 2, self.height - 30))
        self.screen.blit(inst_text, inst_rect)
    
    def draw_game_over(self):
        """Draw the game over screen"""
        self.screen.fill(self.BLACK)
        
        # Game Over
        game_over = self.font_large.render("GAME OVER", True, self.RED)
        game_over_rect = game_over.get_rect(center=(self.width // 2, 150))
        self.screen.blit(game_over, game_over_rect)
        
        # Final score
        score_text = self.font_medium.render(f"Final Score: {self.score_system.current_score}", True, self.WHITE)
        score_rect = score_text.get_rect(center=(self.width // 2, 250))
        self.screen.blit(score_text, score_rect)
        
        # High score
        if self.score_system.current_score == self.score_system.high_score:
            new_high = self.font_medium.render("NEW HIGH SCORE!", True, self.GREEN)
            new_high_rect = new_high.get_rect(center=(self.width // 2, 300))
            self.screen.blit(new_high, new_high_rect)
        else:
            high_text = self.font_medium.render(f"High Score: {self.score_system.high_score}", True, self.WHITE)
            high_rect = high_text.get_rect(center=(self.width // 2, 300))
            self.screen.blit(high_text, high_rect)
        
        # Check for unlocks
        next_unlock, points_needed = self.unlock_system.get_next_unlock()
        if next_unlock:
            unlock_text = self.font_small.render(
                f"Next unlock: {next_unlock.value.capitalize()} ({points_needed} pts needed)",
                True, self.WHITE
            )
            unlock_rect = unlock_text.get_rect(center=(self.width // 2, 380))
            self.screen.blit(unlock_text, unlock_rect)
        
        # Continue instruction
        continue_text = self.font_medium.render("Press SPACE to continue", True, self.WHITE)
        continue_rect = continue_text.get_rect(center=(self.width // 2, 500))
        self.screen.blit(continue_text, continue_rect)
    
    def start_game(self):
        """Start a new game"""
        self.score_system.reset_current_score()
        self.init_deck()
        self.hand = []
        self.selected_card = None
        
        # Draw initial hand
        for _ in range(min(5, len(self.deck))):
            self.draw_card()
        
        self.state = "playing"
    
    def handle_menu_events(self, event):
        """Handle events in menu state"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.start_game()
            elif event.key == pygame.K_1:
                self.difficulty = Difficulty.EASY
            elif event.key == pygame.K_2:
                self.difficulty = Difficulty.MEDIUM
            elif event.key == pygame.K_3:
                self.difficulty = Difficulty.HARD
    
    def handle_game_events(self, event):
        """Handle events in game state"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "menu"
            elif event.key == pygame.K_RETURN and self.selected_card:
                self.play_card(self.selected_card)
                self.selected_card = None
                
                # Check for game over
                if not self.deck and not self.hand:
                    self.state = "game_over"
                    self.score_system.save_scores()
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            y_pos = 200
            for card in self.hand:
                card_rect = pygame.Rect(50, y_pos, 300, 60)
                if card_rect.collidepoint(mouse_pos):
                    self.selected_card = card
                    break
                y_pos += 80
    
    def handle_game_over_events(self, event):
        """Handle events in game over state"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = "menu"
    
    def run(self):
        """Main game loop"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.state == "menu":
                    self.handle_menu_events(event)
                elif self.state == "playing":
                    self.handle_game_events(event)
                elif self.state == "game_over":
                    self.handle_game_over_events(event)
            
            # Draw
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                self.draw_game()
            elif self.state == "game_over":
                self.draw_game_over()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # Clean up
        self.score_system.save_scores()
        pygame.quit()


def main():
    """Main entry point"""
    game = ScoundrelGame()
    game.run()


if __name__ == "__main__":
    main()
