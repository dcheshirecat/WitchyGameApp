from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.carousel import Carousel
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.utils import platform
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, RenderContext, RoundedRectangle
import random
import json
import os
import sqlite3
import base64

class ImageButton(ButtonBehavior, Image): 
    pass

class SmoothButton(ButtonBehavior, Label):
    def __init__(self, bg_color=(0.15, 0.15, 0.2, 1), radius=[15], **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(self.bg_color if self.state == 'normal' else (self.bg_color[0]*1.5, self.bg_color[1]*1.5, self.bg_color[2]*1.5, 1)))
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

def make_wrapped_label(text, font_size='18sp', bold=False, color=(1, 1, 1, 1), size_hint=(1, None), height=80, halign="center"):
    lbl = Label(text=text, font_size=font_size, bold=bold, color=color, halign=halign, valign="middle", size_hint=size_hint)
    if size_hint[1] is None: 
        lbl.height = height
    lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0] - 20, None)))
    return lbl

class TrailWidget(BoxLayout):
    def __init__(self, nodes, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes
        self.bind(pos=self.update_trail, size=self.update_trail)
        with self.canvas.before:
            Color(0.8, 0.6, 0.2, 0.8)
            self.line = Line(width=3, dash_offset=5, dash_length=10)
            
    def update_trail(self, *args):
        pts = []
        for n in self.nodes: 
            pts.extend([self.x + self.width * n['pos'][0], self.y + self.height * n['pos'][1]])
        self.line.points = pts

# --- GLSL MAGIC FOG SHADER ---
fs_magic_fog = '''
#ifdef GL_ES
precision highp float;
#endif
$HEADER$
uniform float time;
uniform vec2 resolution;

void main(void) {
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    float wave = sin(uv.x * 5.0 + time * 0.8) * 0.05 + sin(uv.y * 3.0 - time * 0.5) * 0.05;
    gl_FragColor = vec4(0.0, 0.8, 0.9, 0.15 + wave);
}
'''

class MagicFogOverlay(Widget):
    def __init__(self, **kwargs):
        self.canvas = RenderContext(use_parent_modelview=True, use_parent_projection=True)
        self.canvas.shader.fs = fs_magic_fog
        with self.canvas:
            self.rect = Rectangle(size=self.size, pos=self.pos)
        super().__init__(**kwargs)
        Clock.schedule_interval(self.update_glsl, 1/60.0)

    def on_size(self, *args):
        self.rect.size = self.size
        self.canvas['resolution'] = [float(self.width), float(self.height)]

    def on_pos(self, *args):
        self.rect.pos = self.pos

    def update_glsl(self, dt):
        self.canvas['time'] = Clock.get_boottime()

# --- Core Data Structures ---
class Spell:
    def __init__(self, name, damage, cost, spell_type="Nature", block=0, status_effect=None, level=1, exhaust=False):
        self.name = name; self.damage = damage; self.cost = cost; self.spell_type = spell_type; self.block = block; self.status_effect = status_effect; self.level = level; self.exhaust = exhaust

class Entity:
    def __init__(self, name, origin, rarity, passive_desc, ultimate_spell, char_spells, lore, image_file, dialogues=None):
        self.name = name; self.origin = origin; self.rarity = rarity; self.passive_desc = passive_desc; self.ultimate_spell = ultimate_spell; self.char_spells = char_spells; self.lore = lore; self.image_file = image_file; self.bond = 0; self.current_hp = 60; self.max_hp = 60; self.dialogues = dialogues or []

class Enemy:
    def __init__(self, name, hp, weakness, intents, lore, image_file):
        self.name = name; self.max_hp = hp; self.hp = hp; self.block = 0; self.burn = 0; self.poison = 0; self.weakness = weakness; self.intents = intents; self.lore = lore; self.image_file = image_file

DATABASE = {
    "Entities": [
        Entity("Chloe", "Witch", 1, "Heals 3 HP on Fire spells", Spell("Inferno", 25, 3, "Nature", status_effect=("Burn", 8), exhaust=True), [Spell("Fireball", 15, 2, "Nature", status_effect=("Burn", 5)), Spell("Ember", 8, 1, "Nature")], "Village herbalist.", "chloe.png", dialogues=[{"prompt": "Harvest Nightshade or Mandrake?", "options": [{"text": "Nightshade.", "reward": ("bond", 25)}, {"text": "Mandrake.", "reward": ("dust", 30)}]}]),
        Entity("Sam", "Witch", 2, "+10% Shadow damage", Spell("Shadow Strike", 30, 3, "Shadow", status_effect=("Poison", 4), exhaust=True), [Spell("Hex", 12, 2, "Shadow", status_effect=("Poison", 3)), Spell("Dark Ward", 0, 1, "Shadow", block=10)], "Solitary hedge witch.", "sam.png", dialogues=[{"prompt": "Do you fear the dark?", "options": [{"text": "I embrace it.", "reward": ("bond", 25)}, {"text": "It hides enemies.", "reward": ("currency", 50)}]}]),
        Entity("Lilith", "Witch", 3, "Start combat with +1 Mana", Spell("Obliterate", 100, 5, "Shadow", exhaust=True), [Spell("Void Ray", 25, 2, "Shadow"), Spell("Drain", 15, 2, "Shadow", status_effect=("Poison", 2))], "Ancient grand witch.", "lilith.png", dialogues=[{"prompt": "Power requires sacrifice.", "options": [{"text": "My blood.", "reward": ("bond", 35)}, {"text": "Their blood.", "reward": ("dust", 50)}]}]),
        Entity("Morgana", "Witch", 3, "Spells cost 1 less Mana", Spell("Eldritch Storm", 45, 4, "Nature"), [Spell("Briar Patch", 10, 1, "Nature", block=5), Spell("Root Snare", 20, 2, "Nature")], "The swamp queen.", "morgana.png"),
        Entity("Puck", "Fae", 1, "Draw +1 card at battle start", Spell("Trickster Spark", 12, 1, "Nature"), [Spell("Glimmer", 5, 1, "Nature"), Spell("Distract", 0, 1, "Nature", block=12)], "Elusive woodland spirit.", "puck.png"),
        Entity("The Kelpie", "Fae", 2, "Enemies take 15% more damage", Spell("Drowning Depths", 35, 3, "Nature"), [Spell("Tidal Crash", 20, 2, "Nature"), Spell("Chilling Mist", 5, 1, "Nature", block=8)], "A shapeshifting water demon.", "kelpie.png"),
        Entity("Queen Mab", "Fae", 3, "Steals 1 enemy intent turn", Spell("Nightmare Realm", 75, 4, "Shadow"), [Spell("Slumber", 0, 2, "Shadow", block=20), Spell("Dream Eater", 30, 3, "Shadow")], "Monarch of the Unseelie court.", "queen_mab.png"),
        Entity("Dullahan", "Fae", 2, "Gains 2 Strength when damaged", Spell("Sever", 40, 3, "Shadow"), [Spell("Whip Strike", 18, 2, "Shadow"), Spell("Bone Shield", 0, 2, "Shadow", block=15)], "The headless rider.", "dullahan.png"),
        Entity("Ophanim", "Angel", 2, "Gain 5 Block each turn", Spell("Wheel of Eyes", 25, 2, "Divine", block=15, exhaust=True), [Spell("Holy Ray", 15, 2, "Divine"), Spell("Aegis", 0, 2, "Divine", block=18)], "A celestial ring.", "ophanim.png"),
        Entity("Metatron", "Angel", 3, "Purges enemy buffs", Spell("Wrath of Heaven", 120, 6, "Divine", block=30, exhaust=True), [Spell("Divine Word", 25, 2, "Divine"), Spell("Purify", 10, 1, "Divine", status_effect=("Burn", 3))], "Supreme voice of the heavens.", "metatron.png"),
        Entity("Seraphim", "Angel", 3, "Burns enemies", Spell("Six Wings", 50, 4, "Divine"), [Spell("Cleansing Fire", 20, 2, "Divine", status_effect=("Burn", 4)), Spell("Radiance", 10, 1, "Divine", block=10)], "The burning ones.", "seraphim.png")
    ],
    "GlobalSpells": [
        Spell("Basic Strike", 5, 1, "Nature"), Spell("Zap", 5, 1, "Divine"), Spell("Punch", 10, 1, "Nature"), Spell("Magic Missile", 20, 2, "Divine")
    ],
    "Bestiary": [
        Enemy("Woodland Shade", 80, "Divine", [("Attack", 10)], "A lingering spirit.", "woodland_shade.png"),
        Enemy("Corrupted Knight", 120, "Nature", [("Attack", 15)], "A rusted, animated armor.", "corrupted_knight.png"),
        Enemy("Mothman Legend", 250, "Shadow", [("Attack", 25)], "A winged harbinger.", "mothman_legend.png")
    ]
}

class PlayerState:
    def __init__(self):
        self.currency = 500; self.dust = 100; self.roster = []; self.team = []; self.bestiary_unlocked = []; self.current_tier = 0
        self.global_deck = [Spell("Basic Strike", 5, 1, "Nature"), Spell("Basic Strike", 5, 1, "Nature")]
        self.map_nodes = [
            {"id": 0, "type": "Story", "label": "The Outskirts", "pos": (0.3, 0.2), "story": "The twisted trees of the dead forest loom overhead. A foul presence blocks the path forward.", "next": "Combat"},
            {"id": 1, "type": "Alchemist Shop", "label": "Apothecary", "pos": (0.7, 0.4)},
            {"id": 2, "type": "Story", "label": "Sacred Spring", "pos": (0.3, 0.6), "story": "The holy waters of the shrine mend the Coven's wounds. You feel prepared for the darkness ahead.", "next": "Shrine"},
            {"id": 3, "type": "Boss", "label": "The Fog", "pos": (0.5, 0.85)}
        ]

    def _get_db_path(self):
        app = App.get_running_app()
        if not app: 
            return 'savegame.db'
        return os.path.join(app.user_data_dir, 'savegame.db')

    def init_db(self):
        with sqlite3.connect(self._get_db_path()) as conn:
            c = conn.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, currency INT, dust INT, current_tier INT)')
            c.execute('CREATE TABLE IF NOT EXISTS roster (name TEXT PRIMARY KEY, bond INT, hp INT, in_team INT)')
            c.execute('CREATE TABLE IF NOT EXISTS deck (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS bestiary (name TEXT PRIMARY KEY)')
            c.execute('SELECT count(*) FROM state')
            if c.fetchone()[0] == 0:
                c.execute('INSERT INTO state (id, currency, dust, current_tier) VALUES (1, 500, 100, 0)')
                c.execute('INSERT INTO deck (name) VALUES ("Basic Strike")')
                c.execute('INSERT INTO deck (name) VALUES ("Basic Strike")')
            conn.commit()

    def save_game(self):
        with sqlite3.connect(self._get_db_path()) as conn:
            c = conn.cursor()
            c.execute('UPDATE state SET currency=?, dust=?, current_tier=? WHERE id=1', (self.currency, self.dust, self.current_tier))
            c.execute('DELETE FROM roster')
            for ent in self.roster:
                in_team = 1 if ent in self.team else 0
                c.execute('INSERT INTO roster (name, bond, hp, in_team) VALUES (?, ?, ?, ?)', (ent.name, ent.bond, ent.current_hp, in_team))
            c.execute('DELETE FROM deck')
            for spell in self.global_deck:
                c.execute('INSERT INTO deck (name) VALUES (?)', (spell.name,))
            c.execute('DELETE FROM bestiary')
            for b in self.bestiary_unlocked:
                c.execute('INSERT INTO bestiary (name) VALUES (?)', (b,))
            conn.commit()

    def load_game(self):
        self.init_db()
        with sqlite3.connect(self._get_db_path()) as conn:
            c = conn.cursor()
            c.execute('SELECT currency, dust, current_tier FROM state WHERE id=1')
            row = c.fetchone()
            if row:
                self.currency, self.dust, self.current_tier = row
            self.roster = []; self.team = []
            c.execute('SELECT name, bond, hp, in_team FROM roster')
            for r_name, r_bond, r_hp, r_in_team in c.fetchall():
                db_ent = next((e for e in DATABASE['Entities'] if e.name == r_name), None)
                if db_ent:
                    db_ent.bond = r_bond; db_ent.current_hp = r_hp; self.roster.append(db_ent)
                    if r_in_team == 1: self.team.append(db_ent)
            self.global_deck = []
            c.execute('SELECT name FROM deck')
            for (d_name,) in c.fetchall():
                db_spell = next((s for s in DATABASE['GlobalSpells'] if s.name == d_name), None)
                if db_spell: self.global_deck.append(db_spell)
                else: 
                    for ent in DATABASE['Entities']:
                        if ent.ultimate_spell.name == d_name: 
                            self.global_deck.append(ent.ultimate_spell); break
            self.bestiary_unlocked = []
            c.execute('SELECT name FROM bestiary')
            for (b_name,) in c.fetchall():
                self.bestiary_unlocked.append(b_name)

player = PlayerState()

# --- Screens ---
class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        bg_path = 'presplash.png' if os.path.exists('presplash.png') else 'assets/card_back.png'
        self.layout.add_widget(Image(source=bg_path, allow_stretch=True, keep_ratio=False, size_hint=(1, 1)))
        text_bg = BoxLayout(size_hint=(0.8, 0.15), pos_hint={'center_x': 0.5, 'y': 0.1})
        with text_bg.canvas.before:
            Color(0, 0, 0, 0.85)
            self.rect = Rectangle(pos=text_bg.pos, size=text_bg.size)
        text_bg.bind(pos=self.update_rect, size=self.update_rect)
        self.label = make_wrapped_label("Summoning the Coven...", font_size='24sp', bold=True)
        text_bg.add_widget(self.label)
        self.layout.add_widget(text_bg); self.add_widget(self.layout)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos; self.rect.size = instance.size

    def on_enter(self):
        anim = Animation(opacity=0.2, duration=0.6) + Animation(opacity=1.0, duration=0.6)
        anim.repeat = True; anim.start(self.label)
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'menu'), 2.5)

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        layout.add_widget(make_wrapped_label("URBAN LEGEND DECKBUILDER", font_size='28sp', bold=True, size_hint=(1, 0.2)))
        buttons = [
            ("Enter The Hunt (Map)", lambda x: setattr(self.manager, 'current', 'map'), (0.2, 0.6, 0.3, 1)),
            ("Coven & Team Building", lambda x: setattr(self.manager, 'current', 'team'), (0.4, 0.2, 0.5, 1)),
            ("Arcane Dust Upgrade Shrine", lambda x: setattr(self.manager, 'current', 'upgrade'), (0.6, 0.4, 0.1, 1)),
            ("The Esoteric Grimoire", lambda x: setattr(self.manager, 'current', 'grimoire'), (0.2, 0.4, 0.6, 1)),
            ("3D Summoning Ritual", lambda x: setattr(self.manager, 'current', 'gacha'), (0.8, 0.2, 0.2, 1)),
            ("Hangout (Friendship)", lambda x: setattr(self.manager, 'current', 'hangout'), (0.1, 0.5, 0.6, 1))
        ]
        for text, cb, col in buttons:
            btn = SmoothButton(text=text, font_size='18sp', size_hint=(1, 0.13), bg_color=col)
            btn.bind(on_press=cb); layout.add_widget(btn)
        self.add_widget(layout)

class StoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20)
        self.text_label = make_wrapped_label("", font_size='20sp', size_hint=(1, 0.8))
        self.layout.add_widget(self.text_label)
        self.continue_btn = SmoothButton(text="Continue...", font_size='18sp', size_hint=(1, 0.2), bg_color=(0.3, 0.3, 0.3, 1))
        self.continue_btn.bind(on_press=self.finish_story)
        self.layout.add_widget(self.continue_btn); self.add_widget(self.layout)
        self.full_text = ""; self.current_idx = 0; self.next_node_type = ""

    def load_story(self, text, next_node):
        self.full_text = text; self.next_node_type = next_node; self.text_label.text = ""; self.current_idx = 0
        self.continue_btn.disabled = True
        Clock.schedule_interval(self.typewriter, 0.03)

    def typewriter(self, dt):
        if self.current_idx < len(self.full_text):
            self.text_label.text += self.full_text[self.current_idx]
            self.current_idx += 1
        else:
            self.continue_btn.disabled = False
            return False 

    def finish_story(self, instance):
        if self.next_node_type == "Combat":
            self.manager.get_screen('combat').start_combat(is_boss=False)
            self.manager.current = 'combat'
        elif self.next_node_type == "Shrine":
            for e in player.team: 
                e.current_hp = min(e.max_hp, e.current_hp + 30)
            player.current_tier += 1; player.save_game(); self.manager.get_screen('map').refresh_map()
            self.manager.current = 'map'

class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout(); self.add_widget(self.layout)

    def on_enter(self):
        self.refresh_map()

    def refresh_map(self):
        self.layout.clear_widgets()
        bg_path = 'assets/map_bg.png' if os.path.exists('assets/map_bg.png') else 'assets/card_back.png'
        self.layout.add_widget(Image(source=bg_path, allow_stretch=True, keep_ratio=False, size_hint=(1, 1), pos_hint={'x':0, 'y':0}, color=(1, 1, 1, 0.45)))
        self.layout.add_widget(MagicFogOverlay(size_hint=(1, 1), pos_hint={'x':0, 'y':0}))
        self.layout.add_widget(TrailWidget(player.map_nodes, size_hint=(1,1), pos_hint={'x':0, 'y':0}))
        
        for idx, node in enumerate(player.map_nodes):
            is_active = (idx == player.current_tier); is_cleared = (idx < player.current_tier)
            orb_box = FloatLayout(size_hint=(None, None), size=(120, 100))
            orb_box.pos_hint = {'center_x': node['pos'][0], 'center_y': node['pos'][1]}
            btn_color = (0.2, 0.9, 0.2, 1) if is_cleared else (0, 0.9, 1, 1) if is_active else (0.4, 0.4, 0.4, 1)
            
            img_src = 'assets/map_node.png' if os.path.exists('assets/map_node.png') else 'assets/summoning_circle.png'
            orb_btn = ImageButton(source=img_src, size_hint=(0.6, 0.6), pos_hint={'center_x': 0.5, 'center_y': 0.6}, color=btn_color)
            if is_active:
                orb_btn.bind(on_press=lambda inst, n=node: self.enter_node(n))
                anim = Animation(opacity=0.4, duration=0.8) + Animation(opacity=1.0, duration=0.8)
                anim.repeat = True; anim.start(orb_btn)
            orb_box.add_widget(orb_btn)
            lbl_color = (1,1,1,1) if is_active else (0.7,0.7,0.7,1)
            orb_box.add_widget(Label(text=node['label'], font_size='14sp', bold=True, size_hint=(1, 0.3), pos_hint={'center_x': 0.5, 'y': 0}, color=lbl_color))
            self.layout.add_widget(orb_box)

        ui_box = BoxLayout(orientation='vertical', size_hint=(1, 1))
        stats_text = f"Gold: {player.currency} | Dust: {player.dust}\nActive Coven Size: {len(player.team)}/3"
        ui_box.add_widget(make_wrapped_label(stats_text, font_size='18sp', bold=True, size_hint=(1, 0.15), color=(1,0.9,0.5,1)))
        ui_box.add_widget(BoxLayout(size_hint=(1, 0.75)))
        back_btn = SmoothButton(text="Return to Menu", font_size='18sp', size_hint=(1, 0.1), bg_color=(0.2, 0.2, 0.2, 1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        ui_box.add_widget(back_btn); self.layout.add_widget(ui_box)

    def enter_node(self, node):
        if len(player.team) == 0: 
            self.manager.current = 'team'; return
        if node['type'] == "Story":
            self.manager.get_screen('story').load_story(node['story'], node['next'])
            self.manager.current = 'story'
        elif node['type'] == "Boss":
            self.manager.get_screen('combat').start_combat(is_boss=True)
            self.manager.current = 'combat'
        elif node['type'] == "Alchemist Shop":
            self.manager.current = 'shop'

class TeamScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.team_label = make_wrapped_label("Current Coven: None", font_size='16sp', size_hint=(1, 0.15))
        self.layout.add_widget(self.team_label)
        self.carousel = Carousel(direction='right', size_hint=(1, 0.7))
        self.layout.add_widget(self.carousel)
        back_btn = SmoothButton(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15), bg_color=(0.2, 0.2, 0.2, 1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn); self.add_widget(self.layout)

    def on_enter(self):
        self.update_team_label()
        current_idx = self.carousel.index
        self.carousel.clear_widgets()
        if not player.roster:
            self.carousel.add_widget(make_wrapped_label("No entities summoned yet.\nGo to the Gacha screen!", font_size='18sp'))
            return
        for entity in player.roster:
            card_box = BoxLayout(orientation='vertical', padding=20, spacing=10)
            img_path = f"assets/{entity.image_file}" if os.path.exists(f"assets/{entity.image_file}") else "assets/card_back.png"
            card_box.add_widget(Image(source=img_path, size_hint=(1, 0.5), allow_stretch=True))
            stats = f"{entity.name}\nHP: {entity.current_hp}/{entity.max_hp}\nPassive: {entity.passive_desc}\nUltimate: {entity.ultimate_spell.name}"
            card_box.add_widget(make_wrapped_label(stats, font_size='16sp', size_hint=(1, 0.3)))
            btn_text = "Remove from Coven" if entity in player.team else "Add to Coven"
            btn_color = (0.8, 0.3, 0.3, 1) if entity in player.team else (0.2, 0.8, 0.4, 1)
            toggle_btn = SmoothButton(text=btn_text, font_size='18sp', size_hint=(1, 0.2), bg_color=btn_color)
            toggle_btn.bind(on_press=lambda inst, e=entity: self.toggle_team(e))
            card_box.add_widget(toggle_btn); self.carousel.add_widget(card_box)
        if current_idx is not None and current_idx < len(self.carousel.slides):
            self.carousel.index = current_idx

    def update_team_label(self):
        if not player.team: 
            self.team_label.text = "Current Coven: None (Select up to 3)"
        else: 
            self.team_label.text = "Current Coven:\n" + ", ".join([e.name for e in player.team])

    def toggle_team(self, entity):
        if entity in player.team: 
            player.team.remove(entity)
        elif len(player.team) < 3: 
            player.team.append(entity)
        player.save_game(); self.on_enter()

class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        self.enemy = None; self.combat_log = "An enemy blocks your path!"; self.webview = None
        self.web_placeholder = BoxLayout(size_hint=(1, 0.45)); self.layout.add_widget(self.web_placeholder)
        self.ui_panel = BoxLayout(orientation='vertical', size_hint=(1, 0.55), spacing=8)
        self.layout.add_widget(self.ui_panel); self.add_widget(self.layout)

    def on_enter(self):
        if platform == 'android': self.load_android_webview()
        else:
            self.web_placeholder.clear_widgets()
            self.web_placeholder.add_widget(make_wrapped_label("[3D Combat Engine Active]", font_size='14sp'))

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
            WebView = autoclass('android.webkit.WebView'); WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = autoclass('android.util.DisplayMetrics')(); activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True); self.webview.getSettings().setAllowFileAccess(True)
                self.webview.getSettings().setAllowFileAccessFromFileURLs(True); self.webview.setBackgroundColor(0)
                self.webview.setWebViewClient(WebViewClient())
                html_path = os.path.abspath(os.path.join('assets', 'combat.html'))
                if os.path.exists(html_path): self.webview.loadUrl(f'file://{html_path}')
                params = autoclass('android.view.ViewGroup$LayoutParams')(metrics.widthPixels, int(metrics.heightPixels * 0.45))
                activity.addContentView(self.webview, params)
                self.sync_js_state()
            create_webview()
        except Exception: pass

    def start_combat(self, is_boss=False):
        if is_boss: 
            self.enemy = Enemy("Mothman Legend", 250, "Shadow", [("Attack", 25)], DATABASE["Bestiary"][2].lore, DATABASE["Bestiary"][2].image_file)
        else: 
            self.enemy = Enemy("Corrupted Knight", 120, "Nature", [("Attack", 15)], DATABASE["Bestiary"][1].lore, DATABASE["Bestiary"][1].image_file)
            
        if self.enemy.name not in player.bestiary_unlocked: player.bestiary_unlocked.append(self.enemy.name)

        player.block = 0; player.mana = 4 if any("Lilith" in e.name for e in player.team) else 3
        self.combat_deck = player.global_deck.copy()
        for e in player.team:
            if e.current_hp > 0: 
                self.combat_deck.extend(e.char_spells); self.combat_deck.append(e.ultimate_spell)
            
        self.hand = random.sample(self.combat_deck, min(4, len(self.combat_deck)))
        self.combat_log = f"A wild {self.enemy.name} appears!"
        self.update_ui(); self.sync_js_state()

    def sync_js_state(self):
        if platform == 'android' and getattr(self, 'webview', None):
            team_data = [{"name": e.name.split(" ")[0], "hp": e.current_hp, "maxHp": e.max_hp, "img": e.image_file} for e in player.team]
            payload = {"enemyName": self.enemy.name, "enemyHp": self.enemy.hp, "enemyMaxHp": self.enemy.max_hp, "enemyImg": self.enemy.image_file, "team": team_data}
            js_cmd = f"javascript:if(window.updateCombatState) updateCombatState({json.dumps(payload)});"
            wv = self.webview
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                try: wv.loadUrl(js_cmd)
                except Exception: pass
            trigger()

    def trigger_js_attack(self, attacker="player", hero_index=0):
        if platform == 'android' and getattr(self, 'webview', None):
            js_cmd = f"javascript:if(window.playAttackAnim) playAttackAnim('{attacker}', {hero_index});"
            wv = self.webview
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                try: wv.loadUrl(js_cmd)
                except Exception: pass
            trigger()

    def trigger_js_float_text(self, text, color, target="enemy"):
        if platform == 'android' and getattr(self, 'webview', None):
            js_cmd = f"javascript:if(window.showFloatingText) showFloatingText('{text}', '{color}', '{target}');"
            wv = self.webview
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                try: wv.loadUrl(js_cmd)
                except Exception: pass
            trigger()

    def update_ui(self, disable_input=False):
        self.ui_panel.clear_widgets()
        if self.enemy.hp <= 0:
            player.currency += 150; player.current_tier += 1; player.save_game()
            self.ui_panel.add_widget(make_wrapped_label(f"VICTORY!\nEarned 150 Gold!", font_size='26sp', bold=True, color=(1, 0.8, 0.2, 1), size_hint=(1, 0.6)))
            back_btn = SmoothButton(text="Continue Path", font_size='20sp', size_hint=(1, 0.4), bg_color=(0.2, 0.8, 0.2, 1)); back_btn.bind(on_press=self.finish_combat)
            self.ui_panel.add_widget(back_btn); return

        alive_team = [e for e in player.team if e.current_hp > 0]
        if not alive_team:
            self.ui_panel.add_widget(make_wrapped_label("YOUR COVEN WAS DEFEATED...", font_size='30sp', bold=True, size_hint=(1, 0.6)))
            back_btn = SmoothButton(text="Return to Menu", font_size='20sp', size_hint=(1, 0.4), bg_color=(0.8, 0.2, 0.2, 1)); back_btn.bind(on_press=self.reset_run)
            self.ui_panel.add_widget(back_btn); return

        team_hp_str = " | ".join([f"{e.name[:5]}: {e.current_hp}/{e.max_hp}" for e in alive_team])
        status_text = f"Coven Block: {player.block}  |  Mana: {player.mana}\n{team_hp_str}\nEnemy Statuses: Burn ({self.enemy.burn}) | Poison ({self.enemy.poison})"
        self.ui_panel.add_widget(make_wrapped_label(status_text, font_size='14sp', bold=True, size_hint=(1, 0.15)))

        log_bg = BoxLayout(size_hint=(1, 0.15))
        log_bg.add_widget(make_wrapped_label(self.combat_log, font_size='14sp', color=(0.4, 0.9, 1, 1), bold=True))
        self.ui_panel.add_widget(log_bg)

        scroll = ScrollView(size_hint=(1, 0.5))
        cards_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_x=None)
        cards_layout.bind(minimum_width=cards_layout.setter('width'))
        
        for spell in self.hand:
            owner_idx = 0
            for i, e in enumerate(player.team):
                if spell in e.char_spells or spell == e.ultimate_spell: owner_idx = i; break
            ex_txt = "\n[Exhaust]" if spell.exhaust else ""
            btn_text = f"{spell.name}\n[{spell.spell_type}]\nDmg: {spell.damage}\nCost: {spell.cost}{ex_txt}"
            btn = SmoothButton(text=btn_text, font_size='14sp', halign="center", valign="middle", size_hint_x=None, width=150, bg_color=(0.2, 0.2, 0.4, 1), disabled=disable_input)
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-10, None)))
            btn.bind(on_press=lambda instance, s=spell, c=spell.cost, b=btn, idx=owner_idx: self.cast_spell(s, c, idx))
            cards_layout.add_widget(btn)
            
        scroll.add_widget(cards_layout); self.ui_panel.add_widget(scroll)
        
        nav_row = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.2))
        end_turn_btn = SmoothButton(text="End Turn", font_size='18sp', bg_color=(0.6, 0.2, 0.2, 1), disabled=disable_input)
        end_turn_btn.bind(on_press=self.enemy_turn); nav_row.add_widget(end_turn_btn)
        self.ui_panel.add_widget(nav_row); self.sync_js_state()

    def cast_spell(self, spell, cost, owner_idx):
        if player.mana >= cost:
            self.trigger_js_attack("player", owner_idx)
            player.mana -= cost; player.block += spell.block
            mult = 1.5 if spell.spell_type == self.enemy.weakness else 1.0
            dmg = int(spell.damage * mult); self.enemy.hp -= dmg
            
            self.trigger_js_float_text(f"-{dmg}", "#ff4444", "enemy")
            self.combat_log = f"Cast {spell.name} dealing {dmg} damage!"
            if spell.status_effect:
                eff, val = spell.status_effect
                if eff == "Burn": self.enemy.burn += val
                elif eff == "Poison": self.enemy.poison += val
                self.trigger_js_float_text(f"+{val} {eff}", "#ffaa00", "enemy")
            
            self.hand.remove(spell)
            if spell.exhaust and spell in self.combat_deck: self.combat_deck.remove(spell)
            self.update_ui()
        else:
            self.combat_log = "Not enough mana!"; self.update_ui()

    def enemy_turn(self, instance):
        self.combat_log = f"{self.enemy.name} is preparing to attack..."
        self.update_ui(disable_input=True)
        Clock.schedule_once(self.resolve_enemy_turn, 1.0)

    def resolve_enemy_turn(self, dt):
        self.trigger_js_attack("enemy")
        if self.enemy.burn > 0:
            self.enemy.hp -= self.enemy.burn; self.trigger_js_float_text(f"-{self.enemy.burn} Burn", "#ffaa00", "enemy")
            self.enemy.burn = max(0, self.enemy.burn - 1)
        if self.enemy.poison > 0:
            self.enemy.hp -= self.enemy.poison; self.trigger_js_float_text(f"-{self.enemy.poison} Poison", "#44ff44", "enemy")

        raw_damage = 15
        damage_to_hp = max(0, raw_damage - player.block)
        player.block = max(0, player.block - raw_damage)

        alive_team = [e for e in player.team if e.current_hp > 0]
        if alive_team:
            target = random.choice(alive_team)
            target.current_hp -= damage_to_hp
            self.trigger_js_float_text(f"-{damage_to_hp}", "#ff4444", "player")
            self.combat_log = f"{self.enemy.name} attacks {target.name} for {damage_to_hp} damage!\nYour turn."

        player.mana = 4 if any("Lilith" in e.name for e in player.team) else 3
        self.hand = random.sample(self.combat_deck, min(4, len(self.combat_deck)))
        self.update_ui(disable_input=False)

    def finish_combat(self, instance): 
        self.manager.current = 'map'
        
    def reset_run(self, instance):
        for e in player.roster: e.current_hp = e.max_hp
        player.current_tier = 0; player.save_game(); self.manager.current = 'menu'

class GachaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout() 
        self.webview = None
        main_box = BoxLayout(orientation='vertical')
        self.web_placeholder = BoxLayout(size_hint=(1, 0.65))
        main_box.add_widget(self.web_placeholder)
        
        control_panel = BoxLayout(orientation='vertical', size_hint=(1, 0.35), padding=10, spacing=10)
        self.status_label = make_wrapped_label(f"Tap 'Commence Ritual' to summon.", font_size='16sp', size_hint=(1, 0.4))
        control_panel.add_widget(self.status_label)
        
        self.summon_btn = SmoothButton(text="Commence Ritual (100 Gold)", font_size='18sp', size_hint=(1, 0.3), bg_color=(0, 0.5, 0.7, 1))
        self.summon_btn.bind(on_press=self.start_summon)
        control_panel.add_widget(self.summon_btn)
        
        back_btn = SmoothButton(text="Leave Ritual Chamber", font_size='18sp', size_hint=(1, 0.3), bg_color=(0.2, 0.2, 0.2, 1))
        back_btn.bind(on_press=self.go_back)
        control_panel.add_widget(back_btn)
        main_box.add_widget(control_panel)
        self.layout.add_widget(main_box)
        
        self.gold_label = Label(text=f"Gold: {player.currency}\nDust: {player.dust}", size_hint=(None, None), size=(150, 60), pos_hint={'right': 0.95, 'top': 0.95}, color=(1, 0.8, 0.1, 1), bold=True, font_size='18sp', halign='right')
        self.layout.add_widget(self.gold_label)
        self.add_widget(self.layout)

    def on_enter(self):
        self.gold_label.text = f"Gold: {player.currency}\nDust: {player.dust}"
        if platform == 'android': self.load_android_webview()
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
            WebView = autoclass('android.webkit.WebView'); WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = autoclass('android.util.DisplayMetrics')(); activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True); self.webview.getSettings().setAllowFileAccess(True)
                self.webview.setBackgroundColor(0); self.webview.setWebViewClient(WebViewClient())
                html_path = os.path.abspath(os.path.join('assets', 'index.html'))
                if os.path.exists(html_path): self.webview.loadUrl(f'file://{html_path}')
                params = autoclass('android.view.ViewGroup$LayoutParams')(metrics.widthPixels, int(metrics.heightPixels * 0.65))
                activity.addContentView(self.webview, params)
            create_webview()
        except Exception: pass

    def go_back(self, instance): self.manager.current = 'menu'

    def start_summon(self, instance):
        if player.currency < 100:
            self.status_label.text = "Not enough gold!"
            return
        player.currency -= 100
        self.gold_label.text = f"Gold: {player.currency}\nDust: {player.dust}"
        self.summon_btn.disabled = True
        Clock.schedule_once(lambda dt: setattr(self.summon_btn, 'disabled', False), 2.5)
        
        if random.random() < 0.7: 
            pulled = random.choice(DATABASE["Entities"])
            if not any(e.name == pulled.name for e in player.roster):
                player.roster.append(pulled)
                self.status_label.text = f"Summoned {pulled.name}!\nPassive: {pulled.passive_desc}"
            else:
                player.dust += 25
                self.gold_label.text = f"Gold: {player.currency}\nDust: {player.dust}"
                self.status_label.text = f"Duplicate {pulled.name}.\nConverted to 25 Arcane Dust!"
            self.trigger_js_animation(pulled.image_file, pulled.name)
        else:
            pulled = random.choice(DATABASE["GlobalSpells"])
            player.global_deck.append(pulled)
            self.status_label.text = f"Pulled Spell: {pulled.name}!\nDmg: {pulled.damage} | Blk: {pulled.block}"
            self.trigger_js_animation("card_back.png", pulled.name)
        player.save_game()

    def trigger_js_animation(self, img_file, entity_name):
        if platform == 'android' and getattr(self, 'webview', None):
            js_cmd = f"javascript:if(window.triggerSummon) triggerSummon('{img_file}', '{entity_name}');"
            wv = self.webview
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def trigger():
                try: wv.loadUrl(js_cmd)
                except Exception: pass
            trigger()

class UpgradeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.add_widget(self.layout)
    def on_enter(self): self.refresh_ui()
    def refresh_ui(self):
        self.layout.clear_widgets()
        status = f"ARCANE DUST SHRINE\nDust: {player.dust}  |  Gold: {player.currency}"
        self.layout.add_widget(make_wrapped_label(status, font_size='22sp', bold=True, size_hint=(1, 0.15)))
        self.layout.add_widget(make_wrapped_label("Select a global spell to empower (+5 Dmg, max Lv 3):", font_size='16sp', size_hint=(1, 0.08)))
        scroll = ScrollView(size_hint=(1, 0.62))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))
        
        for spell in player.global_deck:
            cost_dust = spell.level * 50
            btn_text = f"[{spell.spell_type}] {spell.name} (Lv {spell.level})\nDamage: {spell.damage} | Upgrade Cost: {cost_dust} Dust"
            btn = SmoothButton(text=btn_text, font_size='16sp', halign="center", valign="middle", size_hint_y=None, height=100, bg_color=(0.1, 0.3, 0.4, 1), disabled=(player.dust < cost_dust or spell.level >= 3))
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-20, None)))
            btn.bind(on_press=lambda inst, s=spell, c=cost_dust: self.upgrade_spell(s, c))
            list_layout.add_widget(btn)
            
        scroll.add_widget(list_layout)
        self.layout.add_widget(scroll)
        back_btn = SmoothButton(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15), bg_color=(0.2, 0.2, 0.2, 1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        self.layout.add_widget(back_btn)
        
    def upgrade_spell(self, spell, dust_cost):
        if player.dust >= dust_cost and spell.level < 3:
            player.dust -= dust_cost; spell.level += 1; spell.damage += 5
            player.save_game(); self.refresh_ui()

class GrimoireScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.webview = None
        self.web_placeholder = BoxLayout(size_hint=(1, 0.85))
        self.layout.add_widget(self.web_placeholder)
        back_btn = SmoothButton(text="Back to Menu", font_size='18sp', size_hint=(1, 0.15), bg_color=(0.2, 0.2, 0.2, 1))
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)
        self.add_widget(self.layout)

    def on_enter(self):
        if platform == 'android': self.load_android_webview()
        else:
            self.web_placeholder.clear_widgets()
            self.web_placeholder.add_widget(make_wrapped_label("[3D Grimoire Active]", font_size='16sp'))

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
            WebView = autoclass('android.webkit.WebView'); WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            metrics = autoclass('android.util.DisplayMetrics')(); activity.getWindowManager().getDefaultDisplay().getMetrics(metrics)
            
            lore_data = []
            for db_ent in DATABASE["Entities"]:
                if any(e.name == db_ent.name for e in player.roster): 
                    lore_data.append({"name": db_ent.name, "img": db_ent.image_file, "lore": db_ent.lore, "stats": f"Passive: {db_ent.passive_desc}"})
                else: 
                    lore_data.append({"name": "???", "img": "", "lore": "LORE LOCKED - Summon to reveal.", "stats": ""})
            
            # Base64 Encode to safely pass apostrophes to JS
            encoded_data = base64.b64encode(json.dumps(lore_data).encode('utf-8')).decode('utf-8')

            @run_on_ui_thread
            def create_webview():
                self.webview = WebView(activity)
                self.webview.getSettings().setJavaScriptEnabled(True); self.webview.getSettings().setAllowFileAccess(True)
                self.webview.setBackgroundColor(0); self.webview.setWebViewClient(WebViewClient())
                html_path = os.path.abspath(os.path.join('assets', 'grimoire.html'))
                if os.path.exists(html_path): self.webview.loadUrl(f'file://{html_path}')
                
                # Decode Base64 in Javascript directly
                js_cmd = f"javascript:if(window.loadGrimoire) loadGrimoire(atob('{encoded_data}'));"
                self.webview.loadUrl(js_cmd)
                
                params = autoclass('android.view.ViewGroup$LayoutParams')(metrics.widthPixels, int(metrics.heightPixels * 0.85))
                activity.addContentView(self.webview, params)
            create_webview()
        except Exception: pass

    def go_back(self, instance): self.manager.current = 'menu'

class ShopScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)
        
    def on_enter(self): self.refresh_shop()
        
    def refresh_shop(self):
        self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label("ALCHEMIST HUT", font_size='26sp', bold=True, size_hint=(1, 0.15)))
        self.layout.add_widget(make_wrapped_label(f"Gold: {player.currency}\nRestores 30 HP to all Coven members.", font_size='18sp', size_hint=(1, 0.15)))
        
        btn_heal = SmoothButton(text="Buy Healing Salve (+30 HP)\n75 Gold", font_size='18sp', size_hint=(1, 0.2), bg_color=(0.2, 0.6, 0.3, 1))
        btn_heal.bind(on_press=self.buy_heal); self.layout.add_widget(btn_heal)
        
        btn_spell = SmoothButton(text="Buy Random Global Spell\n120 Gold", font_size='18sp', size_hint=(1, 0.2), bg_color=(0.3, 0.2, 0.6, 1))
        btn_spell.bind(on_press=self.buy_spell); self.layout.add_widget(btn_spell)
        
        leave_btn = SmoothButton(text="Leave Shop & Continue Path", font_size='18sp', size_hint=(1, 0.2), bg_color=(0.2, 0.2, 0.2, 1))
        leave_btn.bind(on_press=self.leave_shop); self.layout.add_widget(leave_btn)

    def buy_heal(self, instance):
        if player.currency >= 75:
            player.currency -= 75
            for e in player.team: e.current_hp = min(e.max_hp, e.current_hp + 30)
            player.save_game(); self.refresh_shop()
            
    def buy_spell(self, instance):
        if player.currency >= 120:
            player.currency -= 120; player.global_deck.append(random.choice(DATABASE["GlobalSpells"]))
            player.save_game(); self.refresh_shop()
            
    def leave_shop(self, instance):
        player.current_tier += 1; player.save_game(); self.manager.get_screen('map').refresh_map(); self.manager.current = 'map'

class HangoutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)
        
    def on_enter(self): self.refresh_list()
        
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
                btn = SmoothButton(text=f"Talk to {entity.name} (Bond: {entity.bond}/100)", font_size='18sp', halign="center", valign="middle", size_hint_y=None, height=100, bg_color=(0.3, 0.1, 0.3, 1))
                btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0]-20, None)))
                btn.bind(on_press=lambda instance, e=entity: self.open_dialogue(e))
                list_layout.add_widget(btn)
            scroll.add_widget(list_layout); self.layout.add_widget(scroll)
            
        back_btn = SmoothButton(text="Back to Menu", font_size='18sp', size_hint=(1, 0.2), bg_color=(0.2, 0.2, 0.2, 1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu')); self.layout.add_widget(back_btn)

    def open_dialogue(self, entity):
        self.layout.clear_widgets()
        if not entity.dialogues:
            self.layout.add_widget(make_wrapped_label(f"{entity.name} stares at you silently.", font_size='20sp', size_hint=(1, 0.5)))
            btn = SmoothButton(text="Leave", font_size='18sp', size_hint=(1, 0.2), bg_color=(0.2, 0.2, 0.2, 1))
            btn.bind(on_press=lambda x: self.refresh_list()); self.layout.add_widget(btn)
            return
            
        dialogue = random.choice(entity.dialogues)
        self.layout.add_widget(make_wrapped_label(f"{entity.name}:\n\"{dialogue['prompt']}\"", font_size='20sp', size_hint=(1, 0.4)))
        options_layout = BoxLayout(orientation='vertical', spacing=15, size_hint=(1, 0.4))
        
        for opt in dialogue['options']:
            btn = SmoothButton(text=opt['text'], font_size='18sp', bg_color=(0.2, 0.3, 0.4, 1))
            btn.bind(on_press=lambda inst, e=entity, r=opt['reward']: self.resolve_dialogue(e, r))
            options_layout.add_widget(btn)
        self.layout.add_widget(options_layout)

    def resolve_dialogue(self, entity, reward):
        reward_type, val = reward
        result_text = ""
        if reward_type == "bond":
            entity.bond += val; result_text = f"Your bond with {entity.name} increased by {val}!"
            if entity.bond >= 100: 
                player.global_deck.append(entity.ultimate_spell); result_text += f"\nMax Bond Reached! You gained the global spell: {entity.ultimate_spell.name}."
        elif reward_type == "dust": 
            player.dust += val; result_text = f"You searched the area and found {val} Arcane Dust."
        elif reward_type == "currency": 
            player.currency += val; result_text = f"{entity.name} handed you {val} Gold."
            
        player.save_game(); self.layout.clear_widgets()
        self.layout.add_widget(make_wrapped_label(result_text, font_size='20sp', size_hint=(1, 0.7)))
        btn = SmoothButton(text="Continue", font_size='18sp', size_hint=(1, 0.3), bg_color=(0.2, 0.2, 0.2, 1))
        btn.bind(on_press=lambda x: self.refresh_list()); self.layout.add_widget(btn)

class DeckbuilderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(StoryScreen(name='story'))
        sm.add_widget(MapScreen(name='map'))
        sm.add_widget(TeamScreen(name='team'))
        sm.add_widget(UpgradeScreen(name='upgrade'))
        sm.add_widget(GrimoireScreen(name='grimoire'))
        sm.add_widget(ShopScreen(name='shop'))
        sm.add_widget(GachaScreen(name='gacha'))
        sm.add_widget(HangoutScreen(name='hangout'))
        sm.add_widget(CombatScreen(name='combat'))
        return sm
        
    def on_start(self): player.load_game()
    def on_pause(self): player.save_game(); return True
    def on_stop(self): player.save_game()

if __name__ == '__main__':
    DeckbuilderApp().run()
