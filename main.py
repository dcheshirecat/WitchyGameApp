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
    def __init__(self, name, damage, cost, spell_type="Nature", block=0, status_effect=None, level=1):
        self.name = name
        self.damage = damage
        self.cost = cost
        self.spell_type = spell_type # "Nature", "Shadow", "Divine"
        self.block = block
        self.status_effect = status_effect # ("Burn", value) or ("Poison", value)
        self.level = level

class Entity:
    def __init__(self, name, origin, rarity, passive_desc, ultimate_spell, lore):
        self.name = name
        self.origin = origin # "Witch", "Fae", "Angel"
        self.rarity = rarity
        self.passive_desc = passive_desc
        self.ultimate_spell = ultimate_spell
        self.lore = lore
        self.bond = 0

class Enemy:
    def __init__(self, name, hp, weakness, intents, lore):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.block = 0
        self.burn = 0
        self.poison = 0
        self.weakness = weakness
        self.intents = intents # List of (action_type, value)
        self.lore = lore

# Expanded Database
DATABASE = {
    "Entities": [
        Entity("Chloe (1 Star)", "Witch", 1, "Heals 3 HP on Fire spells", 
               Spell("Fireball", 15, 2, "Nature", status_effect=("Burn", 5)),
               "A village herbalist who learned to kindle eldritch embers in secret root cellars."),
        Entity("Sam (2 Star)", "Witch", 2, "+10% Shadow damage", 
               Spell("Shadow Strike", 30, 3, "Shadow", status_effect=("Poison", 4)),
               "A solitary hedge witch capable of weaving twilight into deadly piercing blades."),
        Entity("Lilith (3 Star)", "Witch", 3, "Start combat with +1 Mana", 
               Spell("Obliterate", 100, 5, "Shadow"),
               "The ancient grand witch of dark arcana, commanding supreme shadow geometry."),
        Entity("Puck (1 Star)", "Fae", 1, "Draw +1 card at battle start", 
               Spell("Trickster Spark", 12, 1, "Nature"),
               "An elusive woodland spirit whose laughter bends probability and misdirects travelers."),
        Entity("The Kelpie (2 Star)", "Fae", 2, "Enemies take 15% more damage", 
               Spell("Drowning Depths", 35, 3, "Nature"),
               "A shapeshifting water demon of Scottish lochs that drags the unwary beneath dark waters."),
        Entity("Queen Mab (3 Star)", "Fae", 3, "Steals 1 enemy intent turn", 
               Spell("Nightmare Realm", 75, 4, "Shadow"),
               "Monarch of the Unseelie court, governing bad dreams, illusions, and nocturnal oaths."),
        Entity("Ophanim (2 Star)", "Angel", 2, "Gain 5 Block each turn", 
               Spell("Wheel of Eyes", 25, 2, "Divine", block=15),
               "A celestial ring of spinning golden wheels lined with a hundred vigilant eyes."),
        Entity("Metatron (3 Star)", "Angel", 3, "Purges enemy buffs", 
               Spell("Wrath of Heaven", 120, 6, "Divine", block=30),
               "The supreme voice of the heavens whose spoken word incinerates unholy hexes.")
    ],
    "Spells": [
        Spell("Basic Strike", 5, 1, "Nature"),
        Spell("Zap", 5, 1, "Divine"),
        Spell("Punch", 10, 1, "Nature"),
        Spell("Magic Missile", 20, 2, "Divine"),
        Spell("Hex of Rot", 12, 2, "Shadow", status_effect=("Poison", 3)),
        Spell("Holy Barrier", 0, 2, "Divine", block=20)
    ],
    "Bestiary": [
        Enemy("Woodland Shade", 60, "Divine", [("Attack", 10)], 
              "A lingering spirit born of old forgotten woods, vulnerable to holy light."),
        Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20), ("Curse", 0)], 
              "A winged red-eyed harbinger whose presence destabilizes the fabric of reality.")
    ]
}

# Player State
class PlayerState:
    def __init__(self):
        self.currency = 500
        self.dust = 100
        self.hp = 80
        self.max_hp = 80
        self.block = 0
        self.roster = []
        self.bestiary_unlocked = []
        self.active_leader = None
        self.deck = [
            Spell("Basic Strike", 5, 1, "Nature"), 
            Spell("Basic Strike", 5, 1, "Nature"),
            Spell("Zap", 5, 1, "Divine"),
            Spell("Holy Barrier", 0, 2, "Divine", block=15)
        ]
        self.current_node = 0
        self.nodes = ["Crossroads", "Shrine", "Alchemist Shop", "Crossroads", "The Fog (Boss)"]

player = PlayerState()

# --- Screens ---

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=30, spacing=10)
        
        # Background frame setup
        layout.add_widget(Label(text="URBAN LEGEND DECKBUILDER", font_size=28, bold=True))
        
        btn_map = Button(text="Enter The Hunt (Rogue-lite Map)", size_hint=(1, 0.12))
        btn_map.bind(on_press=self.go_to_map)
        layout.add_widget(btn_map)
        
        btn_team = Button(text="Coven & Team Building", size_hint=(1, 0.12))
        btn_team.bind(on_press=self.go_to_team)
        layout.add_widget(btn_team)

        btn_upgrade = Button(text="Arcane Dust Upgrade Shrine", size_hint=(1, 0.12))
        btn_upgrade.bind(on_press=self.go_to_upgrade)
        layout.add_widget(btn_upgrade)

        btn_grimoire = Button(text="The Esoteric Grimoire", size_hint=(1, 0.12))
        btn_grimoire.bind(on_press=self.go_to_grimoire)
        layout.add_widget(btn_grimoire)

        btn_gacha = Button(text="Summoning Circle (Gacha)", size_hint=(1, 0.12))
        btn_gacha.bind(on_press=lambda x: setattr(self.manager, 'current', 'gacha'))
        layout.add_widget(btn_gacha)
        
        btn_hangout = Button(text="Hangout (Friendship)", size_hint=(1, 0.12))
        btn_hangout.bind(on_press=self.go_to_hangout)
        layout.add_widget(btn_hangout)
        
        self.add_widget(layout)

    def go_to_map(self, instance):
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'

    def go_to_team(self, instance):
        self.manager.get_screen('team').refresh_ui()
        self.manager.current = 'team'

    def go_to_upgrade(self, instance):
        self.manager.get_screen('upgrade').refresh_ui()
        self.manager.current = 'upgrade'

    def go_to_grimoire(self, instance):
        self.manager.get_screen('grimoire').refresh_ui()
        self.manager.current = 'grimoire'

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
        
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), spacing=10)
        header.add_widget(Image(source='assets/icon_hp.png', size_hint=(0.15, 1)))
        
        status_text = f"HP: {player.hp}/{player.max_hp} | Gold: {player.currency} | Dust: {player.dust}\n"
        leader_name = player.active_leader.name if player.active_leader else "None"
        status_text += f"Leader: {leader_name}"
        header.add_widget(Label(text=status_text, font_size=16))
        
        self.layout.add_widget(header)
        self.layout.add_widget(Label(text="--- THE HUNT PATH ---", font_size=22, size_hint=(1, 0.1)))

        nodes_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 0.58))
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

        back_btn = Button(text="Return to Menu", size_hint=(1, 0.12))
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


class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=8)
        self.enemy = None
        self.mana = 3
        self.hand = []
        self.add_widget(self.layout)

    def start_combat(self, is_boss=False):
        if is_boss:
            self.enemy = Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20)], DATABASE["Bestiary"][1].lore)
        else:
            self.enemy = Enemy("Woodland Shade", 60, "Divine", [("Attack", 12)], DATABASE["Bestiary"][0].lore)
            
        if self.enemy.name not in player.bestiary_unlocked:
            player.bestiary_unlocked.append(self.enemy.name)

        player.block = 0
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

        # Status & Resource Header with UI Icons
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.15), spacing=5)
        
        hp_box = BoxLayout(orientation='horizontal')
        hp_box.add_widget(Image(source='assets/icon_hp.png', size_hint=(0.4, 1)))
        hp_box.add_widget(Label(text=f"{player.hp}/{player.max_hp}\nShield: {player.block}", font_size=14))
        header.add_widget(hp_box)

        mana_box = BoxLayout(orientation='horizontal')
        mana_box.add_widget(Image(source='assets/icon_mana.png', size_hint=(0.4, 1)))
        mana_box.add_widget(Label(text=f"Mana: {self.mana}", font_size=14))
        header.add_widget(mana_box)

        self.layout.add_widget(header)

        # Enemy Display & Status Effects (Burn/Poison)
        enemy_info = f"{self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp} (Weakness: {self.enemy.weakness})\n"
        enemy_info += f"Statuses: Burn ({self.enemy.burn}) | Poison ({self.enemy.poison})"
        self.layout.add_widget(Label(text=enemy_info, font_size=16, size_hint=(1, 0.15)))

        # Card Hand with Custom Templates
        cards_layout = BoxLayout(orientation='horizontal', spacing=8, size_hint=(1, 0.5))
        for spell in self.hand:
            card_box = BoxLayout(orientation='vertical', padding=5)
            btn_text = f"{spell.name} (Lv {spell.level})\n[{spell.spell_type}]\nDmg:{spell.damage} Blk:{spell.block}\nCost: {spell.cost}"
            btn = Button(text=btn_text, font_size=12)
            btn.bind(on_press=lambda instance, s=spell: self.cast_spell(s))
            card_box.add_widget(btn)
            cards_layout.add_widget(card_box)
            
        self.layout.add_widget(cards_layout)
        
        end_turn_btn = Button(text="End Turn", size_hint=(1, 0.15))
        end_turn_btn.bind(on_press=self.enemy_turn)
        self.layout.add_widget(end_turn_btn)

    def cast_spell(self, spell):
        if self.mana >= spell.cost:
            self.mana -= spell.cost
            
            # Apply Shield Block
            player.block += spell.block
            
            # Calculate Elemental Weakness Damage
            mult = 1.5 if spell.spell_type == self.enemy.weakness else 1.0
            total_dmg = int(spell.damage * mult)
            
            self.enemy.hp -= total_dmg
            
            # Apply Status Effect
            if spell.status_effect:
                effect_type, val = spell.status_effect
                if effect_type == "Burn":
                    self.enemy.burn += val
                elif effect_type == "Poison":
                    self.enemy.poison += val

            self.hand.remove(spell)
            self.update_ui()

    def enemy_turn(self, instance):
        # 1. Process Enemy Status Effects (Burn / Poison)
        if self.enemy.burn > 0:
            self.enemy.hp -= self.enemy.burn
            self.enemy.burn = max(0, self.enemy.burn - 1)

        if self.enemy.poison > 0:
            self.enemy.hp -= self.enemy.poison

        # 2. Enemy Attacks Player (Mitigated by Shield Block)
        raw_damage = 12
        damage_to_hp = max(0, raw_damage - player.block)
        player.block = max(0, player.block - raw_damage)
        player.hp -= damage_to_hp

        # Reset turn
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


class UpgradeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), spacing=10)
        header.add_widget(Image(source='assets/icon_dust.png', size_hint=(0.2, 1)))
        header.add_widget(Label(text=f"ARCANE DUST SHRINE\nDust: {player.dust} | Gold: {player.currency}", font_size=18))
        self.layout.add_widget(header)

        self.layout.add_widget(Label(text="Select a spell to empower (+5 Dmg, max Lv 3):", size_hint=(1, 0.08)))

        scroll = ScrollView(size_hint=(1, 0.65))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        for spell in player.deck:
            cost_dust = spell.level * 50
            btn_text = f"[{spell.spell_type}] {spell.name} (Lv {spell.level})\nDamage: {spell.damage} | Cost: {cost_dust} Dust"
            btn = Button(text=btn_text, size_hint_y=None, height=80, disabled=(player.dust < cost_dust or spell.level >= 3))
            btn.bind(on_press=lambda inst, s=spell, c=cost_dust: self.upgrade_spell(s, c))
            list_layout.add_widget(btn)

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Back to Menu", size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def upgrade_spell(self, spell, dust_cost):
        if player.dust >= dust_cost and spell.level < 3:
            player.dust -= dust_cost
            spell.level += 1
            spell.damage += 5
            self.refresh_ui()


class GrimoireScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="ESOTERIC GRIMOIRE", font_size=24, size_hint=(1, 0.12)))

        scroll = ScrollView(size_hint=(1, 0.73))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        list_layout.add_widget(Label(text="=== COVEN ENTITIES ===", font_size=20, size_hint_y=None, height=40))
        for db_entity in DATABASE["Entities"]:
            is_unlocked = any(e.name == db_entity.name for e in player.roster)
            if is_unlocked:
                entry = f"📜 {db_entity.name} [{db_entity.origin}]\nPassive: {db_entity.passive_desc}\nLore: {db_entity.lore}"
            else:
                entry = f"🔒 {db_entity.name} [{db_entity.origin}]\n[LORE LOCKED - Summon to reveal entry]"
            
            lbl = Label(text=entry, size_hint_y=None, height=110, halign="center")
            list_layout.add_widget(lbl)

        list_layout.add_widget(Label(text="=== URBAN LEGEND BESTIARY ===", font_size=20, size_hint_y=None, height=40))
        for db_enemy in DATABASE["Bestiary"]:
            is_encountered = db_enemy.name in player.bestiary_unlocked
            if is_encountered:
                entry = f"💀 {db_enemy.name} (Weakness: {db_enemy.weakness})\nLore: {db_enemy.lore}"
            else:
                entry = f"❓ {db_enemy.name}\n[LORE LOCKED - Encounter on The Hunt to reveal]"
            
            lbl = Label(text=entry, size_hint_y=None, height=90, halign="center")
            list_layout.add_widget(lbl)

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Back to Menu", size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)


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
            if not any(e.name == pulled.name for e in player.roster):
                player.roster.append(pulled)
                self.status_label.text = f"Summoned {pulled.origin}:\n{pulled.name}!"
            else:
                player.dust += 25
                self.status_label.text = f"Duplicate {pulled.name}.\nConverted to 25 Arcane Dust!"
                
            if "Lilith" in pulled.name:
                self.card_image.source = 'assets/lilith.png'
            elif "Puck" in pulled.name:
                self.card_image.source = 'assets/puck.png'
            elif "Ophanim" in pulled.name:
                self.card_image.source = 'assets/ophanim.png'
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


# --- App Runner ---
class DeckbuilderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(MapScreen(name='map'))
        sm.add_widget(TeamScreen(name='team'))
        sm.add_widget(UpgradeScreen(name='upgrade'))
        sm.add_widget(GrimoireScreen(name='grimoire'))
        sm.add_widget(ShopScreen(name='shop'))
        sm.add_widget(GachaScreen(name='gacha'))
        sm.add_widget(HangoutScreen(name='hangout'))
        sm.add_widget(CombatScreen(name='combat'))
        return sm

if __name__ == '__main__':
    DeckbuilderApp().run()
