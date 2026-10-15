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
        self.name = name; self.origin = origin; self.rarity = rarity; self.passive_desc = passive_desc; self.ultimate_spell = ultimate_spell; self.lore = lore; self.image_file = image_file; self.bond = 0; self.current_hp = 50; self.max_hp = 50; self.dialogues = dialogues or []

class Enemy:
    def __init__(self, name, hp, weakness, intents, lore, image_file):
        self.name = name; self.max_hp = hp; self.hp = hp; self.block = 0; self.burn = 0; self.poison = 0; self.weakness = weakness; self.intents = intents; self.lore = lore; self.image_file = image_file

# Expanded Database with deep dialogues
DATABASE = {
    "Entities": [
        Entity("Chloe (1 Star)", "Witch", 1, "Heals 3 HP on Fire spells", Spell("Fireball", 15, 2, "Nature", status_effect=("Burn", 5)), "Village herbalist.", "chloe.png", dialogues=[
            {"prompt": "The moon is full. Harvest Nightshade or Mandrake?", "options": [{"text": "Nightshade.", "reward": ("bond", 25)}, {"text": "Mandrake.", "reward": ("dust", 30)}]},
            {"prompt": "I found a cursed grimoire in the woods.", "options": [{"text": "Burn it.", "reward": ("bond", 30)}, {"text": "Read it.", "reward": ("currency", 50)}]}
        ]),
        Entity("Sam (2 Star)", "Witch", 2, "+10% Shadow damage", Spell("Shadow Strike", 30, 3, "Shadow", status_effect=("Poison", 4)), "Solitary hedge witch.", "sam.png", dialogues=[
            {"prompt": "The shadows are restless. Do you fear the dark?", "options": [{"text": "I embrace it.", "reward": ("bond", 25)}, {"text": "It hides our enemies.", "reward": ("currency", 50)}]},
            {"prompt": "They burned my coven. I will not forget.", "options": [{"text": "Vengeance.", "reward": ("bond", 35)}, {"text": "Focus.", "reward": ("dust", 30)}]}
        ])
        # Add Lilith, Puck, Kelpie, Mab, Ophanim, Metatron here following the same pattern
    ],
    "Spells": [Spell("Basic Strike", 5, 1, "Nature"), Spell("Zap", 5, 1, "Divine"), Spell("Holy Barrier", 0, 2, "Divine", block=20)],
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
        self.team = [] # Max 3 entities for combat
        self.bestiary_unlocked = []
        self.current_tier = 0
        # Map nodes with relative x,y coordinates for visual placement (0.0 to 1.0)
        self.map_nodes = [
            {"id": 0, "type": "Crossroads", "label": "Path Alpha", "pos": (0.2, 0.1)},
            {"id": 1, "type": "Alchemist Shop", "label": "Apothecary", "pos": (0.5, 0.3)},
            {"id": 2, "type": "Crossroads", "label": "Haunted Ruins", "pos": (0.8, 0.6)},
            {"id": 3, "type": "Boss", "label": "The Fog", "pos": (0.5, 0.9)}
        ]
    
    def save_game(self): pass # Add JSON save logic here
    def load_game(self): pass # Add JSON load logic here

player = PlayerState()

def make_wrapped_label(text, font_size='18sp', bold=False, color=(1,1,1,1), size_hint=(1, None), height=80):
    lbl = Label(text=text, font_size=font_size, bold=bold, color=color, halign="center", valign="middle", size_hint=size_hint)
    if size_hint[1] is None: lbl.height = height
    lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-20, None)))
    return lbl

class MenuScreen(Screen):
    # Same as previous MenuScreen
    pass

class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)

    def refresh_map(self):
        self.layout.clear_widgets()
        # Visual Background
        bg = Image(source='assets/map_bg.png', allow_stretch=True, keep_ratio=False, size_hint=(1, 1), pos_hint={'x':0, 'y':0})
        self.layout.add_widget(bg)
        
        # Overlay UI
        ui_box = BoxLayout(orientation='vertical', size_hint=(1, 1))
        ui_box.add_widget(make_wrapped_label(f"Gold: {player.currency} | Dust: {player.dust}", font_size='18sp', bold=True, size_hint=(1, 0.1), color=(1,1,1,1)))
        ui_box.add_widget(BoxLayout(size_hint=(1, 0.8))) # Empty spacer for map area
        
        back_btn = Button(text="Menu", size_hint=(1, 0.1), font_size='18sp', background_color=(0.1, 0.1, 0.2, 0.9))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        ui_box.add_widget(back_btn)
        self.layout.add_widget(ui_box)

        # Plot Glowing Orbs
        for idx, node in enumerate(player.map_nodes):
            is_active = (idx == player.current_tier)
            is_cleared = (idx < player.current_tier)
            
            orb_box = BoxLayout(orientation='vertical', size_hint=(None, None), size=(100, 100), pos_hint={'center_x': node['pos'][0], 'center_y': node['pos'][1]})
            
            btn_color = (0.3, 1, 0.3, 1) if is_cleared else (0, 1, 1, 1) if is_active else (0.3, 0.3, 0.3, 1)
            orb_btn = Button(text="", background_normal='assets/map_node.png', background_color=btn_color, size_hint=(1, 0.7), disabled=not is_active)
            orb_btn.bind(on_press=lambda inst, n=node['type']: self.enter_node(n))
            
            if is_active:
                anim = Animation(opacity=0.4, duration=0.8) + Animation(opacity=1.0, duration=0.8)
                anim.repeat = True; anim.start(orb_btn)
                
            orb_box.add_widget(orb_btn)
            orb_box.add_widget(Label(text=node['label'], font_size='12sp', bold=True, size_hint=(1, 0.3), color=(1,1,1,1)))
            self.layout.add_widget(orb_box)

    def enter_node(self, node_type):
        if node_type in ["Crossroads", "Boss"]:
            self.manager.get_screen('combat').start_combat(is_boss=(node_type=="Boss"))
            self.manager.current = 'combat'
        elif node_type == "Alchemist Shop": pass # Route to shop
        elif node_type == "Shrine": pass # Route to shrine

class TeamScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')
        self.web_placeholder = BoxLayout(size_hint=(1, 0.85))
        self.layout.add_widget(self.web_placeholder)
        
        btn_box = BoxLayout(size_hint=(1, 0.15))
        back_btn = Button(text="Back to Menu", font_size='18sp'); back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        btn_box.add_widget(back_btn)
        self.layout.add_widget(btn_box)
        self.add_widget(self.layout)

    def on_enter(self):
        if platform == 'android':
            self.load_android_webview()
        else:
            self.web_placeholder.clear_widgets()
            self.web_placeholder.add_widget(make_wrapped_label("[3D Gallery Active]\nCompile to APK to view.", font_size='16sp'))

    def on_leave(self):
        if platform == 'android' and getattr(self, 'webview', None):
            # Clean up logic
            pass 

    def load_android_webview(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            
            # Custom WebViewClient to intercept JS button clicks
            class CustomClient(WebViewClient):
                def shouldOverrideUrlLoading(self, view, url):
                    if url.startswith("kivy://select_team"):
                        parsed = urllib.parse.urlparse(url)
                        char_name = urllib.parse.parse_qs(parsed.query)['name'][0]
                        # Python logic to add char_name to player.team
                        return True
                    return False

            roster_data = [{"name": e.name, "img": e.image_file, "passive": e.passive_desc, "ult_name": e.ultimate_spell.name, "dmg": e.ultimate_spell.damage, "cost": e.ultimate_spell.cost, "blk": e.ultimate_spell.block} for e in player.roster]
            json_data = json.dumps(roster_data)

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True)
                self.webview.setBackgroundColor(0)
                client = CustomClient()
                self.webview.setWebViewClient(client)
                html_path = os.path.abspath(os.path.join('assets', 'gallery.html'))
                self.webview.loadUrl(f'file://{html_path}')
                self.webview.evaluateJavascript(f"loadGallery('{json_data}');", None)
                # attach to layout
            create_webview()
        except Exception as e: pass

class CombatScreen(Screen):
    # Update to cycle through player.team entities for attacks/HP tracking instead of a global pool
    pass

class DeckbuilderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(MapScreen(name='map'))
        sm.add_widget(TeamScreen(name='team'))
        sm.add_widget(CombatScreen(name='combat'))
        # Add remaining screens
        return sm

if __name__ == '__main__':
    DeckbuilderApp().run()
