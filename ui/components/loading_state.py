import customtkinter as ctk
from ui.theme import THEME, FONTS


class LoadingState(ctk.CTkFrame):
    """
    Premium animated loading state with a braille-character spinner
    and pulsing text. Replaces the static emoji placeholder.
    """
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, master, text="Loading data...", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._frame_index = 0
        self._running = True

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._spinner_lbl = ctk.CTkLabel(
            inner, text=self.SPINNER_FRAMES[0],
            font=("Inter", 36, "bold"),
            text_color=THEME["blue"])
        self._spinner_lbl.pack(pady=(0, 8))

        self._text_lbl = ctk.CTkLabel(
            inner, text=text,
            font=FONTS["body"],
            text_color=THEME["text_secondary"])
        self._text_lbl.pack()

        # Subtitle hint
        ctk.CTkLabel(
            inner, text="This won't take long",
            font=FONTS["small"],
            text_color=THEME["text_tertiary"]).pack(pady=(4, 0))

        self._animate()

    def _animate(self):
        if not self._running:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self._frame_index = (self._frame_index + 1) % len(self.SPINNER_FRAMES)
        self._spinner_lbl.configure(text=self.SPINNER_FRAMES[self._frame_index])
        self.after(80, self._animate)

    def destroy(self):
        self._running = False
        super().destroy()
