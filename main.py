from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
import random

# --- Game Data Structures ---

class Spell:
    def __init__(self, name, damage, cost):
        self.name = name
        self.damage = damage
        self.cost = cost

class Witch:
    def __init__(self, name, rarity, ultimate_spell):
        self.name = name
        self.rarity = rarity
        self.bond = 0
        self.ultimate_spell = ultimate_spell
        self.spell_unlocked = False

# Database of all possible summons
DATABASE = {
    "Witches": [
        Witch("Chloe (1 Star)", 1, Spell("Fireball", 15, 2)),
        Witch("Sam (2 Star)", 2, Spell("Shadow Strike", 30, 3)),
        Witch("Lilith (3 Star)", 3, Spell("Obliterate", 100, 5))
    ],
    "Spells": [
        Spell("Zap", 5, 1),
        Spell("Punch", 10, 1),
        Spell("Magic Missile", 20, 2)
    ]
}

# Player State
class PlayerState:
    def __init__(self):
        self.currency = 500
        self.witches = []
        self.deck = [Spell("Basic Strike", 5, 1), Spell("Basic Strike", 5, 1)]

player = PlayerState()

# --- Screens ---

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(text="URBAN LEGEND DECKBUILDER", font_size=30))
        
        btn_gacha = Button(text="Summoning Circle (Gacha)", size_hint=(1, 0.2))
        btn_gacha.bind(on_press=self.go_to_gacha)
        layout.add_widget(btn_gacha)
        
        btn_hangout = Button(text="Hangout (Friendship)", size_hint=(1, 0.2))
        btn_hangout.bind(on_press=self.go_to_hangout)
        layout.add_widget(btn_hangout)
        
        btn_combat = Button(text="Hunt an Urban Legend", size_hint=(1, 0.2))
        btn_combat.bind(on_press=self.go_to_combat)
        layout.add_widget(btn_combat)
        
        self.add_widget(layout)

    def go_to_gacha(self, instance):
        self.manager.current = 'gacha'

    def go_to_hangout(self, instance):
        self.manager.get_screen('hangout').refresh_list()
        self.manager.current = 'hangout'

    def go_to_combat(self, instance):
        self.manager.get_screen('combat').start_combat()
        self.manager.current = 'combat'


class GachaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.status_label = Label(text=f"Currency: {player.currency}\nReady to summon.", font_size=20, halign="center")
        layout.add_widget(self.status_label)
        
        summon_btn = Button(text="Summon (Cost: 100)", size_hint=(1, 0.2))
        summon_btn.bind(on_press=self.summon)
        layout.add_widget(summon_btn)
        
        back_btn = Button(text="Back to Menu", size_hint=(1, 0.2))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def summon(self, instance):
        if player.currency < 100:
            self.status_label.text = f"Currency: {player.currency}\nNot enough currency!"
            return
            
        player.currency -= 100
        
        # 30% chance for a Witch, 70% chance for a Spell
        if random.random() < 0.3:
            pulled = random.choice(DATABASE["Witches"])
            if pulled not in player.witches:
                player.witches.append(pulled)
                self.status_label.text = f"Currency: {player.currency}\nYou summoned a Witch!\n{pulled.name}"
            else:
                self.status_label.text = f"Currency: {player.currency}\nDuplicate Witch {pulled.name}. Gained 50 currency."
                player.currency += 50
        else:
            pulled = random.choice(DATABASE["Spells"])
            player.deck.append(pulled)
            self.status_label.text = f"Currency: {player.currency}\nYou pulled a Spell!\n{pulled.name}"


class HangoutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_list(self):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="Hangout with your Coven", size_hint=(1, 0.2)))
        
        if not player.witches:
            self.layout.add_widget(Label(text="You have no Witches. Go summon some!"))
        else:
            scroll = ScrollView(size_hint=(1, 0.6))
            list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
            list_layout.bind(minimum_height=list_layout.setter('height'))
            
            for witch in player.witches:
                btn_text = f"Talk to {witch.name} (Bond: {witch.bond}/100)"
                btn = Button(text=btn_text, size_hint_y=None, height=100)
                btn.bind(on_press=lambda instance, w=witch: self.talk_to(w))
                list_layout.add_widget(btn)
            
            scroll.add_widget(list_layout)
            self.layout.add_widget(scroll)
            
        back_btn = Button(text="Back to Menu", size_hint=(1, 0.2))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def talk_to(self, witch):
        if witch.bond < 100:
            witch.bond += 25
            if witch.bond >= 100 and not witch.spell_unlocked:
                witch.spell_unlocked = True
                player.deck.append(witch.ultimate_spell)
        self.refresh_list()


class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.enemy_hp = 100
        self.mana = 3
        self.hand = []
        self.add_widget(self.layout)

    def start_combat(self):
        self.enemy_hp = 100
        self.mana = 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()

    def update_ui(self):
        self.layout.clear_widgets()
        
        if self.enemy_hp <= 0:
            self.layout.add_widget(Label(text="YOU WON!\nGained 150 Currency.", font_size=30))
            player.currency += 150
            back_btn = Button(text="Back to Menu", size_hint=(1, 0.2))
            back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
            self.layout.add_widget(back_btn)
            return

        self.layout.add_widget(Label(text=f"Urban Legend HP: {self.enemy_hp}\nYour Mana: {self.mana}", font_size=20))
        
        cards_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.4))
        for spell in self.hand:
            btn = Button(text=f"{spell.name}\nDmg: {spell.damage}\nCost: {spell.cost}")
            btn.bind(on_press=lambda instance, s=spell: self.cast_spell(s))
            cards_layout.add_widget(btn)
            
        self.layout.add_widget(cards_layout)
        
        end_turn_btn = Button(text="End Turn", size_hint=(1, 0.2))
        end_turn_btn.bind(on_press=self.enemy_turn)
        self.layout.add_widget(end_turn_btn)

    def cast_spell(self, spell):
        if self.mana >= spell.cost:
            self.mana -= spell.cost
            self.enemy_hp -= spell.damage
            self.hand.remove(spell)
            self.update_ui()

    def enemy_turn(self, instance):
        # Very simple enemy turn logic
        self.mana = 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()


# --- App Runner ---
class DeckbuilderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(GachaScreen(name='gacha'))
        sm.add_widget(HangoutScreen(name='hangout'))
        sm.add_widget(CombatScreen(name='combat'))
        return sm

if __name__ == '__main__':
    DeckbuilderApp().run()
