from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.utils import platform
import random
import json
import os

# --- Core Data Structures ---

class Spell:
    def __init__(self, name, damage, cost, spell_type="Nature", block=0, status_effect=None, level=1):
        self.name = name
        self.damage = damage
        self.cost = cost
        self.spell_type = spell_type
        self.block = block
        self.status_effect = status_effect
        self.level = level

class Entity:
    def __init__(self, name, origin, rarity, passive_desc, ultimate_spell, lore, dialogues=None):
        self.name = name
        self.origin = origin
        self.rarity = rarity
        self.passive_desc = passive_desc
        self.ultimate_spell = ultimate_spell
        self.lore = lore
        self.bond = 0
        self.dialogues = dialogues or []

class Enemy:
    def __init__(self, name, hp, weakness, intents, lore):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.block = 0
        self.burn = 0
        self.poison = 0
        self.weakness = weakness
        self.intents = intents
        self.lore = lore

# Expanded Database with Dialogue Trees
DATABASE = {
    "Entities": [
        Entity("Chloe (1 Star)", "Witch", 1, "Heals 3 HP on Fire spells", 
               Spell("Fireball", 15, 2, "Nature", status_effect=("Burn", 5)),
               "A village herbalist who learned to kindle eldritch embers in secret root cellars.",
               dialogues=[{
                   "prompt": "The moon is full. Should we harvest Nightshade or Mandrake tonight?",
                   "options": [
                       {"text": "Nightshade for hexes.", "reward": ("bond", 25)},
                       {"text": "Mandrake for alchemy.", "reward": ("dust", 30)}
                   ]
               }]),
        Entity("Sam (2 Star)", "Witch", 2, "+10% Shadow damage", 
               Spell("Shadow Strike", 30, 3, "Shadow", status_effect=("Poison", 4)),
               "A solitary hedge witch capable of weaving twilight into deadly piercing blades.",
               dialogues=[{
                   "prompt": "The shadows are restless. Do you fear the dark?",
                   "options": [
                       {"text": "I embrace it.", "reward": ("bond", 25)},
                       {"text": "It hides our enemies.", "reward": ("currency", 50)}
                   ]
               }]),
        Entity("Lilith (3 Star)", "Witch", 3, "Start combat with +1 Mana", 
               Spell("Obliterate", 100, 5, "Shadow"),
               "The ancient grand witch of dark arcana, commanding supreme shadow geometry.",
               dialogues=[{
                   "prompt": "True power requires blood sacrifice. What will you offer?",
                   "options": [
                       {"text": "My own blood.", "reward": ("bond", 35)},
                       {"text": "The blood of my foes.", "reward": ("dust", 50)}
                   ]
               }]),
        Entity("Puck (1 Star)", "Fae", 1, "Draw +1 card at battle start", 
               Spell("Trickster Spark", 12, 1, "Nature"),
               "An elusive woodland spirit whose laughter bends probability and misdirects travelers.",
               dialogues=[{
                   "prompt": "Pick a hand, mortal! Left or Right?",
                   "options": [
                       {"text": "The Left Hand.", "reward": ("dust", 20)},
                       {"text": "The Right Hand.", "reward": ("bond", 25)}
                   ]
               }]),
        Entity("The Kelpie (2 Star)", "Fae", 2, "Enemies take 15% more damage", 
               Spell("Drowning Depths", 35, 3, "Nature"),
               "A shapeshifting water demon of Scottish lochs that drags the unwary beneath dark waters.",
               dialogues=[{
                   "prompt": "The water is so very cold... come closer.",
                   "options": [
                       {"text": "Step back.", "reward": ("dust", 25)},
                       {"text": "Offer an apple.", "reward": ("bond", 25)}
                   ]
               }]),
        Entity("Queen Mab (3 Star)", "Fae", 3, "Steals 1 enemy intent turn", 
               Spell("Nightmare Realm", 75, 4, "Shadow"),
               "Monarch of the Unseelie court, governing bad dreams, illusions, and nocturnal oaths.",
               dialogues=[{
                   "prompt": "Will you swear fealty to the winter court?",
                   "options": [
                       {"text": "Yes, my Queen.", "reward": ("bond", 25)},
                       {"text": "I serve no one.", "reward": ("dust", 40)}
                   ]
               }]),
        Entity("Ophanim (2 Star)", "Angel", 2, "Gain 5 Block each turn", 
               Spell("Wheel of Eyes", 25, 2, "Divine", block=15),
               "A celestial ring of spinning golden wheels lined with a hundred vigilant eyes.",
               dialogues=[{
                   "prompt": "BE NOT AFRAID.",
                   "options": [
                       {"text": "I am not afraid.", "reward": ("bond", 25)},
                       {"text": "I am terrified.", "reward": ("currency", 75)}
                   ]
               }]),
        Entity("Metatron (3 Star)", "Angel", 3, "Purges enemy buffs", 
               Spell("Wrath of Heaven", 120, 6, "Divine", block=30),
               "The supreme voice of the heavens whose spoken word incinerates unholy hexes.",
               dialogues=[{
                   "prompt": "The scales of reality must be balanced.",
                   "options": [
                       {"text": "Then balance them.", "reward": ("bond", 25)},
                       {"text": "Break the scales.", "reward": ("dust", 50)}
                   ]
               }])
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
        Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20)], 
              "A winged red-eyed harbinger whose presence destabilizes the fabric of reality.")
    ]
}

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
        self.current_tier = 0
        self.map_graph = [
            [{"id": 0, "type": "Crossroads", "label": "⚔️ Path Alpha"}, {"id": 1, "type": "Crossroads", "label": "⚔️ Path Beta"}],
            [{"id": 2, "type": "Alchemist Shop", "label": "🧪 Apothecary"}, {"id": 3, "type": "Shrine", "label": "⛩️ Sacred Spring"}],
            [{"id": 4, "type": "Boss", "label": "💀 The Fog (Mothman)"}]
        ]

    def save_game(self):
        app = App.get_running_app()
        if not app: return
        save_path = os.path.join(app.user_data_dir, 'savegame.json')
        
        data = {
            'currency': self.currency,
            'dust': self.dust,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'current_tier': self.current_tier,
            'bestiary_unlocked': self.bestiary_unlocked,
            'roster': [{'name': e.name, 'bond': e.bond} for e in self.roster],
            'active_leader': self.active_leader.name if self.active_leader else None,
            'deck': [{'name': s.name, 'level': s.level, 'damage': s.damage, 'cost': s.cost, 'spell_type': s.spell_type, 'block': s.block, 'status_effect': s.status_effect} for s in self.deck]
        }
        
        with open(save_path, 'w') as f:
            json.dump(data, f)

    def load_game(self):
        app = App.get_running_app()
        if not app: return
        save_path = os.path.join(app.user_data_dir, 'savegame.json')
        
        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                data = json.load(f)
                
            self.currency = data.get('currency', 500)
            self.dust = data.get('dust', 100)
            self.hp = data.get('hp', 80)
            self.max_hp = data.get('max_hp', 80)
            self.current_tier = data.get('current_tier', 0)
            self.bestiary_unlocked = data.get('bestiary_unlocked', [])
            
            # Reconstruct roster and bond levels
            self.roster = []
            for saved_ent in data.get('roster', []):
                for db_ent in DATABASE['Entities']:
                    if db_ent.name == saved_ent['name']:
                        db_ent.bond = saved_ent.get('bond', 0)
                        self.roster.append(db_ent)
                        
            leader_name = data.get('active_leader')
            if leader_name:
                self.active_leader = next((e for e in self.roster if e.name == leader_name), None)
                
            # Reconstruct independent spell cards
            self.deck = []
            for s in data.get('deck', []):
                status_eff = s.get('status_effect')
                if status_eff:
                    status_eff = tuple(status_eff)
                self.deck.append(Spell(s['name'], s['damage'], s['cost'], s['spell_type'], s.get('block', 0), status_eff, s.get('level', 1)))

player = PlayerState()

def make_wrapped_label(text, font_size='18sp', bold=False, color=(1, 1, 1, 1), size_hint=(1, None), height=80):
    lbl = Label(
        text=text, font_size=font_size, bold=bold, color=color,
        halign="center", valign="middle", size_hint=size_hint
    )
    if size_hint[1] is None:
        lbl.height = height
    lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0] - 20, None)))
    return lbl

# --- Screens ---

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)
        layout.add_widget(make_wrapped_label("URBAN LEGEND DECKBUILDER", font_size='28sp', bold=True, size_hint=(1, 0.16)))
        
        btn_map = Button(text="Enter The Hunt (Branching Map)", font_size='18sp', size_hint=(1, 0.12))
        btn_map.bind(on_press=self.go_to_map)
        layout.add_widget(btn_map)
        
        btn_team = Button(text="Coven & Team Building", font_size='18sp', size_hint=(1, 0.12))
        btn_team.bind(on_press=self.go_to_team)
        layout.add_widget(btn_team)

        btn_upgrade = Button(text="Arcane Dust Upgrade Shrine", font_size='18sp', size_hint=(1, 0.12))
        btn_upgrade.bind(on_press=self.go_to_upgrade)
        layout.add_widget(btn_upgrade)

        btn_grimoire = Button(text="The Esoteric Grimoire", font_size='18sp', size_hint=(1, 0.12))
        btn_grimoire.bind(on_press=self.go_to_grimoire)
        layout.add_widget(btn_grimoire)

        btn_web = Button(text="Launch 3D Web Battlefield", font_size='18sp', size_hint=(1, 0.12))
        btn_web.bind(on_press=lambda x: setattr(self.manager, 'current', 'web'))
        layout.add_widget(btn_web)

        btn_gacha = Button(text="Summoning Circle (Gacha)", font_size='18sp', size_hint=(1, 0.12))
        btn_gacha.bind(on_press=lambda x: setattr(self.manager, 'current', 'gacha'))
        layout.add_widget(btn_gacha)
        
        btn_hangout = Button(text="Hangout (Friendship)", font_size='18sp', size_hint=(1, 0.12))
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
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        self.add_widget(self.layout)

    def refresh_map(self):
        self.layout.clear_widgets()
        
        leader_name = player.active_leader.name if player.active_leader else "None"
        stats_text = f"HP: {player.hp}/{player.max_hp} | Gold: {player.currency} | Dust: {player.dust}\nCoven Leader: {leader_name}"
        self.layout.add_widget(make_wrapped_label(stats_text, font_size='18sp', bold=True, size_hint=(1, 0.15)))

        self.layout.add_widget(make_wrapped_label("--- BRANCHING MAP GRAPH ---", font_size='22sp', bold=True, size_hint=(1, 0.1)))

        scroll = ScrollView(size_hint=(1, 0.65))
        map_path_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=20, padding=10)
        map_path_layout.bind(minimum_height=map_path_layout.setter('height'))

        for tier_idx in range(len(player.map_graph) - 1, -1, -1):
            tier_nodes = player.map_graph[tier_idx]
            tier_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, spacing=15)
            
            for node in tier_nodes:
                if tier_idx < player.current_tier:
                    btn_text = f"✓ {node['label']}"
                    btn_color = (0.3, 0.7, 0.3, 1)
                    is_disabled = True
                elif tier_idx == player.current_tier:
                    btn_text = f"▶ {node['label']}"
                    btn_color = (0.9, 0.6, 0.2, 1)
                    is_disabled = False
                else:
                    btn_text = f"🔒 {node['label']}"
                    btn_color = (0.3, 0.3, 0.35, 1)
                    is_disabled = True

                btn = Button(
                    text=btn_text, font_size='16sp', bold=True,
                    background_color=btn_color, disabled=is_disabled
                )
                btn.bind(on_press=lambda inst, n=node['type']: self.enter_node(n))
                tier_box.add_widget(btn)
                
            map_path_layout.add_widget(tier_box)

        scroll.add_widget(map_path_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Return to Menu", font_size='18sp', size_hint=(1, 0.12))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def enter_node(self, node_type):
        if node_type in ["Crossroads", "Boss"]:
            self.manager.get_screen('combat').start_combat(is_boss=(node_type == "Boss"))
            self.manager.current = 'combat'
        elif node_type == "Alchemist Shop":
            self.manager.get_screen('shop').refresh_shop()
            self.manager.current = 'shop'
        elif node_type == "Shrine":
            player.hp = min(player.max_hp, player.hp + 25)
            player.current_tier += 1
            player.save_game()
            self.refresh_map()


class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
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
            player.save_game()

        player.block = 0
        self.mana = 4 if (player.active_leader and "Lilith" in player.active_leader.name) else 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()

    def update_ui(self):
        self.layout.clear_widgets()
        
        if self.enemy.hp <= 0:
            player.currency += 120
            player.current_tier += 1
            player.save_game()
            self.layout.add_widget(make_wrapped_label("VICTORY!\nGained 120 Gold.", font_size='32sp', bold=True, size_hint=(1, 0.6)))
            back_btn = Button(text="Continue Path", font_size='22sp', size_hint=(1, 0.2))
            back_btn.bind(on_press=self.finish_combat)
            self.layout.add_widget(back_btn)
            return

        if player.hp <= 0:
            self.layout.add_widget(make_wrapped_label("YOU WERE DEFEATED...", font_size='32sp', bold=True, size_hint=(1, 0.6)))
            back_btn = Button(text="Return to Menu", font_size='22sp', size_hint=(1, 0.2))
            back_btn.bind(on_press=self.reset_run)
            self.layout.add_widget(back_btn)
            return

        status_text = f"HP: {player.hp}/{player.max_hp} (Shield: {player.block})  |  Mana: {self.mana}\n"
        status_text += f"{self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp} (Weakness: {self.enemy.weakness})\n"
        status_text += f"Enemy Statuses: Burn ({self.enemy.burn}) | Poison ({self.enemy.poison})"
        self.layout.add_widget(make_wrapped_label(status_text, font_size='16sp', bold=True, size_hint=(1, 0.25)))

        cards_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.55))
        for spell in self.hand:
            btn_text = f"{spell.name}\n(Lv {spell.level})\n[{spell.spell_type}]\nDmg: {spell.damage}\nCost: {spell.cost}"
            btn = Button(text=btn_text, font_size='15sp', halign="center", valign="middle")
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-10, None)))
            btn.bind(on_press=lambda instance, s=spell, b=btn: self.cast_spell(s, b))
            cards_layout.add_widget(btn)
            
        self.layout.add_widget(cards_layout)
        
        nav_row = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.2))
        flee_btn = Button(text="Retreat", font_size='20sp')
        flee_btn.bind(on_press=self.retreat_combat)
        end_turn_btn = Button(text="End Turn", font_size='20sp', background_color=(0.2, 0.6, 0.8, 1))
        end_turn_btn.bind(on_press=self.enemy_turn)
        nav_row.add_widget(flee_btn)
        nav_row.add_widget(end_turn_btn)
        
        self.layout.add_widget(nav_row)

    def cast_spell(self, spell, btn_widget):
        if self.mana >= spell.cost:
            anim = Animation(size_hint_y=1.1, duration=0.1) + Animation(size_hint_y=1.0, duration=0.1)
            anim.start(btn_widget)
            
            self.mana -= spell.cost
            player.block += spell.block
            mult = 1.5 if spell.spell_type == self.enemy.weakness else 1.0
            self.enemy.hp -= int(spell.damage * mult)
            
            if spell.status_effect:
                effect_type, val = spell.status_effect
                if effect_type == "Burn":
                    self.enemy.burn += val
                elif effect_type == "Poison":
                    self.enemy.poison += val

            self.hand.remove(spell)
            self.update_ui()

    def enemy_turn(self, instance):
        shake = (Animation(x=self.layout.x + 10, duration=0.04) + 
                 Animation(x=self.layout.x - 10, duration=0.04) + 
                 Animation(x=self.layout.x, duration=0.04))
        shake.start(self.layout)

        if self.enemy.burn > 0:
            self.enemy.hp -= self.enemy.burn
            self.enemy.burn = max(0, self.enemy.burn - 1)

        if self.enemy.poison > 0:
            self.enemy.hp -= self.enemy.poison

        raw_damage = 12
        damage_to_hp = max(0, raw_damage - player.block)
        player.block = max(0, player.block - raw_damage)
        player.hp -= damage_to_hp

        self.mana = 4 if (player.active_leader and "Lilith" in player.active_leader.name) else 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()

    def finish_combat(self, instance):
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'
        
    def retreat_combat(self, instance):
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'

    def reset_run(self, instance):
        player.hp = player.max_hp
        player.current_tier = 0
        player.save_game()
        self.manager.current = 'menu'


class WebScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(make_wrapped_label("3D RITUAL BATTLEFIELD", font_size='22sp', bold=True, size_hint=(1, 0.1)))
        
        self.web_container = BoxLayout(size_hint=(1, 0.8))
        self.layout.add_widget(self.web_container)
        
        back_btn = Button(text="Return to Main Menu", font_size='18sp', size_hint=(1, 0.1))
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)
        
        self.add_widget(self.layout)

    def on_enter(self):
        if platform == 'android':
            self.load_android_webview()
        else:
            self.web_container.clear_widgets()
            self.web_container.add_widget(
                make_wrapped_label("[index.html Active]\n(Compiling into APK launches native Web View)", 
                                   font_size='18sp', size_hint=(1, 1))
            )

    def load_android_webview(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = PythonActivity.mActivity

            combat_payload = {
                "mana": 3,
                "enemyHp": 3000,
                "deck": [{"name": s.name, "dmg": s.damage} for s in player.deck]
            }
            json_data = json.dumps(combat_payload)

            @run_on_ui_thread
            def create_webview():
                webview = WebView(activity)
                
                # Enable JS and Local File Access Permissions
                settings = webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setAllowFileAccess(True)
                settings.setAllowFileAccessFromFileURLs(True)
                settings.setAllowUniversalAccessFromFileURLs(True)
                
                webview.setWebViewClient(WebViewClient())
                
                # Dynamically locate where Kivy extracted the index.html file on the device
                html_path = os.path.abspath(os.path.join('assets', 'index.html'))
                webview.loadUrl(f'file://{html_path}')
                
                webview.evaluateJavascript(f"initBattlefield({json_data});", None)
                activity.setContentView(webview)

            create_webview()
        except Exception as e:
            self.web_container.clear_widgets()
            self.web_container.add_widget(make_wrapped_label(f"WebView Exception: {str(e)}", font_size='16sp', size_hint=(1, 1)))

    def go_back(self, instance):
        self.manager.current = 'menu'


class UpgradeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        
        status = f"ARCANE DUST SHRINE\nDust: {player.dust}  |  Gold: {player.currency}"
        self.layout.add_widget(make_wrapped_label(status, font_size='22sp', bold=True, size_hint=(1, 0.15)))
        self.layout.add_widget(make_wrapped_label("Select a spell to empower (+5 Dmg, max Lv 3):", font_size='18sp', size_hint=(1, 0.08)))

        scroll = ScrollView(size_hint=(1, 0.62))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        for spell in player.deck:
            cost_dust = spell.level * 50
            btn_text = f"[{spell.spell_type}] {spell.name} (Lv {spell.level})\nDamage: {spell.damage} | Upgrade Cost: {cost_dust} Dust"
            btn = Button(
                text=btn_text, font_size='16sp', halign="center", valign="middle",
                size_hint_y=None, height=100, disabled=(player.dust < cost_dust or spell.level >= 3)
            )
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-20, None)))
            btn.bind(on_press=lambda inst, s=spell, c=cost_dust: self.upgrade_spell(s, c))
            list_layout.add_widget(btn)

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def upgrade_spell(self, spell, dust_cost):
        if player.dust >= dust_cost and spell.level < 3:
            player.dust -= dust_cost
            spell.level += 1
            spell.damage += 5
            player.save_game()
            self.refresh_ui()


class GrimoireScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label("ESOTERIC GRIMOIRE", font_size='24sp', bold=True, size_hint=(1, 0.12)))

        scroll = ScrollView(size_hint=(1, 0.73))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=20)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        list_layout.add_widget(make_wrapped_label("=== COVEN ENTITIES ===", font_size='20sp', bold=True, height=50))
        for db_entity in DATABASE["Entities"]:
            is_unlocked = any(e.name == db_entity.name for e in player.roster)
            if is_unlocked:
                entry = f"📜 {db_entity.name} [{db_entity.origin}]\nPassive: {db_entity.passive_desc}\nLore: {db_entity.lore}"
            else:
                entry = f"🔒 {db_entity.name} [{db_entity.origin}]\n[LORE LOCKED - Summon to reveal entry]"
            
            lbl = make_wrapped_label(entry, font_size='16sp', height=140)
            list_layout.add_widget(lbl)

        list_layout.add_widget(make_wrapped_label("=== URBAN LEGEND BESTIARY ===", font_size='20sp', bold=True, height=50))
        for db_enemy in DATABASE["Bestiary"]:
            is_encountered = db_enemy.name in player.bestiary_unlocked
            if is_encountered:
                entry = f"💀 {db_enemy.name} (Weakness: {db_enemy.weakness})\nLore: {db_enemy.lore}"
            else:
                entry = f"❓ {db_enemy.name}\n[LORE LOCKED - Encounter on The Hunt to reveal]"
            
            lbl = make_wrapped_label(entry, font_size='16sp', height=100)
            list_layout.add_widget(lbl)

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)


class TeamScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label("COVEN & TEAM BUILDING", font_size='24sp', bold=True, size_hint=(1, 0.12)))

        active_text = f"Current Leader: {player.active_leader.name if player.active_leader else 'None'}"
        self.layout.add_widget(make_wrapped_label(active_text, font_size='18sp', size_hint=(1, 0.1)))

        scroll = ScrollView(size_hint=(1, 0.63))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        for entity in player.roster:
            ult = entity.ultimate_spell
            btn_text = (f"Set {entity.name} [{entity.origin}]\nPassive: {entity.passive_desc}\n"
                        f"Ult: {ult.name} (Dmg:{ult.damage}, Cost:{ult.cost}, Blk:{ult.block})")
            btn = Button(text=btn_text, font_size='16sp', halign="center", valign="middle", size_hint_y=None, height=130)
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-20, None)))
            btn.bind(on_press=lambda inst, e=entity: self.set_leader(e))
            list_layout.add_widget(btn)

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def set_leader(self, entity):
        player.active_leader = entity
        player.save_game()
        self.refresh_ui()


class ShopScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)

    def refresh_shop(self):
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label("ALCHEMIST HUT", font_size='26sp', bold=True, size_hint=(1, 0.15)))
        
        status_text = f"Gold: {player.currency}  |  HP: {player.hp}/{player.max_hp}"
        self.layout.add_widget(make_wrapped_label(status_text, font_size='20sp', size_hint=(1, 0.1)))

        btn_heal = Button(text="Buy Healing Salve (+30 HP)\n75 Gold", font_size='18sp', size_hint=(1, 0.2))
        btn_heal.bind(on_press=self.buy_heal)
        self.layout.add_widget(btn_heal)

        btn_spell = Button(text="Buy Random Ritual Spell\n120 Gold", font_size='18sp', size_hint=(1, 0.2))
        btn_spell.bind(on_press=self.buy_spell)
        self.layout.add_widget(btn_spell)

        leave_btn = Button(text="Leave Shop & Continue Path", font_size='18sp', size_hint=(1, 0.2))
        leave_btn.bind(on_press=self.leave_shop)
        self.layout.add_widget(leave_btn)

    def buy_heal(self, instance):
        if player.currency >= 75:
            player.currency -= 75
            player.hp = min(player.max_hp, player.hp + 30)
            player.save_game()
            self.refresh_shop()

    def buy_spell(self, instance):
        if player.currency >= 120:
            player.currency -= 120
            new_spell = random.choice(DATABASE["Spells"])
            player.deck.append(new_spell)
            player.save_game()
            self.refresh_shop()

    def leave_shop(self, instance):
        player.current_tier += 1
        player.save_game()
        self.manager.get_screen('map').refresh_map()
        self.manager.current = 'map'


class GachaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.status_label = make_wrapped_label(
            f"Currency: {player.currency} | Dust: {player.dust}\nReady to summon.",
            font_size='18sp', size_hint=(1, 0.25)
        )
        layout.add_widget(self.status_label)
        
        self.card_image = Image(
            source='assets/summoning_circle.png', 
            size_hint=(1, 0.35), allow_stretch=True, keep_ratio=True
        )
        layout.add_widget(self.card_image)
        
        self.summon_btn = Button(text="Summon (Cost: 100 Gold)", font_size='18sp', size_hint=(1, 0.15))
        self.summon_btn.bind(on_press=self.start_summon)
        layout.add_widget(self.summon_btn)
        
        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15))
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
            ult = pulled.ultimate_spell
            if not any(e.name == pulled.name for e in player.roster):
                player.roster.append(pulled)
                self.status_label.text = (f"Summoned {pulled.origin}: {pulled.name}!\nPassive: {pulled.passive_desc}\n"
                                          f"Ult: {ult.name} [Type: {ult.spell_type} | Dmg: {ult.damage} | Blk: {ult.block} | Cost: {ult.cost}]")
            else:
                player.dust += 25
                self.status_label.text = f"Duplicate {pulled.name}.\nConverted to 25 Arcane Dust!"
                
            if "Lilith" in pulled.name:
                self.card_image.source = 'assets/lilith.png'
            elif "Puck" in pulled.name:
                self.card_image.source = 'assets/puck.png'
            elif "Ophanim" in pulled.name:
                self.card_image.source = 'assets/ophanim.png'
            elif "Chloe" in pulled.name:
                self.card_image.source = 'assets/chloe.png'
            elif "Sam" in pulled.name:
                self.card_image.source = 'assets/sam.png'
            elif "Kelpie" in pulled.name:
                self.card_image.source = 'assets/kelpie.png'
            elif "Mab" in pulled.name:
                self.card_image.source = 'assets/queen_mab.png'
            elif "Metatron" in pulled.name:
                self.card_image.source = 'assets/metatron.png'
            else:
                self.card_image.source = 'assets/card_back.png'
        else:
            pulled = random.choice(DATABASE["Spells"])
            player.deck.append(pulled)
            self.status_label.text = (f"Pulled Spell: {pulled.name}!\nType: {pulled.spell_type} | "
                                      f"Dmg: {pulled.damage} | Blk: {pulled.block} | Cost: {pulled.cost}")
            self.card_image.source = 'assets/card_back.png'
            
        player.save_game()


class HangoutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)

    def refresh_list(self):
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label("COVEN HANGOUT", font_size='24sp', bold=True, size_hint=(1, 0.15)))
        
        if not player.roster:
            self.layout.add_widget(make_wrapped_label("Your coven is empty. Go summon some entities!", font_size='18sp', size_hint=(1, 0.65)))
        else:
            scroll = ScrollView(size_hint=(1, 0.65))
            list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
            list_layout.bind(minimum_height=list_layout.setter('height'))
            
            for entity in player.roster:
                btn_text = f"Talk to {entity.name} (Bond: {entity.bond}/100)"
                btn = Button(text=btn_text, font_size='18sp', halign="center", valign="middle", size_hint_y=None, height=100)
                btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-20, None)))
                btn.bind(on_press=lambda instance, e=entity: self.open_dialogue(e))
                list_layout.add_widget(btn)
            
            scroll.add_widget(list_layout)
            self.layout.add_widget(scroll)
            
        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.2))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)

    def open_dialogue(self, entity):
        self.layout.clear_widgets()
        
        if not entity.dialogues:
            self.layout.add_widget(make_wrapped_label(f"{entity.name} stares at you silently.", font_size='20sp', size_hint=(1, 0.5)))
            btn = Button(text="Leave", font_size='18sp', size_hint=(1, 0.2))
            btn.bind(on_press=lambda x: self.refresh_list())
            self.layout.add_widget(btn)
            return

        dialogue = random.choice(entity.dialogues)
        self.layout.add_widget(make_wrapped_label(f"{entity.name}:\n\"{dialogue['prompt']}\"", font_size='20sp', size_hint=(1, 0.4)))

        options_layout = BoxLayout(orientation='vertical', spacing=15, size_hint=(1, 0.4))
        for opt in dialogue['options']:
            btn = Button(text=opt['text'], font_size='18sp')
            btn.bind(on_press=lambda inst, e=entity, r=opt['reward']: self.resolve_dialogue(e, r))
            options_layout.add_widget(btn)

        self.layout.add_widget(options_layout)

    def resolve_dialogue(self, entity, reward):
        reward_type, val = reward
        result_text = ""
        
        if reward_type == "bond":
            entity.bond += val
            result_text = f"Your bond with {entity.name} increased by {val}!"
            if entity.bond >= 100:
                player.deck.append(entity.ultimate_spell)
                result_text += f"\nMax Bond Reached! You gained the spell: {entity.ultimate_spell.name}."
        elif reward_type == "dust":
            player.dust += val
            result_text = f"You searched the area and found {val} Arcane Dust."
        elif reward_type == "currency":
            player.currency += val
            result_text = f"{entity.name} handed you {val} Gold."

        player.save_game()
        
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label(result_text, font_size='20sp', size_hint=(1, 0.7)))
        
        btn = Button(text="Continue", font_size='18sp', size_hint=(1, 0.3))
        btn.bind(on_press=lambda x: self.refresh_list())
        self.layout.add_widget(btn)


# --- App Runner ---
class DeckbuilderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(MapScreen(name='map'))
        sm.add_widget(TeamScreen(name='team'))
        sm.add_widget(UpgradeScreen(name='upgrade'))
        sm.add_widget(GrimoireScreen(name='grimoire'))
        sm.add_widget(WebScreen(name='web'))
        sm.add_widget(ShopScreen(name='shop'))
        sm.add_widget(GachaScreen(name='gacha'))
        sm.add_widget(HangoutScreen(name='hangout'))
        sm.add_widget(CombatScreen(name='combat'))
        return sm
        
    def on_start(self):
        player.load_game()
        
    def on_pause(self):
        player.save_game()
        return True
        
    def on_stop(self):
        player.save_game()

if __name__ == '__main__':
    DeckbuilderApp().run()
