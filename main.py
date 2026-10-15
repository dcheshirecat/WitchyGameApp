from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.animation import Animation
from kivy.utils import platform
from kivy.clock import Clock
import random
import json
import os
import urllib.parse

# --- Core Data Structures ---

class Spell:
    def __init__(self, name, damage, cost, spell_type="Nature", block=0, status_effect=None, level=1):
        self.name = name; self.damage = damage; self.cost = cost; self.spell_type = spell_type; self.block = block; self.status_effect = status_effect; self.level = level

class Entity:
    def __init__(self, name, origin, rarity, passive_desc, ultimate_spell, lore, image_file, dialogues=None):
        self.name = name; self.origin = origin; self.rarity = rarity; self.passive_desc = passive_desc; self.ultimate_spell = ultimate_spell
        self.lore = lore; self.image_file = image_file; self.bond = 0; self.current_hp = 50; self.max_hp = 50; self.dialogues = dialogues or []

class Enemy:
    def __init__(self, name, hp, weakness, intents, lore, image_file):
        self.name = name; self.max_hp = hp; self.hp = hp; self.block = 0; self.burn = 0; self.poison = 0; self.weakness = weakness; self.intents = intents; self.lore = lore; self.image_file = image_file

# Expanded Database
DATABASE = {
    "Entities": [
        Entity("Chloe (1 Star)", "Witch", 1, "Heals 3 HP on Fire spells", Spell("Fireball", 15, 2, "Nature", status_effect=("Burn", 5)), "Village herbalist.", "chloe.png", dialogues=[
            {"prompt": "The moon is full. Should we harvest Nightshade or Mandrake tonight?", "options": [{"text": "Nightshade.", "reward": ("bond", 25)}, {"text": "Mandrake.", "reward": ("dust", 30)}]}
        ]),
        Entity("Sam (2 Star)", "Witch", 2, "+10% Shadow damage", Spell("Shadow Strike", 30, 3, "Shadow", status_effect=("Poison", 4)), "Solitary hedge witch.", "sam.png", dialogues=[
            {"prompt": "The shadows are restless. Do you fear the dark?", "options": [{"text": "I embrace it.", "reward": ("bond", 25)}, {"text": "It hides our enemies.", "reward": ("currency", 50)}]}
        ]),
        Entity("Lilith (3 Star)", "Witch", 3, "Start combat with +1 Mana", Spell("Obliterate", 100, 5, "Shadow"), "Ancient grand witch.", "lilith.png", dialogues=[
            {"prompt": "True power requires sacrifice.", "options": [{"text": "My blood.", "reward": ("bond", 35)}, {"text": "Their blood.", "reward": ("dust", 50)}]}
        ]),
        Entity("Puck (1 Star)", "Fae", 1, "Draw +1 card at battle start", Spell("Trickster Spark", 12, 1, "Nature"), "Elusive woodland spirit.", "puck.png", dialogues=[
            {"prompt": "Pick a hand, mortal! Left or Right?", "options": [{"text": "Left.", "reward": ("dust", 20)}, {"text": "Right.", "reward": ("bond", 25)}]}
        ]),
        Entity("The Kelpie (2 Star)", "Fae", 2, "Enemies take 15% more damage", Spell("Drowning Depths", 35, 3, "Nature"), "A shapeshifting water demon.", "kelpie.png", dialogues=[
            {"prompt": "The water is cold... come closer.", "options": [{"text": "Step back.", "reward": ("dust", 25)}, {"text": "Offer an apple.", "reward": ("bond", 25)}]}
        ]),
        Entity("Queen Mab (3 Star)", "Fae", 3, "Steals 1 enemy intent turn", Spell("Nightmare Realm", 75, 4, "Shadow"), "Monarch of the Unseelie court.", "queen_mab.png", dialogues=[
            {"prompt": "Will you swear fealty?", "options": [{"text": "Yes, my Queen.", "reward": ("bond", 35)}, {"text": "I serve no one.", "reward": ("dust", 50)}]}
        ]),
        Entity("Ophanim (2 Star)", "Angel", 2, "Gain 5 Block each turn", Spell("Wheel of Eyes", 25, 2, "Divine", block=15), "A celestial ring of spinning wheels.", "ophanim.png", dialogues=[
            {"prompt": "BE NOT AFRAID.", "options": [{"text": "I am not afraid.", "reward": ("bond", 25)}, {"text": "I am terrified.", "reward": ("currency", 75)}]}
        ]),
        Entity("Metatron (3 Star)", "Angel", 3, "Purges enemy buffs", Spell("Wrath of Heaven", 120, 6, "Divine", block=30), "Supreme voice of the heavens.", "metatron.png", dialogues=[
            {"prompt": "The scales of reality must be balanced.", "options": [{"text": "Balance them.", "reward": ("bond", 25)}, {"text": "Break the scales.", "reward": ("dust", 50)}]}
        ])
    ],
    "Spells": [
        Spell("Basic Strike", 5, 1, "Nature"), Spell("Zap", 5, 1, "Divine"), 
        Spell("Punch", 10, 1, "Nature"), Spell("Magic Missile", 20, 2, "Divine"),
        Spell("Hex of Rot", 12, 2, "Shadow", status_effect=("Poison", 3)), Spell("Holy Barrier", 0, 2, "Divine", block=20)
    ],
    "Bestiary": [
        Enemy("Woodland Shade", 60, "Divine", [("Attack", 10)], "A lingering spirit.", "woodland_shade.png"),
        Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20)], "A winged harbinger.", "mothman_legend.png")
    ]
}

class PlayerState:
    def __init__(self):
        self.currency = 500
        self.dust = 100
        self.roster = []
        self.team = [] # The active combat team (Max 3)
        self.bestiary_unlocked = []
        self.current_tier = 0
        self.mana = 3
        self.block = 0
        self.map_nodes = [
            {"id": 0, "type": "Crossroads", "label": "Path Alpha", "pos": (0.3, 0.2)},
            {"id": 1, "type": "Alchemist Shop", "label": "Apothecary", "pos": (0.7, 0.4)},
            {"id": 2, "type": "Shrine", "label": "Sacred Spring", "pos": (0.3, 0.6)},
            {"id": 3, "type": "Boss", "label": "The Fog", "pos": (0.5, 0.85)}
        ]

    def save_game(self):
        app = App.get_running_app()
        if not app: return
        save_path = os.path.join(app.user_data_dir, 'savegame.json')
        data = {
            'currency': self.currency, 'dust': self.dust, 'current_tier': self.current_tier, 'bestiary_unlocked': self.bestiary_unlocked,
            'roster': [{'name': e.name, 'bond': e.bond, 'hp': e.current_hp} for e in self.roster],
            'team': [e.name for e in self.team]
        }
        try:
            with open(save_path, 'w') as f:
                json.dump(data, f)
        except Exception: pass

    def load_game(self):
        app = App.get_running_app()
        if not app: return
        save_path = os.path.join(app.user_data_dir, 'savegame.json')
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r') as f: data = json.load(f)
                self.currency = data.get('currency', 500)
                self.dust = data.get('dust', 100)
                self.current_tier = data.get('current_tier', 0)
                self.bestiary_unlocked = data.get('bestiary_unlocked', [])
                
                self.roster = []
                for saved_ent in data.get('roster', []):
                    for db_ent in DATABASE['Entities']:
                        if db_ent.name == saved_ent['name']:
                            db_ent.bond = saved_ent.get('bond', 0)
                            db_ent.current_hp = saved_ent.get('hp', 50)
                            self.roster.append(db_ent)
                            
                self.team = []
                for t_name in data.get('team', []):
                    ent = next((e for e in self.roster if e.name == t_name), None)
                    if ent: self.team.append(ent)
            except Exception: pass

player = PlayerState()

def make_wrapped_label(text, font_size='18sp', bold=False, color=(1, 1, 1, 1), size_hint=(1, None), height=80):
    lbl = Label(text=text, font_size=font_size, bold=bold, color=color, halign="center", valign="middle", size_hint=size_hint)
    if size_hint[1] is None: lbl.height = height
    lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0] - 20, None)))
    return lbl

# --- Screens ---

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        
        # New Presplash background
        bg_path = 'presplash.png' if os.path.exists('presplash.png') else 'assets/card_back.png'
        self.layout.add_widget(Image(source=bg_path, allow_stretch=True, keep_ratio=False, size_hint=(1, 1)))
        
        self.label = make_wrapped_label("Summoning the Coven...", font_size='24sp', bold=True, size_hint=(1, 0.2), height=100)
        self.label.pos_hint = {'center_x': 0.5, 'y': 0.1}
        self.layout.add_widget(self.label)
        self.add_widget(self.layout)

    def on_enter(self):
        anim = Animation(opacity=0.2, duration=0.6) + Animation(opacity=1.0, duration=0.6)
        anim.repeat = True
        anim.start(self.label)
        Clock.schedule_once(self.go_to_menu, 2.5)

    def go_to_menu(self, dt):
        self.manager.current = 'menu'


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)
        layout.add_widget(make_wrapped_label("URBAN LEGEND DECKBUILDER", font_size='28sp', bold=True, size_hint=(1, 0.2)))
        
        buttons = [
            ("Enter The Hunt (Interactive Map)", lambda x: setattr(self.manager, 'current', 'map')),
            ("Coven & Team Building", lambda x: setattr(self.manager, 'current', 'team')),
            ("Arcane Dust Upgrade Shrine", lambda x: setattr(self.manager, 'current', 'upgrade')),
            ("The Esoteric Grimoire", lambda x: setattr(self.manager, 'current', 'grimoire')),
            ("3D Summoning Ritual (Gacha)", lambda x: setattr(self.manager, 'current', 'gacha')),
            ("Hangout (Friendship)", lambda x: setattr(self.manager, 'current', 'hangout'))
        ]
        
        for text, cb in buttons:
            btn = Button(text=text, font_size='18sp', size_hint=(1, 0.13))
            btn.bind(on_press=cb)
            layout.add_widget(btn)
        self.add_widget(layout)


class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)

    def on_enter(self):
        self.refresh_map()

    def refresh_map(self):
        self.layout.clear_widgets()
        
        # Lower Opacity Map Background
        bg_path = 'assets/map_bg.png' if os.path.exists('assets/map_bg.png') else 'assets/card_back.png'
        bg = Image(source=bg_path, allow_stretch=True, keep_ratio=False, size_hint=(1, 1), pos_hint={'x':0, 'y':0}, color=(1, 1, 1, 0.4))
        self.layout.add_widget(bg)
        
        ui_box = BoxLayout(orientation='vertical', size_hint=(1, 1))
        stats_text = f"Gold: {player.currency} | Dust: {player.dust}\nActive Coven Size: {len(player.team)}/3"
        ui_box.add_widget(make_wrapped_label(stats_text, font_size='18sp', bold=True, size_hint=(1, 0.15), color=(1,0.9,0.5,1)))
        ui_box.add_widget(BoxLayout(size_hint=(1, 0.75)))
        back_btn = Button(text="Return to Menu", font_size='18sp', size_hint=(1, 0.1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        ui_box.add_widget(back_btn)
        self.layout.add_widget(ui_box)

        for idx, node in enumerate(player.map_nodes):
            is_active = (idx == player.current_tier)
            is_cleared = (idx < player.current_tier)
            
            orb_box = BoxLayout(orientation='vertical', size_hint=(None, None), size=(120, 100))
            orb_box.pos_hint = {'center_x': node['pos'][0], 'center_y': node['pos'][1]}
            btn_color = (0.3, 0.8, 0.3, 1) if is_cleared else (0, 0.8, 1, 1) if is_active else (0.4, 0.4, 0.4, 1)
            
            orb_path = 'assets/map_node.png' if os.path.exists('assets/map_node.png') else 'atlas://data/images/defaulttheme/button'
            orb_btn = Button(background_normal=orb_path, background_color=btn_color, size_hint=(1, 0.7), disabled=not is_active)
            orb_btn.bind(on_press=lambda inst, n=node['type']: self.enter_node(n))
            if is_active:
                anim = Animation(opacity=0.4, duration=0.8) + Animation(opacity=1.0, duration=0.8)
                anim.repeat = True; anim.start(orb_btn)
            orb_box.add_widget(orb_btn)
            
            lbl_color = (1,1,1,1) if is_active else (0.7,0.7,0.7,1)
            orb_box.add_widget(Label(text=node['label'], font_size='14sp', bold=True, size_hint=(1, 0.3), color=lbl_color))
            self.layout.add_widget(orb_box)

    def enter_node(self, node_type):
        if len(player.team) == 0:
            # Need a team to progress! Route to team builder.
            self.manager.current = 'team'
            return
            
        if node_type in ["Crossroads", "Boss"]:
            self.manager.get_screen('combat').start_combat(is_boss=(node_type == "Boss"))
            self.manager.current = 'combat'
        elif node_type == "Alchemist Shop":
            self.manager.get_screen('shop').refresh_shop()
            self.manager.current = 'shop'
        elif node_type == "Shrine":
            for e in player.team: e.current_hp = min(e.max_hp, e.current_hp + 20)
            player.current_tier += 1
            player.save_game()
            self.refresh_map()


class TeamScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.webview = None
        self.web_placeholder = BoxLayout(size_hint=(1, 0.7))
        self.layout.add_widget(self.web_placeholder)
        
        self.team_label = make_wrapped_label("Current Coven: None", font_size='16sp', size_hint=(1, 0.15))
        self.layout.add_widget(self.team_label)
        
        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15))
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)
        self.add_widget(self.layout)

    def on_enter(self):
        self.update_team_label()
        if platform == 'android':
            self.load_android_webview()
        else:
            self.web_placeholder.clear_widgets()
            self.web_placeholder.add_widget(make_wrapped_label("[3D Gallery Active]\nCompile to APK to view.", font_size='16sp'))

    def update_team_label(self):
        if not player.team: self.team_label.text = "Current Coven: None (Select up to 3)"
        else: self.team_label.text = "Current Coven:\n" + ", ".join([e.name for e in player.team])

    def add_to_team(self, char_name):
        ent = next((e for e in player.roster if e.name == char_name), None)
        if ent:
            # Toggle logic
            if ent in player.team:
                player.team.remove(ent)
            elif len(player.team) < 3:
                player.team.append(ent)
        player.save_game()
        self.update_team_label()

    def on_leave(self):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            wv = self.webview; self.webview = None
            @run_on_ui_thread
            def remove_wv():
                try:
                    wv.setVisibility(8); wv.loadUrl("about:blank"); parent = wv.getParent()
                    if parent: parent.removeView(wv)
                    wv.destroy()
                except Exception: pass
            remove_wv()

    def load_android_webview(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android.runnable import run_on_ui_thread
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = autoclass('android.util.DisplayMetrics')()
            activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)

            class CustomClient(PythonJavaClass):
                __javainterfaces__ = ['android/webkit/WebViewClient']
                __javacontext__ = 'app'
                @java_method('(Landroid/webkit/WebView;Ljava/lang/String;)Z')
                def shouldOverrideUrlLoading(self, view, url):
                    if url.startswith("kivy://select_team"):
                        parsed = urllib.parse.urlparse(url)
                        char_name = urllib.parse.parse_qs(parsed.query)['name'][0]
                        Clock.schedule_once(lambda dt: App.get_running_app().root.get_screen('team').add_to_team(char_name))
                        return True
                    return False

            roster_data = [{"name": e.name, "img": e.image_file, "passive": e.passive_desc, "ult_name": e.ultimate_spell.name, "dmg": e.ultimate_spell.damage, "cost": e.ultimate_spell.cost, "blk": e.ultimate_spell.block, "hp": e.current_hp, "max_hp": e.max_hp} for e in player.roster]
            json_data = json.dumps(roster_data)

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True)
                self.webview.getSettings().setAllowFileAccess(True)
                self.webview.setBackgroundColor(0)
                self.client = CustomClient()
                self.webview.setWebViewClient(self.client)
                html_path = os.path.abspath(os.path.join('assets', 'gallery.html'))
                self.webview.loadUrl(f'file://{html_path}')
                self.webview.evaluateJavascript(f"loadGallery('{json_data}');", None)
                params = autoclass('android.view.ViewGroup$LayoutParams')(metrics.widthPixels, int(metrics.heightPixels * 0.7))
                activity.addContentView(self.webview, params)
            create_webview()
        except Exception: pass

    def go_back(self, instance):
        self.manager.current = 'menu'


class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        self.enemy = None
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
            self.web_placeholder.add_widget(make_wrapped_label("[3D Combat Engine Active]\nCompiling to APK activates Web Engine here.", font_size='14sp'))

    def on_leave(self):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            wv = self.webview
            self.webview = None
            @run_on_ui_thread
            def remove_wv():
                try:
                    wv.setVisibility(8); wv.loadUrl("about:blank")
                    parent = wv.getParent(); 
                    if parent: parent.removeView(wv)
                    wv.destroy()
                except Exception: pass
            remove_wv()

    def load_android_webview(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = autoclass('android.util.DisplayMetrics')()
            activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True)
                self.webview.getSettings().setAllowFileAccess(True)
                self.webview.getSettings().setAllowFileAccessFromFileURLs(True)
                self.webview.setBackgroundColor(0)
                self.webview.setWebViewClient(WebViewClient())
                
                html_path = os.path.abspath(os.path.join('assets', 'combat.html'))
                if os.path.exists(html_path):
                    self.webview.loadUrl(f'file://{html_path}')
                
                params = autoclass('android.view.ViewGroup$LayoutParams')(metrics.widthPixels, int(metrics.heightPixels * 0.45))
                activity.addContentView(self.webview, params)
                self.sync_js_state()
            create_webview()
        except Exception: pass

    def start_combat(self, is_boss=False):
        if is_boss:
            self.enemy = Enemy("Mothman Legend", 150, "Shadow", [("Attack", 20)], DATABASE["Bestiary"][1].lore, DATABASE["Bestiary"][1].image_file)
        else:
            self.enemy = Enemy("Woodland Shade", 60, "Divine", [("Attack", 12)], DATABASE["Bestiary"][0].lore, DATABASE["Bestiary"][0].image_file)
            
        if self.enemy.name not in player.bestiary_unlocked:
            player.bestiary_unlocked.append(self.enemy.name)

        player.block = 0
        player.mana = 4 if any("Lilith" in e.name for e in player.team) else 3
        self.combat_log = f"A wild {self.enemy.name} appears!"
        self.update_ui()
        self.sync_js_state()

    def sync_js_state(self):
        if platform == 'android' and getattr(self, 'webview', None):
            payload = {"enemyName": self.enemy.name, "enemyHp": self.enemy.hp, "enemyMaxHp": self.enemy.max_hp, "enemyImg": self.enemy.image_file}
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                self.webview.evaluateJavascript(f"if(window.updateCombatState) updateCombatState({json.dumps(payload)});", None)
            trigger()

    def trigger_js_attack(self, attacker="player"):
        if platform == 'android' and getattr(self, 'webview', None):
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                self.webview.evaluateJavascript(f"if(window.playAttackAnim) playAttackAnim('{attacker}');", None)
            trigger()

    def update_ui(self, disable_input=False):
        self.ui_panel.clear_widgets()
        
        # Check Win Condition
        if self.enemy.hp <= 0:
            player.currency += 120
            player.current_tier += 1
            player.save_game()
            self.ui_panel.add_widget(make_wrapped_label(f"VICTORY!\nThe {self.enemy.name} was defeated.\nEarned 120 Gold!", font_size='26sp', bold=True, color=(1, 0.8, 0.2, 1), size_hint=(1, 0.6)))
            back_btn = Button(text="Continue Path", font_size='20sp', size_hint=(1, 0.4))
            back_btn.bind(on_press=self.finish_combat)
            self.ui_panel.add_widget(back_btn)
            return

        # Check Loss Condition
        alive_team = [e for e in player.team if e.current_hp > 0]
        if not alive_team:
            self.ui_panel.add_widget(make_wrapped_label("YOUR COVEN WAS DEFEATED...", font_size='30sp', bold=True, size_hint=(1, 0.6)))
            back_btn = Button(text="Return to Menu", font_size='20sp', size_hint=(1, 0.4))
            back_btn.bind(on_press=self.reset_run)
            self.ui_panel.add_widget(back_btn)
            return

        # Combat Status UI
        status_text = f"Coven Block: {player.block}  |  Mana: {player.mana}\nEnemy Statuses: Burn ({self.enemy.burn}) | Poison ({self.enemy.poison})"
        self.ui_panel.add_widget(make_wrapped_label(status_text, font_size='14sp', bold=True, size_hint=(1, 0.15)))

        log_bg = BoxLayout(size_hint=(1, 0.15))
        log_bg.add_widget(make_wrapped_label(self.combat_log, font_size='15sp', color=(0.4, 0.9, 1, 1), bold=True))
        self.ui_panel.add_widget(log_bg)

        # Team Combat Buttons
        cards_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.5))
        for entity in player.team:
            if entity.current_hp > 0:
                spell = entity.ultimate_spell
                btn_text = f"{entity.name}\nHP: {entity.current_hp}/{entity.max_hp}\nCast: {spell.name}\n(Dmg:{spell.damage} Cost:{spell.cost})"
                btn = Button(text=btn_text, font_size='12sp', halign="center", valign="middle", disabled=disable_input)
                btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-10, None)))
                btn.bind(on_press=lambda instance, e=entity, s=spell: self.cast_spell(e, s))
                cards_layout.add_widget(btn)
            else:
                dead_lbl = Label(text=f"{entity.name}\n(Fallen)", color=(0.5, 0.5, 0.5, 1), font_size='14sp', halign="center", valign="middle")
                cards_layout.add_widget(dead_lbl)
        self.ui_panel.add_widget(cards_layout)
        
        nav_row = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.2))
        end_turn_btn = Button(text="End Turn", font_size='18sp', background_color=(0.2, 0.6, 0.8, 1), disabled=disable_input)
        end_turn_btn.bind(on_press=self.enemy_turn)
        nav_row.add_widget(end_turn_btn)
        self.ui_panel.add_widget(nav_row)
        
        self.sync_js_state()

    def cast_spell(self, entity, spell):
        if player.mana >= spell.cost:
            self.trigger_js_attack("player")
            player.mana -= spell.cost
            player.block += spell.block
            mult = 1.5 if spell.spell_type == self.enemy.weakness else 1.0
            dmg = int(spell.damage * mult)
            self.enemy.hp -= dmg
            
            self.combat_log = f"{entity.name} cast {spell.name} dealing {dmg} damage!"
            if spell.status_effect:
                eff, val = spell.status_effect
                if eff == "Burn": self.enemy.burn += val
                elif eff == "Poison": self.enemy.poison += val
            self.update_ui()
        else:
            self.combat_log = "Not enough mana!"
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

        raw_damage = 15
        damage_to_hp = max(0, raw_damage - player.block)
        player.block = max(0, player.block - raw_damage)

        alive_team = [e for e in player.team if e.current_hp > 0]
        if alive_team:
            target = random.choice(alive_team)
            target.current_hp -= damage_to_hp
            self.combat_log = f"{self.enemy.name} attacks {target.name} for {damage_to_hp} damage!\nYour turn."

        player.mana = 4 if any("Lilith" in e.name for e in player.team) else 3
        self.update_ui(disable_input=False)

    def finish_combat(self, instance):
        self.manager.current = 'map'

    def reset_run(self, instance):
        for e in player.roster: e.current_hp = e.max_hp
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
        self.status_label = make_wrapped_label(f"Gold: {player.currency} | Dust: {player.dust}\nTap 'Commence Ritual'.", font_size='16sp', size_hint=(1, 0.4))
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
            wv = self.webview; self.webview = None
            @run_on_ui_thread
            def remove_wv():
                try:
                    wv.setVisibility(8); wv.loadUrl("about:blank"); parent = wv.getParent()
                    if parent: parent.removeView(wv)
                    wv.destroy()
                except Exception: pass
            remove_wv()

    def load_android_webview(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = autoclass('android.util.DisplayMetrics')()
            activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True)
                self.webview.getSettings().setAllowFileAccess(True)
                self.webview.setBackgroundColor(0)
                self.webview.setWebViewClient(WebViewClient())
                html_path = os.path.abspath(os.path.join('assets', 'index.html'))
                if os.path.exists(html_path):
                    self.webview.loadUrl(f'file://{html_path}')
                params = autoclass('android.view.ViewGroup$LayoutParams')(metrics.widthPixels, int(metrics.heightPixels * 0.65))
                activity.addContentView(self.webview, params)
            create_webview()
        except Exception: pass

    def go_back(self, instance):
        self.manager.current = 'menu'

    def start_summon(self, instance):
        if player.currency < 100:
            self.status_label.text = "Not enough gold!"
            return
            
        player.currency -= 100
        self.summon_btn.disabled = True
        Clock.schedule_once(lambda dt: setattr(self.summon_btn, 'disabled', False), 2.5)
        
        if random.random() < 0.8: # Adjusted rates to favor getting characters!
            pulled = random.choice(DATABASE["Entities"])
            ult = pulled.ultimate_spell
            if not any(e.name == pulled.name for e in player.roster):
                player.roster.append(pulled)
                self.status_label.text = f"Summoned {pulled.name}!\nPassive: {pulled.passive_desc}"
            else:
                player.dust += 25
                self.status_label.text = f"Duplicate {pulled.name}.\nConverted to 25 Arcane Dust!"
            self.trigger_js_animation(pulled.image_file, pulled.name)
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
                self.webview.evaluateJavascript(f"if(window.triggerSummon) triggerSummon('{img_file}', '{entity_name}');", None)
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
            btn = Button(text=btn_text, font_size='16sp', halign="center", valign="middle", size_hint_y=None, height=100, disabled=(player.dust < cost_dust or spell.level >= 3))
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
            if any(e.name == db_entity.name for e in player.roster):
                entry = f"📜 {db_entity.name} [{db_entity.origin}]\nPassive: {db_entity.passive_desc}\nLore: {db_entity.lore}"
            else:
                entry = f"🔒 {db_entity.name} [{db_entity.origin}]\n[LORE LOCKED - Summon to reveal entry]"
            list_layout.add_widget(make_wrapped_label(entry, font_size='16sp', height=140))

        list_layout.add_widget(make_wrapped_label("=== URBAN LEGEND BESTIARY ===", font_size='20sp', bold=True, height=50))
        for db_enemy in DATABASE["Bestiary"]:
            if db_enemy.name in player.bestiary_unlocked:
                entry = f"💀 {db_enemy.name} (Weakness: {db_enemy.weakness})\nLore: {db_enemy.lore}"
            else:
                entry = f"❓ {db_enemy.name}\n[LORE LOCKED - Encounter on The Hunt to reveal]"
            list_layout.add_widget(make_wrapped_label(entry, font_size='16sp', height=100))

        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)
        back_btn = Button(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)


class ShopScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)

    def refresh_shop(self):
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label("ALCHEMIST HUT", font_size='26sp', bold=True, size_hint=(1, 0.15)))
        
        status_text = f"Gold: {player.currency}\nRestores 30 HP to all Coven members."
        self.layout.add_widget(make_wrapped_label(status_text, font_size='18sp', size_hint=(1, 0.15)))

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
            for e in player.team:
                e.current_hp = min(e.max_hp, e.current_hp + 30)
            player.save_game()
            self.refresh_shop()

    def buy_spell(self, instance):
        if player.currency >= 120:
            player.currency -= 120
            player.deck.append(random.choice(DATABASE["Spells"]))
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
        sm.add_widget(SplashScreen(name='splash'))
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
