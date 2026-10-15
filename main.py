from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.utils import platform
from kivy.clock import Clock
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
    def __init__(self, name, hp, weakness, intents, lore, image_file):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.block = 0
        self.burn = 0
        self.poison = 0
        self.weakness = weakness
        self.intents = intents
        self.lore = lore
        self.image_file = image_file

# Expanded Database
DATABASE = {
    "Entities": [
        Entity("Chloe (1 Star)", "Witch", 1, "Heals 3 HP on Fire spells", 
               Spell("Fireball", 15, 2, "Nature", status_effect=("Burn", 5)),
               "A village herbalist who learned to kindle eldritch embers in secret root cellars.",
               dialogues=[
                   {"prompt": "The moon is full. Should we harvest Nightshade or Mandrake tonight?",
                    "options": [{"text": "Nightshade for hexes.", "reward": ("bond", 25)}, {"text": "Mandrake for alchemy.", "reward": ("dust", 30)}]},
                   {"prompt": "The villagers suspect me. They whisper when I buy sulfur.",
                    "options": [{"text": "Let them burn.", "reward": ("currency", 50)}, {"text": "Hide your craft.", "reward": ("bond", 20)}]},
                   {"prompt": "I brewed a potion of absolute truth. Want a sip?",
                    "options": [{"text": "I have nothing to hide.", "reward": ("bond", 30)}, {"text": "Some secrets must stay buried.", "reward": ("dust", 40)}]}
               ]),
        Entity("Sam (2 Star)", "Witch", 2, "+10% Shadow damage", 
               Spell("Shadow Strike", 30, 3, "Shadow", status_effect=("Poison", 4)),
               "A solitary hedge witch capable of weaving twilight into deadly piercing blades.",
               dialogues=[
                   {"prompt": "The shadows are restless. Do you fear the dark?",
                    "options": [{"text": "I embrace it.", "reward": ("bond", 25)}, {"text": "It hides our enemies.", "reward": ("currency", 50)}]},
                   {"prompt": "A rusted dagger is better than a holy sword if you know where to strike.",
                    "options": [{"text": "Show me the strike.", "reward": ("bond", 30)}, {"text": "I prefer magic.", "reward": ("dust", 20)}]},
                   {"prompt": "They burned my coven. I will not forget.",
                    "options": [{"text": "We will have vengeance.", "reward": ("bond", 35)}, {"text": "Focus on the Hunt.", "reward": ("dust", 30)}]}
               ]),
        Entity("Lilith (3 Star)", "Witch", 3, "Start combat with +1 Mana", 
               Spell("Obliterate", 100, 5, "Shadow"),
               "The ancient grand witch of dark arcana, commanding supreme shadow geometry.",
               dialogues=[
                   {"prompt": "True power requires blood sacrifice. What will you offer?",
                    "options": [{"text": "My own blood.", "reward": ("bond", 35)}, {"text": "The blood of my foes.", "reward": ("dust", 50)}]},
                   {"prompt": "Mortal lifespans are a blink. Why do you struggle so hard?",
                    "options": [{"text": "To leave a legacy.", "reward": ("bond", 20)}, {"text": "Because it's all I have.", "reward": ("bond", 40)}]},
                   {"prompt": "Look into the abyss with me.",
                    "options": [{"text": "[Stare into the Void]", "reward": ("dust", 60)}, {"text": "[Avert your eyes]", "reward": ("currency", 100)}]}
               ]),
        Entity("Puck (1 Star)", "Fae", 1, "Draw +1 card at battle start", 
               Spell("Trickster Spark", 12, 1, "Nature"),
               "An elusive woodland spirit whose laughter bends probability and misdirects travelers.",
               dialogues=[
                   {"prompt": "Pick a hand, mortal! Left or Right?",
                    "options": [{"text": "Left.", "reward": ("dust", 20)}, {"text": "Right.", "reward": ("bond", 25)}]},
                   {"prompt": "I stole the Alchemist's glasses! Should I throw them in the river?",
                    "options": [{"text": "Do it. Chaos!", "reward": ("bond", 30)}, {"text": "Return them.", "reward": ("currency", 40)}]},
                   {"prompt": "If you chase a wisp, where do you end up?",
                    "options": [{"text": "In a swamp.", "reward": ("bond", 20)}, {"text": "Exactly where you need to be.", "reward": ("bond", 35)}]}
               ]),
        Entity("The Kelpie (2 Star)", "Fae", 2, "Enemies take 15% more damage", 
               Spell("Drowning Depths", 35, 3, "Nature"),
               "A shapeshifting water demon of Scottish lochs that drags the unwary beneath dark waters.",
               dialogues=[
                   {"prompt": "The water is so very cold... come closer.",
                    "options": [{"text": "Step back.", "reward": ("dust", 25)}, {"text": "Offer an apple.", "reward": ("bond", 25)}]},
                   {"prompt": "[The beast nudges its bridle toward your hand.]",
                    "options": [{"text": "Mount the beast.", "reward": ("bond", 40)}, {"text": "Refuse the trap.", "reward": ("currency", 60)}]}
               ]),
        Entity("Queen Mab (3 Star)", "Fae", 3, "Steals 1 enemy intent turn", 
               Spell("Nightmare Realm", 75, 4, "Shadow"),
               "Monarch of the Unseelie court, governing bad dreams, illusions, and nocturnal oaths.",
               dialogues=[
                   {"prompt": "Will you swear fealty to the winter court?",
                    "options": [{"text": "Yes, my Queen.", "reward": ("bond", 35)}, {"text": "I serve no one.", "reward": ("dust", 50)}]},
                   {"prompt": "Dreams are more real than the waking world. Which do you prefer?",
                    "options": [{"text": "The Dream.", "reward": ("bond", 25)}, {"text": "The Waking World.", "reward": ("currency", 50)}]}
               ]),
        Entity("Ophanim (2 Star)", "Angel", 2, "Gain 5 Block each turn", 
               Spell("Wheel of Eyes", 25, 2, "Divine", block=15),
               "A celestial ring of spinning golden wheels lined with a hundred vigilant eyes.",
               dialogues=[
                   {"prompt": "BE NOT AFRAID.",
                    "options": [{"text": "I am not afraid.", "reward": ("bond", 25)}, {"text": "I am terrified.", "reward": ("currency", 75)}]},
                   {"prompt": "WE SEE ALL SINS. YOURS ARE MANY.",
                    "options": [{"text": "Judge me then.", "reward": ("bond", 30)}, {"text": "I seek redemption.", "reward": ("dust", 40)}]}
               ]),
        Entity("Metatron (3 Star)", "Angel", 3, "Purges enemy buffs", 
               Spell("Wrath of Heaven", 120, 6, "Divine", block=30),
               "The supreme voice of the heavens whose spoken word incinerates unholy hexes.",
               dialogues=[
                   {"prompt": "The scales of reality must be balanced.",
                    "options": [{"text": "Then balance them.", "reward": ("bond", 25)}, {"text": "Break the scales.", "reward": ("dust", 50)}]},
                   {"prompt": "Mortal flesh is weak. Ascension requires burning away the rot.",
                    "options": [{"text": "Burn me.", "reward": ("bond", 40)}, {"text": "My flesh is my strength.", "reward": ("currency", 80)}]}
               ])
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
              "A lingering spirit born of old woods.", "woodland_shade.png"),
        Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20)], 
              "A winged red-eyed harbinger of disaster.", "mothman_legend.png")
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
            'currency': self.currency, 'dust': self.dust, 'hp': self.hp, 'max_hp': self.max_hp,
            'current_tier': self.current_tier, 'bestiary_unlocked': self.bestiary_unlocked,
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
            
            self.roster = []
            for saved_ent in data.get('roster', []):
                for db_ent in DATABASE['Entities']:
                    if db_ent.name == saved_ent['name']:
                        db_ent.bond = saved_ent.get('bond', 0)
                        self.roster.append(db_ent)
                        
            leader_name = data.get('active_leader')
            if leader_name:
                self.active_leader = next((e for e in self.roster if e.name == leader_name), None)
                
            self.deck = []
            for s in data.get('deck', []):
                status_eff = s.get('status_effect')
                if status_eff: status_eff = tuple(status_eff)
                self.deck.append(Spell(s['name'], s['damage'], s['cost'], s['spell_type'], s.get('block', 0), status_eff, s.get('level', 1)))

player = PlayerState()

def make_wrapped_label(text, font_size='18sp', bold=False, color=(1, 1, 1, 1), size_hint=(1, None), height=80):
    lbl = Label(
        text=text, font_size=font_size, bold=bold, color=color,
        halign="center", valign="middle", size_hint=size_hint
    )
    if size_hint[1] is None: lbl.height = height
    lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0] - 20, None)))
    return lbl

# --- Screens ---

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)
        layout.add_widget(make_wrapped_label("URBAN LEGEND DECKBUILDER", font_size='28sp', bold=True, size_hint=(1, 0.2)))
        
        buttons = [
            ("Enter The Hunt (Combat Map)", self.go_to_map),
            ("Coven & Team Building", self.go_to_team),
            ("Arcane Dust Upgrade Shrine", self.go_to_upgrade),
            ("The Esoteric Grimoire", self.go_to_grimoire),
            ("3D Summoning Ritual (Gacha)", lambda x: setattr(self.manager, 'current', 'gacha')),
            ("Hangout (Friendship)", self.go_to_hangout)
        ]
        
        for text, callback in buttons:
            btn = Button(text=text, font_size='18sp', size_hint=(1, 0.13))
            btn.bind(on_press=callback)
            layout.add_widget(btn)
            
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
                text_col = (1, 1, 1, 1)
                if tier_idx < player.current_tier:
                    btn_text = f"✓ {node['label']}"
                    btn_color = (0.3, 0.7, 0.3, 1)
                    is_disabled = True
                elif tier_idx == player.current_tier:
                    btn_text = f"▶ {node['label']}"
                    btn_color = (0.9, 0.6, 0.2, 1)
                    text_col = (0, 0, 0, 1) # High contrast text
                    is_disabled = False
                else:
                    btn_text = f"🔒 {node['label']}"
                    btn_color = (0.3, 0.3, 0.35, 1)
                    is_disabled = True

                btn = Button(text=btn_text, font_size='16sp', bold=True, background_color=btn_color, disabled=is_disabled, color=text_col)
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
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        self.enemy = None
        self.mana = 3
        self.hand = []
        self.combat_log = "An enemy blocks your path!"
        self.webview = None
        
        self.web_placeholder = BoxLayout(size_hint=(1, 0.45))
        self.layout.add_widget(self.web_placeholder)
        
        self.ui_panel = BoxLayout(orientation='vertical', size_hint=(1, 0.55), spacing=8)
        self.layout.add_widget(self.ui_panel)
        self.add_widget(self.layout)

    def on_enter(self):
        if platform == 'android':
            self.load_android_webview()
        else:
            self.web_placeholder.clear_widgets()
            self.web_placeholder.add_widget(make_wrapped_label("[3D Combat Engine Active]\nCompiling to APK activates the transparent 3D Battle Engine here.", font_size='14sp'))

    def on_leave(self):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def remove_wv():
                if self.webview:
                    parent = self.webview.getParent()
                    if parent: parent.removeView(self.webview)
                    self.webview = None
            remove_wv()

    def load_android_webview(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            DisplayMetrics = autoclass('android.util.DisplayMetrics')
            LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
            
            activity = PythonActivity.mActivity
            metrics = DisplayMetrics()
            activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)
            w = metrics.widthPixels
            h = metrics.heightPixels

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                settings = self.webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setAllowFileAccess(True)
                settings.setAllowFileAccessFromFileURLs(True)
                settings.setAllowUniversalAccessFromFileURLs(True)
                
                self.webview.setBackgroundColor(0)
                self.webview.setWebViewClient(WebViewClient())
                
                html_path = os.path.abspath(os.path.join('assets', 'combat.html'))
                self.webview.loadUrl(f'file://{html_path}')
                
                params = LayoutParams(w, int(h * 0.45))
                activity.addContentView(self.webview, params)
                
                # Push initial combat state
                self.sync_js_state()

            create_webview()
        except Exception as e:
            self.web_placeholder.add_widget(make_wrapped_label(f"WebView Error: {str(e)}", font_size='14sp'))

    def start_combat(self, is_boss=False):
        if is_boss:
            self.enemy = Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20)], DATABASE["Bestiary"][1].lore, DATABASE["Bestiary"][1].image_file)
        else:
            self.enemy = Enemy("Woodland Shade", 60, "Divine", [("Attack", 12)], DATABASE["Bestiary"][0].lore, DATABASE["Bestiary"][0].image_file)
            
        if self.enemy.name not in player.bestiary_unlocked:
            player.bestiary_unlocked.append(self.enemy.name)
            player.save_game()

        player.block = 0
        self.combat_log = f"A wild {self.enemy.name} appears!"
        self.mana = 4 if (player.active_leader and "Lilith" in player.active_leader.name) else 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui()
        self.sync_js_state()

    def sync_js_state(self):
        if platform == 'android' and getattr(self, 'webview', None):
            payload = {
                "enemyName": self.enemy.name,
                "enemyHp": self.enemy.hp,
                "enemyMaxHp": self.enemy.max_hp,
                "enemyImg": self.enemy.image_file
            }
            json_data = json.dumps(payload)
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                self.webview.evaluateJavascript(f"updateCombatState({json_data});", None)
            trigger()

    def trigger_js_attack(self, attacker="player"):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                self.webview.evaluateJavascript(f"playAttackAnim('{attacker}');", None)
            trigger()

    def update_ui(self, disable_input=False):
        self.ui_panel.clear_widgets()
        
        if self.enemy.hp <= 0:
            player.currency += 120
            player.current_tier += 1
            player.save_game()
            self.ui_panel.add_widget(make_wrapped_label(f"VICTORY!\nThe {self.enemy.name} was defeated.\nEarned 120 Gold!", font_size='28sp', bold=True, color=(1, 0.8, 0.2, 1), size_hint=(1, 0.6)))
            back_btn = Button(text="Continue Path", font_size='22sp', size_hint=(1, 0.4))
            back_btn.bind(on_press=self.finish_combat)
            self.ui_panel.add_widget(back_btn)
            return

        if player.hp <= 0:
            self.ui_panel.add_widget(make_wrapped_label("YOU WERE DEFEATED...", font_size='32sp', bold=True, size_hint=(1, 0.6)))
            back_btn = Button(text="Return to Menu", font_size='22sp', size_hint=(1, 0.4))
            back_btn.bind(on_press=self.reset_run)
            self.ui_panel.add_widget(back_btn)
            return

        status_text = f"Your HP: {player.hp}/{player.max_hp} (Shield: {player.block})  |  Mana: {self.mana}\nEnemy Statuses: Burn ({self.enemy.burn}) | Poison ({self.enemy.poison})"
        self.ui_panel.add_widget(make_wrapped_label(status_text, font_size='14sp', bold=True, size_hint=(1, 0.2)))

        log_bg = BoxLayout(size_hint=(1, 0.15))
        log_bg.add_widget(make_wrapped_label(self.combat_log, font_size='15sp', color=(0.4, 0.9, 1, 1), bold=True))
        self.ui_panel.add_widget(log_bg)

        cards_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.45))
        for spell in self.hand:
            btn_text = f"{spell.name}\n[{spell.spell_type}]\nDmg: {spell.damage}\nCost: {spell.cost}"
            btn = Button(text=btn_text, font_size='14sp', halign="center", valign="middle", disabled=disable_input)
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-10, None)))
            btn.bind(on_press=lambda instance, s=spell, b=btn: self.cast_spell(s, b))
            cards_layout.add_widget(btn)
        self.ui_panel.add_widget(cards_layout)
        
        nav_row = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.2))
        flee_btn = Button(text="Retreat", font_size='18sp', disabled=disable_input)
        flee_btn.bind(on_press=self.retreat_combat)
        end_turn_btn = Button(text="End Turn", font_size='18sp', background_color=(0.2, 0.6, 0.8, 1), disabled=disable_input)
        end_turn_btn.bind(on_press=self.enemy_turn)
        nav_row.add_widget(flee_btn)
        nav_row.add_widget(end_turn_btn)
        self.ui_panel.add_widget(nav_row)
        
        self.sync_js_state()

    def cast_spell(self, spell, btn_widget):
        if self.mana >= spell.cost:
            self.trigger_js_attack("player")
            
            self.mana -= spell.cost
            player.block += spell.block
            mult = 1.5 if spell.spell_type == self.enemy.weakness else 1.0
            dmg = int(spell.damage * mult)
            self.enemy.hp -= dmg
            
            self.combat_log = f"Cast {spell.name} dealing {dmg} damage!"
            if spell.status_effect:
                eff, val = spell.status_effect
                if eff == "Burn": self.enemy.burn += val
                elif eff == "Poison": self.enemy.poison += val
                self.combat_log += f" Applied {val} {eff}."

            self.hand.remove(spell)
            self.update_ui()

    def enemy_turn(self, instance):
        self.combat_log = f"{self.enemy.name} is preparing to attack..."
        self.update_ui(disable_input=True)
        Clock.schedule_once(self.resolve_enemy_turn, 1.0)

    def resolve_enemy_turn(self, dt):
        self.trigger_js_attack("enemy")
        
        if self.enemy.burn > 0:
            self.enemy.hp -= self.enemy.burn
            self.enemy.burn = max(0, self.enemy.burn - 1)
        if self.enemy.poison > 0:
            self.enemy.hp -= self.enemy.poison

        raw_damage = 12
        damage_to_hp = max(0, raw_damage - player.block)
        player.block = max(0, player.block - raw_damage)
        player.hp -= damage_to_hp

        self.combat_log = f"{self.enemy.name} attacks! You take {damage_to_hp} damage.\nYour turn."
        self.mana = 4 if (player.active_leader and "Lilith" in player.active_leader.name) else 3
        self.hand = random.sample(player.deck, min(3, len(player.deck)))
        self.update_ui(disable_input=False)

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


class GachaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.webview = None
        
        self.web_placeholder = BoxLayout(size_hint=(1, 0.65))
        self.layout.add_widget(self.web_placeholder)
        
        control_panel = BoxLayout(orientation='vertical', size_hint=(1, 0.35), padding=10, spacing=10)
        self.status_label = make_wrapped_label(f"Gold: {player.currency} | Dust: {player.dust}\nTap 'Commence Ritual' to summon.", font_size='16sp', size_hint=(1, 0.4))
        control_panel.add_widget(self.status_label)
        
        self.summon_btn = Button(text="Commence Ritual (100 Gold)", font_size='18sp', size_hint=(1, 0.3), background_color=(0, 0.7, 0.9, 1))
        self.summon_btn.bind(on_press=self.start_summon)
        control_panel.add_widget(self.summon_btn)
        
        back_btn = Button(text="Leave Ritual Chamber", font_size='18sp', size_hint=(1, 0.3))
        back_btn.bind(on_press=self.go_back)
        control_panel.add_widget(back_btn)
        
        self.layout.add_widget(control_panel)
        self.add_widget(self.layout)

    def on_enter(self):
        self.status_label.text = f"Gold: {player.currency} | Dust: {player.dust}\nTap 'Commence Ritual' to summon."
        if platform == 'android':
            self.load_android_webview()
        else:
            self.web_placeholder.clear_widgets()
            self.web_placeholder.add_widget(make_wrapped_label("[3D Summoning Engine Active]", font_size='16sp'))

    def on_leave(self):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def remove_wv():
                if self.webview:
                    parent = self.webview.getParent()
                    if parent: parent.removeView(self.webview)
                    self.webview = None
            remove_wv()

    def load_android_webview(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            DisplayMetrics = autoclass('android.util.DisplayMetrics')
            LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
            
            activity = PythonActivity.mActivity
            metrics = DisplayMetrics()
            activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)
            w = metrics.widthPixels
            h = metrics.heightPixels

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                settings = self.webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setAllowFileAccess(True)
                self.webview.setBackgroundColor(0)
                self.webview.setWebViewClient(WebViewClient())
                
                html_path = os.path.abspath(os.path.join('assets', 'index.html'))
                self.webview.loadUrl(f'file://{html_path}')
                
                params = LayoutParams(w, int(h * 0.65))
                activity.addContentView(self.webview, params)

            create_webview()
        except Exception as e:
            pass

    def go_back(self, instance):
        self.manager.current = 'menu'

    def start_summon(self, instance):
        if player.currency < 100:
            self.status_label.text = "Not enough gold!"
            return
            
        player.currency -= 100
        self.summon_btn.disabled = True
        Clock.schedule_once(lambda dt: setattr(self.summon_btn, 'disabled', False), 2.5)
        
        img_map = {
            "Chloe": "chloe.png", "Sam": "sam.png", "Lilith": "lilith.png", 
            "Puck": "puck.png", "Kelpie": "kelpie.png", "Mab": "queen_mab.png", 
            "Ophanim": "ophanim.png", "Metatron": "metatron.png"
        }
        
        if random.random() < 0.4:
            pulled = random.choice(DATABASE["Entities"])
            ult = pulled.ultimate_spell
            img_file = next((v for k, v in img_map.items() if k in pulled.name), "card_back.png")
            
            if not any(e.name == pulled.name for e in player.roster):
                player.roster.append(pulled)
                self.status_label.text = f"Summoned {pulled.name}!\nPassive: {pulled.passive_desc}"
            else:
                player.dust += 25
                self.status_label.text = f"Duplicate {pulled.name}.\nConverted to 25 Arcane Dust!"
                
            self.trigger_js_animation(img_file, pulled.name)
        else:
            pulled = random.choice(DATABASE["Spells"])
            player.deck.append(pulled)
            self.status_label.text = f"Pulled Spell: {pulled.name}!\nDmg: {pulled.damage} | Blk: {pulled.block}"
            self.trigger_js_animation("card_back.png", pulled.name)
            
        player.save_game()

    def trigger_js_animation(self, img_file, entity_name):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                self.webview.evaluateJavascript(f"triggerSummon('{img_file}', '{entity_name}');", None)
            trigger()


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
