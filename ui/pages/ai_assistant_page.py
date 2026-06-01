"""
AI Assistant Page — split layout:
  Left 60%: Chat interface with styled bubbles + typing indicator
  Right 40%: Quick Insights panel
"""
import threading
import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar


class _MessageBubble(ctk.CTkFrame):
    """A single chat message bubble."""
    def __init__(self, master, text: str, role: str, **kwargs):
        # role: "user" | "assistant"
        is_user = role == "user"
        bubble_color = THEME["green"] if is_user else THEME["bg_tertiary"]
        text_color   = ("#ffffff", "#ffffff") if is_user else THEME["text_primary"]
        align        = "e" if is_user else "w"

        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        bubble = ctk.CTkFrame(self, fg_color=bubble_color, corner_radius=14)
        bubble.grid(row=0, column=0, sticky=align, padx=(60, 8) if is_user else (8, 60), pady=4)

        ctk.CTkLabel(
            bubble, text=text,
            font=FONTS["body"],
            text_color=text_color,
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(padx=14, pady=10)


class _TypingIndicator(ctk.CTkFrame):
    """Animated '...' typing indicator."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._lbl = ctk.CTkLabel(self, text="● ● ●", font=FONTS["small"],
                                  text_color=THEME["text_tertiary"])
        self._lbl.pack(anchor="w", padx=8, pady=4)
        self._step = 0
        self._running = False

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return
        frames = ["●  ○  ○", "○  ●  ○", "○  ○  ●"]
        self._step = (self._step + 1) % len(frames)
        try:
            self._lbl.configure(text=frames[self._step])
            self.after(400, self._animate)
        except Exception:
            pass


class _InsightCard(ctk.CTkFrame):
    """A single insight card for the right panel."""
    def __init__(self, master, icon, title, description, color, **kwargs):
        super().__init__(master, fg_color=THEME["bg_secondary"], corner_radius=10,
                         border_width=1, border_color=THEME["border"], **kwargs)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 4))

        ctk.CTkLabel(top, text=icon, font=("Segoe UI Emoji", 20),
                     text_color=color).pack(side="left")
        ctk.CTkLabel(top, text=title, font=FONTS["subheading"],
                     text_color=THEME["text_primary"]).pack(side="left", padx=10)

        ctk.CTkLabel(self, text=description, font=FONTS["small"],
                     text_color=THEME["text_secondary"],
                     wraplength=280, justify="left", anchor="w").pack(
                         anchor="w", padx=14, pady=(0, 14))

        # Accent bar on left
        bar = ctk.CTkFrame(self, fg_color=color, width=4, corner_radius=0)
        bar.place(relx=0, rely=0, relheight=1)


class AIAssistantPage(ctk.CTkFrame):
    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id

        # Lazy-init the assistant so we don't block the UI thread
        self._assistant = None

        # ── Topbar ────────────────────────────────────────────────────────────
        self.topbar = Topbar(self, title="🤖 AI Financial Assistant")
        self.topbar.pack(fill="x")

        # ── Main split ───────────────────────────────────────────────────────
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        self._build_chat_panel(split)
        self._build_insights_panel(split)

        # Welcome message
        self._add_message(
            "👋 Hello! I'm your AI financial assistant. Ask me anything about "
            "your finances — top expenses, cash flow trends, spending analysis, "
            "or anything else. I have access to your live transaction data.",
            role="assistant"
        )

    # ─── Chat Panel ───────────────────────────────────────────────────────────

    def _build_chat_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"],
                             corner_radius=12, border_width=1, border_color=THEME["border"])
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(panel, fg_color="transparent", height=50)
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        ctk.CTkLabel(hdr, text="Chat", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        ctk.CTkLabel(hdr, text="Powered by Gemini 2.5 Flash", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="right")

        # Divider
        ctk.CTkFrame(panel, height=1, fg_color=THEME["border"]).grid(
            row=1, column=0, sticky="ew", padx=16)

        # Scrollable message area
        self._chat_scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self._chat_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        self._chat_scroll.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        # Typing indicator (hidden until needed)
        self._typing = _TypingIndicator(self._chat_scroll)

        # Input bar
        input_bar = ctk.CTkFrame(panel, fg_color=THEME["bg_tertiary"],
                                  corner_radius=10, height=60)
        input_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
        input_bar.grid_columnconfigure(0, weight=1)

        self._input = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask anything about your finances… (Ctrl+Enter to send)",
            font=FONTS["body"], fg_color="transparent",
            border_width=0, text_color=THEME["text_primary"],
        )
        self._input.grid(row=0, column=0, sticky="ew", padx=(12, 4), pady=10)
        self._input.bind("<Control-Return>", lambda e: self._on_send())

        send_btn = ctk.CTkButton(
            input_bar, text="Send ➤", width=90, height=36,
            font=FONTS["body"], fg_color=THEME["green"],
            hover_color=THEME["green_dark"],
            command=self._on_send,
        )
        send_btn.grid(row=0, column=1, padx=(4, 10), pady=10)

    def _add_message(self, text: str, role: str):
        bubble = _MessageBubble(self._chat_scroll, text=text, role=role)
        bubble.grid(sticky="ew", pady=2, padx=4)
        self._chat_scroll.grid_columnconfigure(0, weight=1)
        # Scroll to bottom
        self.after(50, self._chat_scroll._parent_canvas.yview_moveto, 1.0)

    def _show_typing(self):
        self._typing.grid(sticky="w", padx=8, pady=2)
        self._typing.start()
        self.after(50, self._chat_scroll._parent_canvas.yview_moveto, 1.0)

    def _hide_typing(self):
        try:
            if self._typing.winfo_exists():
                self._typing.stop()
                self._typing.grid_forget()
        except Exception:
            pass

    def _on_send(self):
        text = self._input.get().strip()
        if not text:
            return
        self._input.delete(0, "end")
        self._add_message(text, role="user")
        self._show_typing()
        self._input.configure(state="disabled")
        threading.Thread(target=self._do_send, args=(text,), daemon=True).start()

    def _do_send(self, text: str):
        if not self._assistant:
            from services.ai_service import AIAssistant
            self._assistant = AIAssistant(self.company_id)
        reply = self._assistant.send(text)
        self.after(0, self._on_reply, reply)

    def _on_reply(self, reply: str):
        if not self.winfo_exists():
            return
        self._hide_typing()
        if self._input.winfo_exists():
            self._input.configure(state="normal")
        self._add_message(reply, role="assistant")

    # ─── Insights Panel ───────────────────────────────────────────────────────

    def _build_insights_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"],
                             corner_radius=12, border_width=1, border_color=THEME["border"])
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        ctk.CTkLabel(hdr, text="Quick Insights", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")

        gen_btn = ctk.CTkButton(
            hdr, text="✨ Generate", width=100, height=30,
            font=FONTS["small"], fg_color=THEME["blue"],
            hover_color=THEME["bg_tertiary"],
            command=self._on_generate_insights,
        )
        gen_btn.pack(side="right")
        self._gen_btn = gen_btn

        ctk.CTkFrame(panel, height=1, fg_color=THEME["border"]).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(60, 0))

        # Scrollable insight list
        self._insight_scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self._insight_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._insight_scroll.grid_columnconfigure(0, weight=1)

        # Placeholder
        self._insight_placeholder = ctk.CTkLabel(
            self._insight_scroll,
            text="Click ✨ Generate to analyse\nyour financial data with AI.",
            font=FONTS["body"], text_color=THEME["text_tertiary"],
            justify="center"
        )
        self._insight_placeholder.pack(pady=60)

    def _on_generate_insights(self):
        self._gen_btn.configure(state="disabled", text="Analysing…")
        for w in self._insight_scroll.winfo_children():
            w.destroy()
        loading = ctk.CTkLabel(self._insight_scroll, text="⏳ Fetching insights…",
                               font=FONTS["body"], text_color=THEME["text_secondary"])
        loading.pack(pady=40)
        threading.Thread(target=self._do_generate_insights, daemon=True).start()

    def _do_generate_insights(self):
        if not self._assistant:
            from services.ai_service import AIAssistant
            self._assistant = AIAssistant(self.company_id)
        insights = self._assistant.generate_insights()
        self.after(0, self._render_insights, insights)

    def _render_insights(self, insights: list):
        if not self.winfo_exists():
            return
        for w in self._insight_scroll.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        for ins in insights:
            card = _InsightCard(
                self._insight_scroll,
                icon=ins["icon"],
                title=ins["title"],
                description=ins["description"],
                color=ins["color"],
            )
            card.pack(fill="x", padx=4, pady=6)
        self._gen_btn.configure(state="normal", text="✨ Refresh")
