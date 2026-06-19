import customtkinter as ctk
from ui.theme import THEME, FONTS


class Modal(ctk.CTkToplevel):
    """
    Premium base modal:
      - Colored top accent bar
      - Bold title + subtitle
      - Styled ✕ close button
      - Escape to close
    """

    def __init__(self, master, title="Modal", subtitle=None,
                 width=480, height=580, accent_color=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.configure(fg_color=THEME["bg_primary"])
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width()  // 2) - (width  // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        self.bind("<Escape>", lambda e: self.destroy())

        # ── Top accent bar ────────────────────────────────────────────────────
        accent = accent_color or THEME["blue"]
        ctk.CTkFrame(self, height=3, corner_radius=0,
                     fg_color=accent).pack(fill="x", side="top")

        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"],
                               corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", padx=20, fill="y")

        ctk.CTkLabel(title_col, text=title, font=("Inter", 16, "bold"),
                     text_color=THEME["text_primary"]).pack(anchor="w", pady=(12, 0))
        if subtitle:
            ctk.CTkLabel(title_col, text=subtitle, font=FONTS["small"],
                         text_color=THEME["text_tertiary"]).pack(anchor="w")

        # Close button
        close_btn = ctk.CTkButton(
            header, text="✕", width=32, height=32,
            corner_radius=16,
            fg_color="transparent",
            hover_color=THEME["bg_tertiary"],
            text_color=THEME["text_tertiary"],
            font=("Inter", 14, "bold"),
            command=self.destroy)
        close_btn.pack(side="right", padx=16, pady=14)

        # ── Divider ───────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=THEME["border"],
                     corner_radius=0).pack(fill="x")

        # ── Content area ──────────────────────────────────────────────────────
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=24, pady=20)

    # ── Safe helpers ──────────────────────────────────────────────────────────

    def focus_set(self):
        try:
            if self.winfo_exists():
                super().focus_set()
        except Exception:
            pass

    def destroy(self):
        try:
            self.grab_release()
            if self.master and self.master.winfo_exists():
                self.master.focus_set()
            self.update_idletasks()
        except Exception:
            pass
        finally:
            if self.winfo_exists():
                self.after(10, super().destroy)
