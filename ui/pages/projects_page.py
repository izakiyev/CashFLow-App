import customtkinter as ctk
from datetime import datetime
from ui.theme import THEME, FONTS
from services.project_service import get_projects, get_project_summary, delete_project
from services.currency_service import format_currency
from ui.components.topbar import Topbar
from ui.components.empty_state import EmptyState
from ui.components.toast import Toast
from ui.utils.thread_worker import ThreadWorker
from ui.modals.add_project import AddProjectModal
from ui.modals.edit_project import EditProjectModal
from ui.modals.confirm_dialog import ConfirmDialog


# ─── Project Card ─────────────────────────────────────────────────────────────

class ProjectCard(ctk.CTkFrame):
    """Premium hoverable project card with progress visualization."""

    def __init__(self, master, p: dict, on_edit, on_delete, on_view, **kwargs):
        super().__init__(
            master, fg_color=THEME["bg_secondary"], corner_radius=14,
            border_width=1, border_color=THEME["border"], **kwargs
        )
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_view = on_view
        self.p = p

        # Left colored accent bar using project color
        color = p.get("color") or "#2970ff"
        accent = ctk.CTkFrame(self, width=5, fg_color=color, corner_radius=3)
        accent.pack(side="left", fill="y", padx=(0, 0), pady=0)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=16, pady=14)

        # ── Top row: name + status badge + actions ──
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")

        name_lbl = ctk.CTkLabel(
            top, text=p["name"], font=FONTS["heading"],
            text_color=THEME["text_primary"], anchor="w"
        )
        name_lbl.pack(side="left")

        # Status badge
        status = p.get("status", "active")
        s_cfg = {
            "active":    (THEME["green"],  THEME["green_light"]),
            "completed": (THEME["blue"],   THEME["blue_light"]),
            "archived":  (THEME["text_secondary"], THEME["border"]),
        }.get(status, (THEME["text_secondary"], THEME["border"]))
        status_lbl = ctk.CTkLabel(
            top, text=f" {status.upper()} ",
            font=("Inter", 9, "bold"),
            text_color=s_cfg[0], fg_color=s_cfg[1],
            corner_radius=5, padx=4, pady=2
        )
        status_lbl.pack(side="left", padx=12)

        # Action buttons (right-aligned)
        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(side="right")

        view_btn = ctk.CTkButton(
            actions, text="View →", width=68, height=26,
            font=("Inter", 11, "bold"),
            fg_color=THEME["blue"], hover_color=THEME["blue_light"],
            text_color="white",
            command=lambda: self.on_view(p)
        )
        view_btn.pack(side="left", padx=(0, 6))

        edit_btn = ctk.CTkButton(
            actions, text="✏", width=32, height=26,
            font=FONTS["small"],
            fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
            text_color=THEME["text_secondary"],
            command=lambda: self.on_edit(p)
        )
        edit_btn.pack(side="left", padx=2)

        del_btn = ctk.CTkButton(
            actions, text="🗑", width=32, height=26,
            font=FONTS["small"],
            fg_color=THEME["bg_tertiary"], hover_color=THEME["red_light"],
            text_color=THEME["red"],
            command=lambda: self.on_delete(p)
        )
        del_btn.pack(side="left")

        # ── Description ──
        if p.get("description"):
            ctk.CTkLabel(
                body, text=p["description"], font=FONTS["small"],
                text_color=THEME["text_tertiary"], anchor="w",
                wraplength=600, justify="left"
            ).pack(fill="x", pady=(2, 0))

        # ── Separator ──
        ctk.CTkFrame(body, height=1, fg_color=THEME["border"]).pack(fill="x", pady=10)

        # ── Metrics row ──
        summary = p.get("_summary", {})
        bc = summary.get("base_currency", "AZN")
        metrics = ctk.CTkFrame(body, fg_color="transparent")
        metrics.pack(fill="x")

        # Dates
        dates_col = ctk.CTkFrame(metrics, fg_color="transparent")
        dates_col.pack(side="left", padx=(0, 24))

        sd = p["start_date"].strftime("%b %d, %Y") if p.get("start_date") else "—"
        ed = p["end_date"].strftime("%b %d, %Y") if p.get("end_date") else "—"

        ctk.CTkLabel(dates_col, text="START", font=("Inter", 9, "bold"),
                     text_color=THEME["text_tertiary"]).pack(anchor="w")
        ctk.CTkLabel(dates_col, text=sd, font=FONTS["small"],
                     text_color=THEME["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(dates_col, text="END", font=("Inter", 9, "bold"),
                     text_color=THEME["text_tertiary"]).pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(dates_col, text=ed, font=FONTS["small"],
                     text_color=THEME["text_primary"]).pack(anchor="w")

        # Divider
        ctk.CTkFrame(metrics, width=1, fg_color=THEME["border"]).pack(side="left", fill="y", padx=16)

        # Financials
        fin_col = ctk.CTkFrame(metrics, fg_color="transparent")
        fin_col.pack(side="left", fill="x", expand=True)

        spent = summary.get("spent", 0)
        income = summary.get("income", 0)
        budget = summary.get("budgeted")
        tx_count = summary.get("tx_count", 0)
        pending = summary.get("planned_pending", 0)

        # Stat pills row
        stats = ctk.CTkFrame(fin_col, fg_color="transparent")
        stats.pack(fill="x")

        def _stat(parent, title, val, color):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(side="left", padx=(0, 24))
            ctk.CTkLabel(f, text=title, font=("Inter", 9, "bold"),
                         text_color=THEME["text_tertiary"]).pack(anchor="w")
            ctk.CTkLabel(f, text=val, font=("Inter", 14, "bold"),
                         text_color=color).pack(anchor="w")

        _stat(stats, "INCOME", format_currency(income, bc), THEME["green"])
        _stat(stats, "SPENT", format_currency(spent, bc), THEME["red"])
        _stat(stats, "TRANSACTIONS", str(tx_count), THEME["text_primary"])
        if pending > 0:
            _stat(stats, "PENDING PLANNED", format_currency(pending, bc), THEME["amber"])

        # Budget progress bar (if budget set)
        if budget is not None:
            pct = spent / budget if budget > 0 else 0
            is_over = summary.get("is_over_budget", False)
            bar_color = THEME["red"] if is_over else (THEME["amber"] if pct > 0.75 else THEME["green"])

            prog_row = ctk.CTkFrame(fin_col, fg_color="transparent")
            prog_row.pack(fill="x", pady=(8, 0))

            budget_lbl = ctk.CTkLabel(
                prog_row,
                text=f"Budget: {format_currency(budget, bc)}",
                font=FONTS["small"], text_color=THEME["text_secondary"]
            )
            budget_lbl.pack(side="left")

            if is_over:
                rem_txt = f"⚠ Over by {format_currency(abs(summary.get('remaining', 0)), bc)}"
                rem_color = THEME["red"]
            else:
                rem = summary.get("remaining", 0)
                rem_txt = f"{format_currency(rem, bc)} left ({int(pct * 100)}%)"
                rem_color = THEME["text_secondary"]

            ctk.CTkLabel(prog_row, text=rem_txt, font=FONTS["small"],
                         text_color=rem_color).pack(side="right")

            bar = ctk.CTkProgressBar(
                fin_col, height=8, corner_radius=4,
                fg_color=THEME["bg_tertiary"], progress_color=bar_color
            )
            bar.pack(fill="x", pady=(4, 0))
            bar.set(min(1.0, pct))
        else:
            ctk.CTkLabel(
                fin_col, text="No budget cap  •  Open-ended project",
                font=FONTS["small"], text_color=THEME["text_tertiary"]
            ).pack(anchor="w", pady=(6, 0))

        # Timeline progress bar (if dates set)
        if p.get("start_date") and p.get("end_date"):
            now = datetime.now()
            start = p["start_date"]
            end = p["end_date"]
            total_days = max(1, (end - start).days)
            elapsed_days = max(0, (now - start).days)
            time_pct = min(1.0, elapsed_days / total_days)

            days_left = max(0, (end - now).days)
            is_late = now > end and status == "active"

            time_row = ctk.CTkFrame(fin_col, fg_color="transparent")
            time_row.pack(fill="x", pady=(6, 0))

            ctk.CTkLabel(time_row, text="Timeline", font=FONTS["small"],
                         text_color=THEME["text_tertiary"]).pack(side="left")

            if is_late:
                time_txt = f"⚠ {abs(days_left)} days overdue"
                time_color = THEME["red"]
            elif days_left == 0:
                time_txt = "Due today"
                time_color = THEME["amber"]
            else:
                time_txt = f"{days_left} days left"
                time_color = THEME["text_secondary"]

            ctk.CTkLabel(time_row, text=time_txt, font=FONTS["small"],
                         text_color=time_color).pack(side="right")

            time_bar_color = THEME["red"] if is_late else (THEME["amber"] if time_pct > 0.85 else THEME["blue"])
            t_bar = ctk.CTkProgressBar(
                fin_col, height=5, corner_radius=3,
                fg_color=THEME["bg_tertiary"], progress_color=time_bar_color
            )
            t_bar.pack(fill="x", pady=(3, 0))
            t_bar.set(time_pct)

        # Hover effect
        self.bind("<Enter>", lambda e: self.configure(border_color=color))
        self.bind("<Leave>", lambda e: self.configure(border_color=THEME["border"]))


# ─── Project Detail Panel ──────────────────────────────────────────────────────

class ProjectDetailPanel(ctk.CTkFrame):
    """An inline detail panel showing all transactions for a project."""

    def __init__(self, master, project, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.project = project
        self.on_back = on_back
        self._build()

    def _build(self):
        # Back button row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkButton(
            top, text="← Back to Projects", width=160, height=30,
            font=FONTS["small"],
            fg_color="transparent", border_width=1, border_color=THEME["border"],
            text_color=THEME["text_secondary"], hover_color=THEME["bg_tertiary"],
            command=self.on_back
        ).pack(side="left")

        p = self.project
        color = p.get("color") or "#2970ff"
        ctk.CTkLabel(
            top,
            text=f"● {p['name']}",
            font=FONTS["heading"],
            text_color=color
        ).pack(side="left", padx=20)

        # Separator
        ctk.CTkFrame(self, height=1, fg_color=THEME["border"]).pack(fill="x", padx=20, pady=8)

        # Summary KPIs
        summary = p.get("_summary", {})
        bc = summary.get("base_currency", "AZN")

        kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        kpi_row.pack(fill="x", padx=20, pady=(0, 12))

        for title, val, color in [
            ("TOTAL INCOME",   format_currency(summary.get("income", 0),   bc), THEME["green"]),
            ("TOTAL EXPENSES", format_currency(summary.get("spent", 0),    bc), THEME["red"]),
            ("NET",            format_currency(summary.get("net", 0),      bc), THEME["blue"]),
            ("TRANSACTIONS",   str(summary.get("tx_count", 0)),                 THEME["text_primary"]),
        ]:
            card = ctk.CTkFrame(kpi_row, fg_color=THEME["bg_secondary"],
                                corner_radius=10, border_width=1, border_color=THEME["border"])
            card.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(card, text=title, font=("Inter", 9, "bold"),
                         text_color=THEME["text_tertiary"]).pack(anchor="w", padx=12, pady=(10, 0))
            ctk.CTkLabel(card, text=val, font=("Inter", 18, "bold"),
                         text_color=color).pack(anchor="w", padx=12, pady=(2, 10))

        # Transactions list
        ctk.CTkLabel(
            self, text="Project Transactions", font=FONTS["heading"],
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=20, pady=(0, 6))

        scroll = ctk.CTkScrollableFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Load transactions
        from services.transaction_service import get_transactions
        txs = get_transactions(p["company_id"], {"project_id": p["id"]})

        if not txs:
            ctk.CTkLabel(
                scroll, text="No transactions linked to this project yet.",
                font=FONTS["body"], text_color=THEME["text_tertiary"]
            ).pack(pady=30)
            return

        # Table header
        hdr = ctk.CTkFrame(scroll, fg_color=THEME["bg_tertiary"], corner_radius=6)
        hdr.pack(fill="x", padx=4, pady=(4, 4))
        for col_text, w in [("Date", 120), ("Description", 300), ("Category", 160), ("Type", 90), ("Amount", 130)]:
            ctk.CTkLabel(hdr, text=col_text, font=("Inter", 10, "bold"),
                         text_color=THEME["text_tertiary"], width=w, anchor="w").pack(side="left", padx=6, pady=6)

        for tx in txs:
            row = ctk.CTkFrame(scroll, fg_color="transparent",
                               border_width=1, border_color=THEME["border"], corner_radius=6)
            row.pack(fill="x", padx=4, pady=2)

            type_color = THEME["green"] if tx["type"] == "income" else (
                THEME["blue"] if tx["type"] == "transfer" else THEME["red"]
            )
            sign = "+" if tx["type"] == "income" else ("-" if tx["type"] == "expense" else "")

            date_str = tx["date"].strftime("%d %b %Y") if tx.get("date") else "—"
            for val, w in [
                (date_str,                                          120),
                (tx.get("description") or "—",                    300),
                (tx.get("category_name") or "Uncategorized",       160),
                (tx.get("type", "").capitalize(),                   90),
                (f"{sign}{format_currency(tx['amount'], tx.get('currency','AZN'))}", 130),
            ]:
                ctk.CTkLabel(
                    row, text=val, font=FONTS["small"],
                    text_color=type_color if val.startswith(("+", "-")) else THEME["text_primary"],
                    width=w, anchor="w"
                ).pack(side="left", padx=6, pady=6)


# ─── Main Projects Page ────────────────────────────────────────────────────────

class ProjectsPage(ctk.CTkFrame):

    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.status_filter = "active"
        self._detail_panel = None

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── Topbar ──
        self.topbar = Topbar(self, title="Projects")
        self.topbar.pack(fill="x")
        self.topbar.add_action("+ New Project", self._open_add, primary=True)

        # ── Summary KPIs ──
        self._kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._kpi_frame.pack(fill="x", padx=20, pady=(14, 0))
        self._kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def _kpi(col, title, icon, color, light):
            card = ctk.CTkFrame(self._kpi_frame, fg_color=THEME["bg_secondary"],
                                corner_radius=12, border_width=1, border_color=THEME["border"], height=90)
            card.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
            card.pack_propagate(False)

            icon_bg = ctk.CTkFrame(card, width=42, height=42, corner_radius=10, fg_color=light)
            icon_bg.pack(side="left", padx=(14, 10), pady=24)
            icon_bg.pack_propagate(False)
            ctk.CTkLabel(icon_bg, text=icon, font=("Inter", 18)).place(relx=0.5, rely=0.5, anchor="center")

            tf = ctk.CTkFrame(card, fg_color="transparent")
            tf.pack(side="left", fill="both", expand=True, pady=(16, 0))
            ctk.CTkLabel(tf, text=title, font=("Inter", 10, "bold"),
                         text_color=THEME["text_tertiary"]).pack(anchor="w")
            lbl = ctk.CTkLabel(tf, text="0", font=("Inter", 22, "bold"), text_color=color)
            lbl.pack(anchor="w")
            return lbl

        self.kpi_total  = _kpi(0, "TOTAL",        "📁", THEME["text_primary"], THEME["bg_tertiary"])
        self.kpi_active = _kpi(1, "ACTIVE",        "🚀", THEME["blue"],         THEME["blue_light"])
        self.kpi_over   = _kpi(2, "OVER BUDGET",   "⚠",  THEME["red"],          THEME["red_light"])
        self.kpi_done   = _kpi(3, "COMPLETED",     "✅", THEME["green"],        THEME["green_light"])

        # ── Filter + Search bar ──
        ctrl = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"],
                            corner_radius=10, border_width=1, border_color=THEME["border"])
        ctrl.pack(fill="x", padx=20, pady=12)

        inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(inner, text="Status:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 6))
        self.status_seg = ctk.CTkSegmentedButton(
            inner, values=["All", "Active", "Completed", "Archived"],
            font=FONTS["small"], height=30, command=self._on_filter
        )
        self.status_seg.set("Active")
        self.status_seg.pack(side="left")

        self._result_lbl = ctk.CTkLabel(inner, text="", font=FONTS["small"],
                                        text_color=THEME["text_tertiary"])
        self._result_lbl.pack(side="right", padx=8)

        # ── Main content area (list or detail) ──
        self._content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def refresh(self):
        if not self.company_id:
            return
        self._show_list()
        ThreadWorker(self, self._fetch_data, on_success=self._render)

    def _on_filter(self, val):
        self.status_filter = val.lower()
        ThreadWorker(self, self._fetch_data, on_success=self._render)

    def _fetch_data(self):
        projs = get_projects(self.company_id, self.status_filter)
        all_projs = get_projects(self.company_id, "all")

        over_budget = 0
        active = 0
        done = 0

        for p in all_projs:
            s = p["status"]
            if s == "active":   active += 1
            if s == "completed": done += 1
            summ = get_project_summary(p["id"])
            if summ.get("is_over_budget"):
                over_budget += 1

        for p in projs:
            p["_summary"] = get_project_summary(p["id"])

        return {
            "projects": projs,
            "kpi": {"total": len(all_projs), "active": active, "over": over_budget, "done": done}
        }

    def _render(self, data):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        kpi = data["kpi"]
        self.kpi_total.configure(text=str(kpi["total"]))
        self.kpi_active.configure(text=str(kpi["active"]))
        self.kpi_over.configure(text=str(kpi["over"]),
                                text_color=THEME["red"] if kpi["over"] > 0 else THEME["text_primary"])
        self.kpi_done.configure(text=str(kpi["done"]))

        projs = data["projects"]
        self._result_lbl.configure(text=f"{len(projs)} project(s)")

        self._show_list()
        for w in self._content.winfo_children():
            w.destroy()

        if not projs:
            EmptyState(
                self._content, icon="📁",
                title="No Projects Found",
                subtitle="Click '+ New Project' to create your first project and start tracking budgets."
            ).pack(fill="both", expand=True, pady=60)
            return

        for p in projs:
            card = ProjectCard(
                self._content, p,
                on_edit=self._open_edit,
                on_delete=self._open_delete,
                on_view=self._view_project
            )
            card.pack(fill="x", pady=6)

    def _show_list(self):
        """Destroy detail panel if shown and return to list mode."""
        if self._detail_panel and self._detail_panel.winfo_exists():
            self._detail_panel.destroy()
            self._detail_panel = None
        self._content.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def _view_project(self, p):
        """Replace list with a detail panel for a specific project."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self._content.pack_forget()

        self._detail_panel = ProjectDetailPanel(
            self, p, on_back=self._show_list
        )
        self._detail_panel.pack(fill="both", expand=True)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _open_add(self):
        AddProjectModal(self.winfo_toplevel(), self.company_id, self.refresh)

    def _open_edit(self, p):
        EditProjectModal(self.winfo_toplevel(), p, self.refresh)

    def _open_delete(self, p):
        def do_delete():
            if delete_project(p["id"]):
                Toast(self.winfo_toplevel(), f"'{p['name']}' deleted", type="success")
                self.refresh()
        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Project",
            message=f"Are you sure you want to delete '{p['name']}'?\nAll linked transactions will be kept but untagged.",
            on_confirm=do_delete
        )
