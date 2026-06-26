import customtkinter as ctk
from ui.theme import THEME, FONTS, validate_hex_color
from ui.components.topbar import Topbar
from ui.components.search_bar import SearchBar
from services.category_service import get_categories, delete_category
from ui.modals.add_category import AddCategoryModal
from ui.modals.edit_category import EditCategoryModal
from ui.modals.confirm_dialog import ConfirmDialog
from ui.components.toast import Toast
from ui.utils.thread_worker import ThreadWorker
from ui.components.empty_state import EmptyState
from ui.components.loading_state import LoadingState

class CategoryCard(ctk.CTkFrame):
    def __init__(self, master, category, on_edit, on_delete, is_sub=False, **kwargs):
        super().__init__(master, fg_color=THEME["bg_primary"], corner_radius=10, 
                         border_width=1, border_color=THEME["border"], **kwargs)
        self.category = category
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.is_sub = is_sub

        # Left side: Color strip / dot
        safe_color = validate_hex_color(self.category.color)
        dot_size = 12 if is_sub else 16
        color_dot = ctk.CTkFrame(self, width=dot_size, height=dot_size, corner_radius=dot_size//2, fg_color=safe_color)
        color_dot.pack(side="left", padx=(16, 10), pady=16)

        # Info section
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=12)

        name_font = FONTS["body"] if is_sub else FONTS["heading"]
        ctk.CTkLabel(info_frame, text=self.category.name, font=name_font, 
                     text_color=THEME["text_primary"]).pack(anchor="w")
        
        if not is_sub:
            # Subtle "Type" badge
            badge_color = THEME["green_light"] if category.type == "income" else THEME["red_light"]
            badge_text_color = THEME["green_dark"] if category.type == "income" else THEME["red"]
            badge = ctk.CTkFrame(info_frame, fg_color=badge_color, corner_radius=6)
            badge.pack(anchor="w", pady=(4, 0))
            ctk.CTkLabel(badge, text=self.category.type.upper(), font=FONTS["small"], 
                         text_color=badge_text_color, height=20).pack(padx=8, pady=2)
        else:
             ctk.CTkLabel(info_frame, text="Category", font=FONTS["small"], 
                          text_color=THEME["text_tertiary"]).pack(anchor="w")

        # Right side: Delete button
        del_btn = ctk.CTkButton(self, text="🗑", width=36, height=36, corner_radius=8,
                                fg_color="transparent", hover_color=THEME["red_light"],
                                text_color=THEME["red"], font=FONTS["heading"],
                                command=lambda: self.on_delete(self.category.id))
        del_btn.pack(side="right", padx=12)
        
        edit_btn = ctk.CTkButton(self, text="✏️", width=36, height=36, corner_radius=8,
                                 fg_color="transparent", hover_color=THEME["bg_tertiary"],
                                 text_color=THEME["blue"], font=FONTS["heading"],
                                 command=lambda: self.on_edit(self.category))
        edit_btn.pack(side="right", padx=2)

        # Hover effects
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Bind children to propagate hover
        hover_children = [color_dot, info_frame]
        if not is_sub:
             try:
                 hover_children.append(badge)
             except UnboundLocalError:
                 pass
                 
        for child in hover_children:
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.configure(border_color=THEME["blue"], fg_color=THEME["bg_tertiary"])
        
    def _on_leave(self, e):
        self.configure(border_color=THEME["border"], fg_color=THEME["bg_primary"])


class CategoriesPage(ctk.CTkFrame):
    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self._active_search = ""

        self.topbar = Topbar(self, title="Clients & Categories")
        self.topbar.pack(fill="x")

        # Top Filters Row
        self._build_filters()

        # Container for the two columns
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Left Column (Income)
        self.col_inc, self.inc_lbl = self._build_column(self.content_frame, "📈 Income Clients & Categories", "income", 0)
        # Right Column (Expense)
        self.col_exp, self.exp_lbl = self._build_column(self.content_frame, "📉 Expense Clients & Categories", "expense", 1)

        self.refresh()

    def _build_filters(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10,
                           border_width=1, border_color=THEME["border"])
        bar.pack(fill="x", padx=24, pady=16)

        self.search_bar = SearchBar(bar, self._on_search)
        self.search_bar.pack(side="left", padx=10, pady=8)

        self.count_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"], text_color=THEME["text_tertiary"])
        self.count_lbl.pack(side="right", padx=16)

    def _on_search(self, query):
        if hasattr(self, '_search_after_id') and self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._active_search = query.lower()
        self._search_after_id = self.after(400, self.refresh)

    def _build_column(self, parent, title, t_filter, col_index):
        col_frame = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        col_frame.grid(row=0, column=col_index, sticky="nsew", padx=8, pady=8)
        
        # Header
        header = ctk.CTkFrame(col_frame, fg_color="transparent", height=60)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text=title, font=FONTS["title"], 
                     text_color=THEME["text_primary"]).pack(side="left")
                     
        add_btn = ctk.CTkButton(header, text="+ Add New", width=100, height=36, 
                                font=FONTS["body"], fg_color=THEME["blue"], 
                                hover_color=THEME["blue_light"],
                                command=lambda f=t_filter: self._add_cat(f))
        add_btn.pack(side="right")
        
        # Separator
        sep = ctk.CTkFrame(col_frame, height=1, fg_color=THEME["border"])
        sep.pack(fill="x", padx=20, pady=(0, 10))
        
        # Loading State component created dynamically when needed

        # Scrollable area for cards
        scroll = ctk.CTkScrollableFrame(col_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        return scroll, col_frame

    def refresh(self):
        if not self.company_id: return
        try:
            if not self.winfo_exists(): return
        except Exception: return

        # Clear existing cards and show loading state
        for scroll in [self.col_inc, self.col_exp]:
            for w in scroll.winfo_children(): 
                w.destroy()
                
        if hasattr(self, '_loading_states'):
            for ls in self._loading_states:
                ls.destroy()
        self._loading_states = []
        for col_frame in [self.inc_lbl, self.exp_lbl]: # these are now the col_frames
            ls = LoadingState(col_frame, text="Loading clients...")
            ls.pack(pady=20)
            self._loading_states.append(ls)
            
        self.count_lbl.configure(text="Searching...")

        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        inc_cats = get_categories(self.company_id, type_filter="income")
        exp_cats = get_categories(self.company_id, type_filter="expense")
        return {"income": inc_cats, "expense": exp_cats}

    def _update_ui(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception: return

        if hasattr(self, '_loading_states'):
            for ls in self._loading_states:
                ls.destroy()
        self._loading_states = []

        total_visible = 0

        for scroll, t_filter, raw_cats in [(self.col_inc, "income", data["income"]), 
                                                (self.col_exp, "expense", data["expense"])]:
            
            # Apply search filter
            filtered_cats = []
            if self._active_search:
                q = self._active_search
                for c in raw_cats:
                    if q in c.name.lower():
                        filtered_cats.append(c)
                        # Also include parent if it's a child
                        if c.parent_id:
                            parent = next((p for p in raw_cats if p.id == c.parent_id), None)
                            if parent and parent not in filtered_cats:
                                filtered_cats.append(parent)
                        # Also include children if it's a parent
                        children = [ch for ch in raw_cats if ch.parent_id == c.id]
                        for ch in children:
                            if ch not in filtered_cats:
                                filtered_cats.append(ch)
            else:
                filtered_cats = raw_cats

            if not filtered_cats:
                empty = EmptyState(scroll, icon="🗂️", 
                                   title="No clients or categories found", 
                                   subtitle="Try a different search or add a new one.")
                empty.pack(fill="both", expand=True, pady=40)
                continue
                
            total_visible += len(filtered_cats)

            # Group by hierarchy
            parents = [c for c in filtered_cats if c.parent_id is None]
            children = [c for c in filtered_cats if c.parent_id is not None]
            
            for p in parents:
                # Parent Card
                card = CategoryCard(scroll, category=p, on_edit=self._edit_cat, on_delete=self._prompt_delete)
                card.pack(fill="x", padx=10, pady=6)
                
                # Children Cards (indented)
                p_children = [c for c in children if c.parent_id == p.id]
                for c in p_children:
                    sub_card = CategoryCard(scroll, category=c, on_edit=self._edit_cat, on_delete=self._prompt_delete, is_sub=True)
                    sub_card.pack(fill="x", padx=(40, 10), pady=2)
            
            # Orphan children (if their parent was filtered out but they weren't somehow, though the logic above prevents this)
            orphans = [c for c in children if not any(p.id == c.parent_id for p in parents)]
            for c in orphans:
                card = CategoryCard(scroll, category=c, on_edit=self._edit_cat, on_delete=self._prompt_delete)
                card.pack(fill="x", padx=10, pady=6)

        self.count_lbl.configure(text=f"{total_visible} items")

    def _add_cat(self, t_filter):
        AddCategoryModal(self.winfo_toplevel(), self.company_id, t_filter, self.refresh)

    def _edit_cat(self, category):
        EditCategoryModal(self.winfo_toplevel(), category, self.refresh)

    def _prompt_delete(self, cid):
        def do_delete():
            if delete_category(cid):
                Toast(self.master, "Category Deleted", type="success")
                self.refresh()
        ConfirmDialog(self.winfo_toplevel(), title="Delete Client / Category", 
                      message="Are you sure you want to delete this client / category?\nTransactions associated with it will lose their classification.", 
                      on_confirm=do_delete)
