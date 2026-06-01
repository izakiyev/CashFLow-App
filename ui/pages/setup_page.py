import customtkinter as ctk
from ui.theme import THEME, FONTS, DARK
from ui.components.toast import Toast

CURRENCIES = ["AZN", "USD", "EUR", "GBP", "TRY", "RUB", "UAH", "KZT"]

class SetupWorkspaceScreen(ctk.CTkFrame):
    """
    Full-screen onboarding shown when:
      - The app is opened for the very first time (no user record)
      - The user has deleted all their workspaces
    On completion it calls on_complete() so the app can proceed to the dashboard.
    """
    def __init__(self, master, on_complete, **kwargs):
        super().__init__(master, fg_color=DARK["bg_primary"], corner_radius=0, **kwargs)
        self.on_complete = on_complete
        self._build_ui()

    def _build_ui(self):
        # Centre column
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        card = ctk.CTkFrame(self, fg_color=DARK["bg_secondary"], corner_radius=20,
                            border_width=1, border_color=DARK["border"], width=480)
        card.grid(row=1, column=1, padx=40, pady=40, sticky="n")
        card.grid_propagate(False)
        card.configure(width=480, height=560)

        # Logo / Icon
        ctk.CTkLabel(card, text="💼", font=("Segoe UI Emoji", 52)).pack(pady=(40, 0))
        ctk.CTkLabel(card, text="Welcome to Ktib Cashflow", font=("Inter", 26, "bold"),
                     text_color=DARK["text_primary"]).pack(pady=(10, 4))
        ctk.CTkLabel(card, text="Set up your first workspace to get started.",
                     font=FONTS["body"], text_color=DARK["text_tertiary"]).pack(pady=(0, 30))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=36)

        # Your Name
        ctk.CTkLabel(form, text="Your Name", font=FONTS["body"],
                     text_color=DARK["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.name_entry = ctk.CTkEntry(form, placeholder_text="e.g. Ilkin Zekiyev",
                                       font=FONTS["heading"], height=42, corner_radius=10)
        self.name_entry.pack(fill="x", pady=(0, 16))

        # Workspace Name
        ctk.CTkLabel(form, text="Workspace Name", font=FONTS["body"],
                     text_color=DARK["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.workspace_entry = ctk.CTkEntry(form, placeholder_text="e.g. My Company or Personal Finances",
                                            font=FONTS["heading"], height=42, corner_radius=10)
        self.workspace_entry.pack(fill="x", pady=(0, 16))

        # Base Currency
        ctk.CTkLabel(form, text="Base Currency", font=FONTS["body"],
                     text_color=DARK["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.currency_var = ctk.StringVar(value="AZN")
        ctk.CTkOptionMenu(form, variable=self.currency_var, values=CURRENCIES,
                          font=FONTS["body"], height=42, corner_radius=10).pack(fill="x", pady=(0, 28))

        # Create Button
        self.create_btn = ctk.CTkButton(
            form, text="Create Workspace  →", height=46,
            font=("Inter", 15, "bold"),
            fg_color=DARK["green"], hover_color=DARK["green_dark"],
            corner_radius=12,
            command=self._submit
        )
        self.create_btn.pack(fill="x")

        # Give name field focus
        self.after(100, self.name_entry.focus)
        self.name_entry.bind("<Return>", lambda e: self.workspace_entry.focus())
        self.workspace_entry.bind("<Return>", lambda e: self._submit())

    def _submit(self):
        from services.auth_service import setup_new_user_and_workspace

        name = self.name_entry.get().strip()
        workspace = self.workspace_entry.get().strip()
        currency = self.currency_var.get()

        if not name:
            self.name_entry.configure(border_color="red", border_width=2)
            self.name_entry.focus()
            return
        self.name_entry.configure(border_color=DARK["border"], border_width=1)

        if not workspace:
            self.workspace_entry.configure(border_color="red", border_width=2)
            self.workspace_entry.focus()
            return
        self.workspace_entry.configure(border_color=DARK["border"], border_width=1)

        self.create_btn.configure(state="disabled", text="Creating…")
        self.after(50, lambda: self._do_create(name, workspace, currency))

    def _do_create(self, name, workspace, currency):
        try:
            from services.auth_service import setup_new_user_and_workspace
            setup_new_user_and_workspace(name, workspace, currency)
            self.on_complete()
        except Exception as e:
            self.create_btn.configure(state="normal", text="Create Workspace  →")
            Toast(self.winfo_toplevel(), f"Error: {e}", type="error")
