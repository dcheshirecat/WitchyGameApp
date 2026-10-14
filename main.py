from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.animation import Animation
import random

# --- Core Data Structures ---

class Spell:
    def __init__(self, name, damage, cost, spell_type="Nature"):
        self.name = name
        self.damage = damage
        self.cost = cost
        self.spell_type = spell_type # "Nature", "Shadow", "Divine"

class Entity:
    def __init__(self, name, origin, rarity, passive_desc, ultimate_spell):
        self.name = name
        self.origin = origin # "Witch", "Fae", "Angel"
        self.rarity = rarity
        self.passive_desc = passive_desc
        self.ultimate_spell = ultimate_spell
        self.bond = 0

class Enemy:
    def __init__(self, name, hp, weakness, intents):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.weakness = weakness
        self.intents = intents # List of (action_type, value)

# Expanded Summon Database
DATABASE = {
    "Entities": [
        Entity("Chloe (1 Star)", "Witch", 1, "Heals 3 HP on Fire spells", Spell("Fireball", 15, 2, "Nature")),
        Entity("Sam (2 Star)", "Witch", 2, "+10% Shadow damage", Spell("Shadow Strike", 30, 3, "Shadow")),
        Entity("Lilith (3 Star)", "Witch", 3, "Start combat with +1 Mana", Spell("Obliterate", 100, 5, "Shadow")),
        Entity("Puck (1 Star)", "Fae", 1, "Draw +1 card at battle start", Spell("Trickster Spark", 12, 1, "Nature")),
        Entity("The Kelpie (2 Star)", "Fae", 2, "Enemies take 15% more damage", Spell("Drowning Depths", 35, 3, "Nature")),
        Entity("Queen Mab (3 Star)", "Fae", 3, "Steals 1 enemy intent turn", Spell("Nightmare Realm", 75, 4, "Shadow")),
        Entity("Ophanim (2 Star)", "Angel", 2, "Gain 5 Block each turn", Spell("Wheel of Eyes", 25, 2, "Divine")),
        Entity("Metatron (3 Star)", "Angel", 3, "Purges enemy buffs", Spell("Wrath of Heaven", 120, 6, "Divine"))
    ],
    "Spells": [
        Spell("Zap", 5, 1, "Divine"),
        Spell("Punch", 10, 1, "Nature"),
        Spell("Magic Missile", 20, 2, "Divine"),
        Spell("Hex of Rot", 18, 2, "Shadow"),
        Spell("Holy Barrier", 0, 2, "Divine") # Block spell
    ]
}

# Player State
class PlayerState:
    def __init__(self):
        self.currency = 500
        self.dust = 0 # Arcane Dust for upgrades
        self.hp = 80
        self.max_hp = 80
        self.roster = [] # Summoned Witches, Fae, Angels
        self.active_leader = None
        self.deck = [
            Spell("Basic Strike", 5, 1, "Nature"), 
            Spell("Basic Strike", 5, 1, "Nature"),
            Spell("Zap", 5, 1, "Divine")
        ]
        self.current_node = 0
        self.nodes = ["Crossroads", "Shrine", "Alchemist Shop", "Crossroads", "The Fog (Boss)"]

player = PlayerState()

# --- Screens ---

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(text="URBAN LEGEND DECKBUILDER", font_size=30))
        
        btn_map = Button(text="Enter The Hunt (Rogue-lite Map)", size_hint=(1, 0.15))
        btn_map.bind(on_press=self.go_to_map)
        layout.add_widget(btn_map)
        
        btn_team = Button(text="Coven & Team Building", size_hint=(1, 0.15))
        btn_team.bind(on_press=self.go_to_team)
        layout.add_widget(btn_team)

        btn_gacha = Button(text="Summoning Circle (Gacha)", size_hint=(1, 0.15))
        btn_gacha.bind(on_press=lambda x: setattr(self.manager, 'current', 'gacha'))
        layout.add_widget(btn_gacha)
        
        btn_hangout = Button(text="Hangout (Friendship)", size_hint=(1, 0.15))
        btn_hangout.bind(on_press=self.go_to_hangout)
        layout.add_widget(btn_hangout)
        
        self.add_widget(layout)

    def go_to_map(self, instance):
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'

    def go_to_team(self, instance):
        self.manager.get_screen('team').refresh_ui()
        self.manager.current = 'team'

    def go_to_hangout(self, instance):
        self.manager.get_screen('hangout').refresh_list()
        self.manager.current = 'hangout'


class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_map(self):
        self.layout.clear_widgets()
        
        status = f"Player HP: {player.hp}/{player.max_hp} | Gold: {player.currency} | Dust: {player.dust}\n"
        leader_name = player.active_leader.name if player.active_leader else "None"
        status += f"Coven Leader: {leader_name}"
        self.layout.add_widget(Label(text=status, font_size=18, size_hint=(1, 0.2)))

        self.layout.add_widget(Label(text="--- THE HUNT PATH ---", font_size=22, size_hint=(1, 0.1)))

        nodes_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 0.5))
        
        for idx, node_name in enumerate(player.nodes):
            if idx < player.current_node:
                btn_text = f"✓ Step {idx+1}: {node_name} (Completed)"
                btn = Button(text=btn_text, disabled=True, size_hint=(1, 0.2))
            elif idx == player.current_node:
                btn_text = f"▶ Step {idx+1}: {node_name} (ENTER)"
                btn = Button(text=btn_text, size_hint=(1, 0.2))
                btn.bind(on_press=lambda inst, n=node_name: self.enter_node(n))
            else:
                btn_text = f"Locked: Step {idx+1}: {node_name}"
                btn = Button(text=btn_text, disabled=True, size_hint=(1, 0.2))
            
            nodes_layout.add_widget(btn)

        self.layout.add_widget(nodes_layout)

        back_btn = Button(text="Return to Menu", size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def enter_node(self, node_name):
        if "Crossroads" in node_name or "Boss" in node_name:
            self.manager.get_screen('combat').start_combat(is_boss=("Boss" in node_name))
            self.manager.current = 'combat'
        elif "Alchemist" in node_name:
            self.manager.get_screen('shop').refresh_shop()
            self.manager.current = 'shop'
        elif "Shrine" in node_name:
            player.hp = min(player.max_hp, player.hp + 25)
            player.current_node += 1
            self.refresh_map()


class TeamScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="COVEN & TEAM BUILDING", font_size=24, size_hint=(1, 0.15)))

        active_text = f"Current Leader: {player.active_leader.name if player.active_leader else 'None'}"
        self.layout.add_widget(Label(text=active_text, font_size=18, size_hint=(1, 0.1)))

        scroll = ScrollView(size_hint=(1, 0.6))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        for entity in player.roster:
            btn_text = f"Set {entity.name} [{entity.origin}]\nPassive: {entity.passive_desc}"
            btn = Button(text=btn_text, size_hint_y=None, height=100)
            btn.bind(on_press=lambda inst, e=entity: self.set_leader(e))
            list_layout.add_widget(btn)

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Back to Menu", size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def set_leader(self, entity):
        player.active_leader = entity
        self.refresh_ui()


class ShopScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_shop(self):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="ALCHEMIST HUT", font_size=26, size_hint=(1, 0.15)))
        
        self.status_label = Label(text=f"Gold: {player.currency} | HP: {player.hp}/{player.max_hp}", font_size=18, size_hint=(1, 0.1))
        self.layout.add_widget(self.status_label)

        # Shop Options
        btn_heal = Button(text="Buy Healing Salve (+30 HP) - 75 Gold", size_hint=(1, 0.2))
        btn_heal.bind(on_press=self.buy_heal)
        self.layout.add_widget(btn_heal)

        btn_spell = Button(text="Buy Random Ritual Spell - 120 Gold", size_hint=(1, 0.2))
        btn_spell.bind(on_press=self.buy_spell)
        self.layout.add_widget(btn_spell)

        leave_btn = Button(text="Leave Shop & Continue Path", size_hint=(1, 0.2))
        leave_btn.bind(on_press=self.leave_shop)
        self.layout.add_widget(leave_btn)

    def buy_heal(self, instance):
        if player.currency >= 75:
            player.currency -= 75
            player.hp = min(player.max_hp, player.hp + 30)
            self.refresh_shop()

    def buy_spell(self, instance):
        if player.currency >= 120:
            player.currency -= 120
            new_spell = random.choice(DATABASE["Spells"])
            player.deck.append(new_spell)
            self.refresh_shop()

    def leave_shop(self, instance):
        player.current_node += 1
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'


class GachaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.status_label = Label(text=f"Currency: {player.currency} | Dust: {player.dust}\nReady to summon.", font_size=18, halign="center")
        layout.add_widget(self.status_label)
        
        self.card_image = Image(
            source='assets/summoning_circle.png', 
            size_hint=(1, 0.4), 
            allow_stretch=True, 
            keep_ratio=True
        )
        layout.add_widget(self.card_image)
        
        self.summon_btn = Button(text="Summon (Cost: 100 Gold)", size_hint=(1, 0.2))
        self.summon_btn.bind(on_press=self.start_summon)
        layout.add_widget(self.summon_btn)
        
        back_btn = Button(text="Back to Menu", size_hint=(1, 0.2))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def start_summon(self, instance):
        if player.currency < 100:
            self.status_label.text = "Not enough gold!"
            return
            
        player.currency -= 100
        
        if random.random() < 0.4:
            pulled = random.choice(DATABASE["Entities"])
            if pulled not in player.roster:
                player.roster.append(pulled)
                self.status_label.text = f"Summoned {pulled.origin}:\n{pulled.name}!"
            else:
                player.dust += 25
                self.status_label.text = f"Duplicate {pulled.name}.\nConverted to 25 Arcane Dust!"
                
            if "Lilith" in pulled.name:
                self.card_image.source = 'assets/lilith.png'
            else:
                self.card_image.source = 'assets/card_back.png'
        else:
            pulled = random.choice(DATABASE["Spells"])
            player.deck.append(pulled)
            self.status_label.text = f"Pulled Ritual Spell:\n{pulled.name}!"
            self.card_image.source = 'assets/card_back.png'


class HangoutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_list(self):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="COVEN HANGOUT", font_size=24, size_hint=(1, 0.2)))
        
        if not player.roster:
            self.layout.add_widget(Label(text="Your coven is empty. Go summon some entities!"))
        else:
            scroll = ScrollView(size_hint=(1, 0.6))
            list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
            list_layout.bind(minimum_height=list_layout.setter('height'))
            
            for entity in player.roster:
                btn_text = f"Talk to {entity.name} (Bond: {entity.bond}/100)"
                btn = Button(text=btn_text, size_hint_y=None, height=100)
                btn.bind(on_press=lambda instance, e=entity: self.talk_to(e))
                list_layout.add_widget(btn)
            
            scroll.add_widget(list_layout)
            self.layout.add_widget(scroll)
            
        back_btn = Button(text="Back to Menu", size_hint=(1, 0.2))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def talk_to(self, entity):
        if entity.bond < 100:
            entity.bond += 25
            if entity.bond >= 100:
                player.deck.append(entity.ultimate_spell)
        self.refresh_list()


class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.enemy = None
        self.mana = 3
        self.hand = []
        self.add_widget(self.layout)

    def start_combat(self, is_boss=False):
        if is_boss:
            self.enemy = Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20), ("Curse", 0)])
        else:
            self.enemy = Enemy("Woodland Shade", 60, "Divine", [("Attack", 10)])
            
        self.mana = 4 if (player.active_leader and "Lilith" in player.active_leader.name) else 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()

    def update_ui(self):
        self.layout.clear_widgets()
        
        if self.enemy.hp <= 0:
            player.currency += 120
            player.current_node += 1
            self.layout.add_widget(Label(text="VICTORY!\nGained 120 Gold.", font_size=30))
            back_btn = Button(text="Continue Path", size_hint=(1, 0.2))
            back_btn.bind(on_press=self.finish_combat)
            self.layout.add_widget(back_btn)
            return

        if player.hp <= 0:
            self.layout.add_widget(Label(text="YOU WERE DEFEATED...", font_size=30))
            back_btn = Button(text="Return to Menu", size_hint=(1, 0.2))
            back_btn.bind(on_press=self.reset_run)
            self.layout.add_widget(back_btn)
            return

        # Header Info
        status_text = f"Your HP: {player.hp}/{player.max_hp} | Mana: {self.mana}\n"
        status_text += f"{self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp} (Weakness: {self.enemy.weakness})"
        self.layout.add_widget(Label(text=status_text, font_size=18, size_hint=(1, 0.2)))
        
        # Draw Hand
        cards_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.4))
        for spell in self.hand:
            btn = Button(text=f"{spell.name}\n[{spell.spell_type}]\nDmg: {spell.damage} | Cost: {spell.cost}")
            btn.bind(on_press=lambda instance, s=spell: self.cast_spell(s))
            cards_layout.add_widget(btn)
            
        self.layout.add_widget(cards_layout)
        
        end_turn_btn = Button(text="End Turn", size_hint=(1, 0.2))
        end_turn_btn.bind(on_press=self.enemy_turn)
        self.layout.add_widget(end_turn_btn)

    def cast_spell(self, spell):
        if self.mana >= spell.cost:
            self.mana -= spell.cost
            
            # Damage multiplier calculation
            mult = 1.5 if spell.spell_type == self.enemy.weakness else 1.0
            total_dmg = int(spell.damage * mult)
            
            self.enemy.hp -= total_dmg
            self.hand.remove(spell)
            self.update_ui()

    def enemy_turn(self, instance):
        # Enemy attacks player
        player.hp -= 10
        self.mana = 4 if (player.active_leader and "Lilith" in player.active_leader.name) else 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()

    def finish_combat(self, instance):
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'

    def reset_run(self, instance):
        player.hp = player.max_hp
        player.current_node = 0
        self.manager.current = 'menu'


# --- App Runner ---
class DeckbuilderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(MapScreen(name='map'))
        sm.add_widget(TeamScreen(name='team'))
        sm.add_widget(ShopScreen(name='shop'))
        sm.add_widget(GachaScreen(name='gacha'))
        sm.add_widget(HangoutScreen(name='hangout'))
        sm.add_widget(CombatScreen(name='combat'))
        return sm

if __name__ == '__main__':
    DeckbuilderApp().run()
