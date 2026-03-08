import os
import json
import nbtlib
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

def get_config(key_path):
    try:
        with open("./config.json", 'r') as file:
            data = json.load(file)

        keys = key_path.split('.')
        value = data
        for key in keys:
            value = value[key]
        
        return value
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        return f"Error: {e}"

PATH_PLAYERDATA = get_config("paths.playerdata")
PATH_STATS      = get_config("paths.stats")
PATH_ASSETS     = get_config("paths.assets")
FILE_USERCACHE  = get_config("server_files.usercache")
FILE_OPS        = get_config("server_files.ops")
FILE_WHITELIST  = get_config("server_files.whitelist")

class StatBar(ctk.CTkFrame):
    def __init__(self, master, label_text, color, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.label = ctk.CTkLabel(self, text=label_text, width=100, anchor="w", font=("Segoe UI", 12, "bold"))
        self.label.pack(side="left")
        self.progress = ctk.CTkProgressBar(self, progress_color=color, height=14)
        self.progress.pack(side="left", fill="x", expand=True, padx=10)
        self.val_label = ctk.CTkLabel(self, text="0/0", width=60)
        self.val_label.pack(side="left")

    def update_bar(self, current, maximum):
        try:
            val = float(current)
            mx = float(maximum)
            pct = max(0, min(1, val / mx)) if mx > 0 else 0
            self.progress.set(pct)
            self.val_label.configure(text=f"{int(val)}/{int(mx)}")
        except:
            self.progress.set(0)
            self.val_label.configure(text="0/0")

class InvSlot(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, width=58, height=58, fg_color="#3C3C3C", border_width=2, border_color="#121212", **kwargs)
        self.grid_propagate(False)
        self.img_label = ctk.CTkLabel(self, text="", image=None)
        self.img_label.place(relx=0.5, rely=0.5, anchor="center")
        self.count_label = ctk.CTkLabel(self, text="", font=("Arial", 11, "bold"))
        self.count_label.place(relx=0.95, rely=0.95, anchor="se")
        
        self.item_id = ""
        self.bind("<Enter>", lambda e: self.configure(border_color="#FFFFFF"))
        self.bind("<Leave>", lambda e: self.configure(border_color="#121212"))

    def set_item(self, item_id, count, icon=None):
        self.clear()
        self.item_id = str(item_id)
        
        clean_count = int(count)
        self.count_label.configure(text=str(clean_count) if clean_count > 1 else "")
        
        if icon:
            self.img_label.configure(image=icon, text="")
        else:
            display_name = self.item_id.split(':')[-1].replace('_', '\n')[:10]
            self.img_label.configure(text=display_name, image=None, font=("Arial", 7))

    def clear(self):
        self.item_id = ""
        self.img_label.configure(image="", text="")
        self.count_label.configure(text="")
        self.update_idletasks()

class EliteMCExplorer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Server Player Viewer [{get_config('ui.server_name')}]")
        self.geometry(get_config("ui.window_size"))
        ctk.set_appearance_mode(get_config("ui.appearance_mode"))
        
        self.server_data = self._load_server_files()
        self.img_cache = {}
        self.inv_widgets = {}
        self.ender_widgets = {}
        
        self._setup_ui()
        self._scan_player_files()

    def _load_server_files(self):
        data = {"names": {}, "ops": [], "white": []}
        for path, key in [(FILE_USERCACHE, "names"), (FILE_OPS, "ops"), (FILE_WHITELIST, "white")]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        content = json.load(f)
                        if key == "names":
                            for entry in content: data["names"][entry['uuid']] = entry['name']
                        else:
                            data[key] = [e.get('uuid') for e in content if isinstance(e, dict)]
                except: pass
        return data

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="Players", font=("Segoe UI", 22, "bold")).pack(pady=20)
        self.p_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.p_scroll.pack(fill="both", expand=True, padx=10)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.t_status = self.tabs.add("Status")
        self.t_inv = self.tabs.add("Inventory")
        self.t_ender = self.tabs.add("Ender Chest")

        self._init_status_ui()
        self._init_inv_ui(self.t_inv, self.inv_widgets)
        self._init_inv_ui(self.t_ender, self.ender_widgets, is_ender=True)

    def _init_status_ui(self):
        v_frame = ctk.CTkFrame(self.t_status, fg_color="#222222", corner_radius=15)
        v_frame.pack(fill="x", padx=30, pady=20)
        self.hp_bar = StatBar(v_frame, "Health", "#FF4B4B")
        self.hp_bar.pack(fill="x", padx=20, pady=10)
        self.hg_bar = StatBar(v_frame, "Hunger", "#FF9F43")
        self.hg_bar.pack(fill="x", padx=20, pady=10)
        self.xp_bar = StatBar(v_frame, "XP Levels", "#55E6C1")
        self.xp_bar.pack(fill="x", padx=20, pady=10)

        self.info_box = ctk.CTkTextbox(self.t_status, font=("Consolas", 14), fg_color="#121212")
        self.info_box.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    def _init_inv_ui(self, parent, widget_dict, is_ender=False):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        if not is_ender:
            a_frame = ctk.CTkFrame(container, fg_color="transparent")
            a_frame.grid(row=0, column=0, rowspan=2, padx=(0, 30))
            for i, key in enumerate(['head', 'chest', 'legs', 'feet', 'offhand']):
                slot = InvSlot(a_frame)
                slot.grid(row=i, column=0, pady=2)
                widget_dict[key] = slot

        g_frame = ctk.CTkFrame(container, fg_color="transparent")
        g_frame.grid(row=0, column=1)
        for r in range(3):
            for c in range(9):
                sid = (9 + r*9 + c) if not is_ender else (r*9 + c)
                slot = InvSlot(g_frame)
                slot.grid(row=r, column=c, padx=2, pady=2)
                widget_dict[sid] = slot

        if not is_ender:
            h_frame = ctk.CTkFrame(container, fg_color="transparent")
            h_frame.grid(row=1, column=1, pady=(20, 0))
            for c in range(9):
                slot = InvSlot(h_frame)
                slot.grid(row=0, column=c, padx=2, pady=2)
                widget_dict[c] = slot

    def _get_icon(self, item_id):
        name = str(item_id).replace("minecraft:", "")
        if name in self.img_cache: return self.img_cache[name]
        path = os.path.join(PATH_ASSETS, f"{name}.png")
        if os.path.exists(path):
            try:
                img = ctk.CTkImage(Image.open(path), size=(40, 40))
                self.img_cache[name] = img
                return img
            except: pass
        return None

    def _scan_player_files(self):
        if not os.path.exists(PATH_PLAYERDATA): return
        for f in os.listdir(PATH_PLAYERDATA):
            if f.endswith(".dat"):
                uuid = f.replace(".dat", "")
                name = self.server_data["names"].get(uuid, uuid[:12])
                ctk.CTkButton(self.p_scroll, text=name, anchor="w",
                             command=lambda u=uuid, fl=f: self._display_player(u, fl)).pack(pady=2, fill="x")

    def _display_player(self, uuid, filename):
        try:
            nbt = nbtlib.load(os.path.join(PATH_PLAYERDATA, filename))
            
            for w in self.inv_widgets.values(): w.clear()
            for w in self.ender_widgets.values(): w.clear()

            eq_data = nbt.get('equipment', {})
            for key in ['head', 'chest', 'legs', 'feet', 'offhand']:
                if key in eq_data:
                    item = eq_data[key]
                    item_id = str(item.get('id', ''))
                    if item_id:
                        count = item.get('count', 1)
                        self.inv_widgets[key].set_item(item_id, count, self._get_icon(item_id))

            for item in nbt.get('Inventory', []):
                sid = int(item.get('Slot', -999))
                if sid in self.inv_widgets:
                    item_id = str(item.get('id', ''))
                    count = item.get('count') or item.get('Count', 1)
                    self.inv_widgets[sid].set_item(item_id, count, self._get_icon(item_id))

            for item in nbt.get('EnderItems', []):
                sid = int(item.get('Slot', -999))
                if sid in self.ender_widgets:
                    item_id = str(item.get('id', ''))
                    count = item.get('count') or item.get('Count', 1)
                    self.ender_widgets[sid].set_item(item_id, count, self._get_icon(item_id))

            self.hp_bar.update_bar(nbt.get('Health', 0), 20)
            self.hg_bar.update_bar(nbt.get('foodLevel', 0), 20)
            self.xp_bar.update_bar(nbt.get('XpLevel', 0), 100)

            kills, deaths = 0, 0
            stat_path = os.path.join(PATH_STATS, f"{uuid}.json")
            if os.path.exists(stat_path):
                try:
                    with open(stat_path, 'r') as f:
                        s_data = json.load(f).get('stats', {})
                        kills = s_data.get('minecraft:killed_by', {}).get('minecraft:player', 0)
                        deaths = s_data.get('minecraft:custom', {}).get('minecraft:deaths', 0)
                except: pass

            potion_effects = nbt.get('active_effects', []) or nbt.get('ActiveEffects', [])
            eff_str = ", ".join([str(e.get('id', '')).split(':')[-1] for e in potion_effects]) if potion_effects else "None"

            def get_game_mode():
                mode = nbt.get('playerGameType', nbt.get('GameType', 0))
                return {0: "Survival", 1: "Creative", 2: "Adventure", 3: "Spectator"}.get(mode, str(mode))

            info = [
                f"--- IDENTITY ---",
                f"Username:    {self.server_data['names'].get(uuid, 'Unknown')}",
                f"UUID:        {uuid}",
                f"GameMode:    {get_game_mode()}",
                f"",
                f"--- SERVER PERMISSIONS ---",
                f"Is OP:       {'YES' if uuid in self.server_data['ops'] else 'NO'}",
                f"Whitelisted: {'YES' if uuid in self.server_data['white'] else 'NO'}",
                f"",
                f"--- WORLD DATA ---",
                f"Position:    {[round(float(x), 2) for x in nbt.get('Pos', [0,0,0])]}",
                f"Dimension:   {nbt.get('Dimension', 'Overworld')}",
                f"",
                f"--- STATISTICS ---",
                f"Potion Effects:  {eff_str}",
                f"Player Kills:    {kills}",
                f"Death Count:     {deaths}"
            ]
            self.info_box.delete("1.0", "end")
            self.info_box.insert("1.0", "\n".join(info))

        except Exception as e:
            messagebox.showerror("NBT Error", f"Failed to load: {e}")

if __name__ == "__main__":
    app = EliteMCExplorer()
    app.mainloop()