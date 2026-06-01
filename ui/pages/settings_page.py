import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.theme import DARK, LIGHT, FONTS
from ui.components.topbar import Topbar
from ui.components.toast import Toast
from ui.modals.confirm_dialog import ConfirmDialog
from services.auth_service import get_current_user, set_active_company
from services.export_service import export_all_json, clear_all_data
from services.company_service import (
    get_company, update_company_currency, 
    update_company_ai_key, update_company_ai_model, update_company_ai_enabled,
    update_company_name, delete_company, get_all_companies, create_company
)
from services.currency_service import load_rates
from config import DB_PATH, load_app_settings, save_app_settings



class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, company_id, on_theme_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.on_theme_change = on_theme_change

        self.topbar = Topbar(self, title="Settings")
        self.topbar.pack(fill="x")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=24, pady=10)

        self._build_workspace_section()
        self._build_profile_section()
        self._build_appearance_section()
        self._build_data_section()
        self._build_ai_section()
        self._build_about_section()

    # ──────────────────────────────────────────────
    # Section builders
    # ──────────────────────────────────────────────
    def _section_card(self, title):
        """Create a titled card and return the inner content frame."""
        card = ctk.CTkFrame(self.scroll, corner_radius=10, border_width=1,
                            fg_color=("white", DARK["bg_secondary"]),
                            border_color=(LIGHT["border"], DARK["border"]))
        card.pack(fill="x", pady=8)

        ctk.CTkLabel(card, text=title, font=FONTS["heading"]).pack(
            anchor="w", padx=16, pady=(14, 6))

        sep = ctk.CTkFrame(card, height=1, fg_color=(LIGHT["border"], DARK["border"]))
        sep.pack(fill="x", padx=16, pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 14))
        return inner

    def _row(self, parent, label, widget=None, label_width=180):
        """Lay out a label + optional widget on a single row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=label, width=label_width, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        if widget:
            widget.pack(side="right")
        return row

    # ── Profile ──────────────────────────────────
    def _build_profile_section(self):
        user = get_current_user()
        inner = self._section_card("👤  Profile")

        ctk.CTkLabel(inner, text=f"Name:   {user['name'] if user else 'Unknown'}",
                     font=FONTS["body"],
                     text_color=(LIGHT["text_secondary"], DARK["text_secondary"])).pack(
            anchor="w", pady=3)
        ctk.CTkLabel(inner, text=f"Email:   {user['email'] if user else '—'}",
                     font=FONTS["body"],
                     text_color=(LIGHT["text_secondary"], DARK["text_secondary"])).pack(
            anchor="w", pady=3)

    # ── Workspace ─────────────────────────────────
    def _build_workspace_section(self):
        inner = self._section_card("🏢  Workspace Settings")

        company = get_company(self.company_id) if self.company_id else None
        current_name = company["name"] if company else "Unknown Workspace"

        # Rename Row
        rename_row = ctk.CTkFrame(inner, fg_color="transparent")
        rename_row.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(rename_row, text="Workspace Name", font=FONTS["body"], width=150, anchor="w").pack(side="left")
        
        self.workspace_name_var = ctk.StringVar(value=current_name)
        name_entry = ctk.CTkEntry(rename_row, textvariable=self.workspace_name_var, font=FONTS["body"], width=200)
        name_entry.pack(side="left", padx=(10, 10))
        
        save_name_btn = ctk.CTkButton(
            rename_row, text="💾 Save", width=80, height=28,
            font=FONTS["small"], fg_color=(LIGHT["green"], DARK["green"]),
            hover_color=(LIGHT["green_dark"], DARK["green_dark"]),
            command=self._save_workspace_name
        )
        save_name_btn.pack(side="left")

        # Delete Row
        del_btn = ctk.CTkButton(
            inner,
            text="🗑  Delete Workspace  (Danger)",
            font=FONTS["body"],
            fg_color=(LIGHT["red"], DARK["red"]),
            hover_color=("#a02020", "#c04040"),
            text_color=("white", "white"),
            height=36,
            command=self._confirm_delete_workspace,
        )
        del_btn.pack(fill="x", pady=(12, 4))

    def _save_workspace_name(self):
        if not self.company_id: return
        new_name = self.workspace_name_var.get().strip()
        if not new_name:
            Toast(self.winfo_toplevel(), "Workspace name cannot be empty", type="error")
            return
            
        success = update_company_name(self.company_id, new_name)
        if success:
            Toast(self.winfo_toplevel(), "Workspace renamed ✓", type="success")
            # Trigger global refresh to update sidebar dropdown
            try:
                self.winfo_toplevel().event_generate("<<CompanyChanged>>")
            except Exception:
                pass
        else:
            Toast(self.winfo_toplevel(), "Failed to rename workspace", type="error")

    def _confirm_delete_workspace(self):
        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Workspace",
            message="This will permanently delete this workspace and ALL its transactions, accounts, categories, and budgets.\n\nThis action CANNOT be undone.",
            on_confirm=self._do_delete_workspace,
        )

    def _do_delete_workspace(self):
        if not self.company_id: return
        user = get_current_user()

        # Capture toplevel NOW — after <<CompanyChanged>>, the SettingsPage
        # widget is destroyed and self.winfo_toplevel() would raise TclError.
        try:
            root = self.winfo_toplevel()
        except Exception:
            return

        try:
            # 1. Fetch remaining companies
            all_companies = get_all_companies()
            other_companies = [c for c in all_companies if c["id"] != self.company_id]

            # 2. Delete the current company
            delete_company(self.company_id)

            # 3. Handle fallback
            if other_companies:
                # Switch to another existing workspace
                new_active_id = other_companies[0]["id"]
                set_active_company(new_active_id)
                try:
                    root.event_generate("<<CompanyChanged>>")
                except Exception:
                    pass
                Toast(root, "Workspace deleted successfully", type="success")
            else:
                # No workspaces left — send user to manual setup screen
                from services.auth_service import _current_user
                import services.auth_service as _auth
                if _auth._current_user:
                    _auth._current_user["company_id"] = None
                try:
                    root.event_generate("<<ShowSetup>>")
                except Exception:
                    pass

        except Exception as e:
            Toast(root, f"Error deleting workspace: {e}", type="error")

    # ── Appearance ────────────────────────────────
    def _build_appearance_section(self):
        inner = self._section_card("🎨  Appearance")

        current = ctk.get_appearance_mode()  # "Dark" or "Light"

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=6)

        ctk.CTkLabel(row, text="Theme Mode", width=180, anchor="w",
                     font=FONTS["body"]).pack(side="left")

        self.theme_seg = ctk.CTkSegmentedButton(
            row,
            values=["System", "Light", "Dark"],
            command=self._apply_theme,
            font=FONTS["body"],
            width=210
        )
        self.theme_seg.set(current if current in ("Light", "Dark") else "System")
        self.theme_seg.pack(side="right")

    def _apply_theme(self, value):
        ctk.set_appearance_mode(value)
        if self.on_theme_change:
            self.on_theme_change(value)
        Toast(self.winfo_toplevel(), f"Theme set to {value}", type="success")

    def _apply_base_currency(self, new_currency):
        if not self.company_id:
            return
        success = update_company_currency(self.company_id, new_currency)
        if success:
            Toast(self.winfo_toplevel(), f"Base currency changed to {new_currency} ✓", type="success")
            # Trigger a global refresh so all pages update their KPIs immediately
            try:
                self.winfo_toplevel().event_generate("<<CompanyChanged>>")
            except Exception:
                pass
        else:
            Toast(self.winfo_toplevel(), "Failed to update currency", type="error")

    # ── Data & Currency ─────────────────────────
    def _build_data_section(self):
        from ui.modals.manage_currencies import ManageCurrenciesModal
        inner = self._section_card("💾  Data & Currency")

        # ── Database Path Selector ────────────────────────────────────────
        db_row = ctk.CTkFrame(inner, fg_color="transparent")
        db_row.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(db_row, text="📂  Database Location", font=FONTS["body"], anchor="w").pack(side="left")
        
        self.db_path_var = ctk.StringVar(value=str(DB_PATH))
        db_entry = ctk.CTkEntry(db_row, textvariable=self.db_path_var, font=FONTS["small"], width=300)
        db_entry.pack(side="left", padx=(20, 10), fill="x", expand=True)
        
        browse_btn = ctk.CTkButton(
            db_row, text="Browse...", width=80, height=28,
            font=FONTS["small"], command=self._browse_db_path
        )
        browse_btn.pack(side="right")
        
        save_db_btn = ctk.CTkButton(
            inner, text="💾  Update Database Path & Restart Required",
            font=FONTS["body"], height=36,
            fg_color=(LIGHT["green"], DARK["green"]),
            hover_color=(LIGHT["green_dark"], DARK["green_dark"]),
            command=self._save_db_path
        )
        save_db_btn.pack(fill="x", pady=(0, 16))

        # ── Base Currency Selector ────────────────────────────────────────
        bc_row = ctk.CTkFrame(inner, fg_color="transparent")
        bc_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(bc_row, text="🏦  Base Currency", font=FONTS["body"], anchor="w").pack(side="left")

        # Build dropdown choices from exchange rate config + ensure AZN/USD are always present
        rates = load_rates()
        all_currencies = sorted(set(list(rates.keys()) + ["AZN", "USD", "EUR", "GBP"]))

        # Pre-select current company currency
        company = get_company(self.company_id) if self.company_id else None
        current_bc = company['currency'] if company else "AZN"

        self.bc_var = ctk.StringVar(value=current_bc)
        bc_dropdown = ctk.CTkOptionMenu(
            bc_row,
            variable=self.bc_var,
            values=all_currencies,
            font=FONTS["body"],
            width=120,
            command=self._apply_base_currency
        )
        bc_dropdown.pack(side="right")

        # Manage Exchange Rates
        curr_btn = ctk.CTkButton(
            inner,
            text="💱  Manage Exchange Rates",
            font=FONTS["body"],
            fg_color=(LIGHT["bg_primary"], DARK["bg_primary"]),
            hover_color=(LIGHT["border"], DARK["border"]),
            text_color=(LIGHT["text_primary"], DARK["text_primary"]),
            border_width=1,
            border_color=(LIGHT["border"], DARK["border"]),
            height=36,
            command=lambda: ManageCurrenciesModal(self.winfo_toplevel(), self.company_id, lambda: None)
        )
        curr_btn.pack(fill="x", pady=4)

        # Export JSON
        export_btn = ctk.CTkButton(
            inner,
            text="⬇  Export All Data (JSON)",
            font=FONTS["body"],
            fg_color=(LIGHT["blue"], DARK["blue"]),
            hover_color=(LIGHT["blue_light"], DARK["blue_light"]),
            text_color=("white", "white"),
            height=36,
            command=self._export_json,
        )
        export_btn.pack(fill="x", pady=4)

        # Clear data
        clear_btn = ctk.CTkButton(
            inner,
            text="🗑  Clear All Data  (Danger)",
            font=FONTS["body"],
            fg_color=(LIGHT["red"], DARK["red"]),
            hover_color=("#a02020", "#c04040"),
            text_color=("white", "white"),
            height=36,
            command=self._confirm_clear,
        )
        clear_btn.pack(fill="x", pady=4)

    def _export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="ktib_cashflow_backup.json",
            title="Export Data"
        )
        if not path:
            return
        result = export_all_json(path, self.company_id)
        if result:
            Toast(self.winfo_toplevel(), f"Exported to {os.path.basename(path)}", type="success")
        else:
            Toast(self.winfo_toplevel(), "Export failed", type="error")

    def _confirm_clear(self):
        ConfirmDialog(
            self.winfo_toplevel(),
            title="Clear All Data",
            message="This will permanently delete ALL transactions, accounts, categories, "
                    "and planned payments.\n\nThis action CANNOT be undone.",
            on_confirm=self._do_clear,
        )

    def _do_clear(self):
        try:
            clear_all_data(self.company_id)
            Toast(self.winfo_toplevel(), "All data cleared successfully", type="success")
        except Exception as e:
            Toast(self.winfo_toplevel(), f"Error: {e}", type="error")

    def _browse_db_path(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All files", "*.*")],
            initialfile=os.path.basename(str(DB_PATH)),
            title="Select Database Location"
        )
        if path:
            self.db_path_var.set(path)

    def _save_db_path(self):
        new_path = self.db_path_var.get().strip()
        if not new_path:
            return
            
        # Check if directory exists
        dirname = os.path.dirname(new_path)
        if not os.path.exists(dirname):
            Toast(self, "Directory does not exist", type="error")
            return

        settings = load_app_settings()
        settings["db_path"] = new_path
        save_app_settings(settings)
        
        messagebox.showinfo("Restart Required", 
                            "Database path has been updated in settings.\n\n"
                            "The application will now close. Please restart it to connect to the new database location.")
        self.winfo_toplevel().quit()

    # ── AI Assistant ──────────────────────────────
    def _build_ai_section(self):
        inner = self._section_card("🤖  AI Assistant")

        company = get_company(self.company_id) if self.company_id else None
        current_key = company.get("ai_api_key", "") if company else ""
        current_model = company.get("ai_model", "gemini-2.5-flash") if company else "gemini-2.5-flash"
        current_enabled = company.get("ai_enabled", True) if company else True

        # Description
        ctk.CTkLabel(inner,
            text="Choose your preferred Gemini model and enter your API key.",
            font=FONTS["small"],
            text_color=(LIGHT["text_secondary"], DARK["text_secondary"]),
            anchor="w").pack(fill="x", pady=(0, 8))

        # Toggle row
        toggle_row = ctk.CTkFrame(inner, fg_color="transparent")
        toggle_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(toggle_row, text="Show AI Insights in Cash Flow", font=FONTS["body"], anchor="w").pack(side="left")
        
        self.ai_enabled_var = ctk.BooleanVar(value=current_enabled)
        ai_switch = ctk.CTkSwitch(toggle_row, text="", variable=self.ai_enabled_var)
        ai_switch.pack(side="right")

        # Model Selector
        model_row = ctk.CTkFrame(inner, fg_color="transparent")
        model_row.pack(fill="x", pady=(0, 8))
# ... existing model_row code ...
        ctk.CTkLabel(model_row, text="AI Model Version", font=FONTS["body"], width=150, anchor="w").pack(side="left")
        
        self.model_var = ctk.StringVar(value=current_model)
        model_dropdown = ctk.CTkOptionMenu(
            model_row,
            variable=self.model_var,
            values=[
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
                "gemini-1.5-pro",
                "gemini-2.0-flash-exp"
            ],
            font=FONTS["body"],
            width=200
        )
        model_dropdown.pack(side="right")

        # Key entry row
        key_row = ctk.CTkFrame(inner, fg_color="transparent")
        key_row.pack(fill="x", pady=(0, 8))
        key_row.grid_columnconfigure(0, weight=1)

        self._key_var = ctk.StringVar(value=current_key)
        key_entry = ctk.CTkEntry(
            key_row,
            textvariable=self._key_var,
            placeholder_text="AIza…",
            font=FONTS["body"],
            show="*",
        )
        key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._show_key = False
        def toggle_show():
            self._show_key = not self._show_key
            key_entry.configure(show="" if self._show_key else "*")
            toggle_btn.configure(text="🙈 Hide" if self._show_key else "👁 Show")

        toggle_btn = ctk.CTkButton(
            key_row, text="👁 Show", width=80, height=36,
            font=FONTS["small"],
            fg_color=(LIGHT["bg_tertiary"], DARK["bg_tertiary"]),
            hover_color=(LIGHT["border"], DARK["border"]),
            text_color=(LIGHT["text_primary"], DARK["text_primary"]),
            command=toggle_show,
        )
        toggle_btn.grid(row=0, column=1)

        # Save button
        ctk.CTkButton(
            inner,
            text="💾  Save API Key",
            font=FONTS["body"],
            fg_color=(LIGHT["green"], DARK["green"]),
            hover_color=(LIGHT["green_dark"], DARK["green_dark"]),
            text_color=("white", "white"),
            height=36,
            command=self._save_api_key,
        ).pack(fill="x", pady=(4, 0))

        # Link to get key
        ctk.CTkLabel(inner,
            text="Get a free key at: https://aistudio.google.com",
            font=FONTS["small"],
            text_color=(LIGHT["blue"], DARK["blue"]),
            cursor="hand2",
            anchor="w").pack(anchor="w", pady=(6, 0))

    def _save_api_key(self):
        new_key = self._key_var.get().strip()
        new_model = self.model_var.get()
        new_enabled = self.ai_enabled_var.get()

        if not self.company_id:
            Toast(self.winfo_toplevel(), "No active company found", type="error")
            return

        try:
            success_key = update_company_ai_key(self.company_id, new_key)
            success_model = update_company_ai_model(self.company_id, new_model)
            success_enabled = update_company_ai_enabled(self.company_id, new_enabled)
            
            if not success_key or not success_model or not success_enabled:
                Toast(self.winfo_toplevel(), "Failed to update AI settings", type="error")
                return

            Toast(self.winfo_toplevel(), "AI Settings saved ✓", type="success")
        except Exception as e:
            Toast(self.winfo_toplevel(), f"Failed to save: {e}", type="error")

    # ── About ─────────────────────────────────────
    def _build_about_section(self):
        inner = self._section_card("ℹ️  About")

        for label, value in [
            ("Application", "KTIB Cash Flow — Financial Management"),
            ("Version", "1.0.0"),
            ("Built with", "Python · CustomTkinter · SQLAlchemy"),
        ]:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, width=180, anchor="w", font=FONTS["body"],
                         text_color=(LIGHT["text_secondary"], DARK["text_secondary"])).pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w", font=FONTS["body"]).pack(side="left")
