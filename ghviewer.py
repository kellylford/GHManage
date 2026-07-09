#!/usr/bin/env python3
"""ghviewer — a wxPython GUI for browsing and managing GitHub issues & PRs.

Requires the `gh` CLI (https://cli.github.com/) and wxPython.
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

import wx

from gh_data import (
    ALL_COLUMNS,
    DEFAULT_COLUMNS,
    GhError,
    Item,
    SORT_ORDERS,
    add_comment,
    close_item,
    detect_repo,
    fetch_issues,
    fetch_item_detail,
    fetch_prs,
    list_repos,
    open_in_browser,
    reopen_item,
    sort_items,
)


# ── IDs ─────────────────────────────────────────────────────────────────

ID_REFRESH = wx.NewIdRef()
ID_CLOSE_ITEM = wx.NewIdRef()
ID_REOPEN = wx.NewIdRef()
ID_COMMENT = wx.NewIdRef()
ID_OPEN_BROWSER = wx.NewIdRef()
ID_QUICK_MODE = wx.NewIdRef()
ID_FULL_MODE = wx.NewIdRef()
ID_STATE_OPEN = wx.NewIdRef()
ID_STATE_CLOSED = wx.NewIdRef()
ID_STATE_ALL = wx.NewIdRef()
ID_TAB_ISSUES = wx.NewIdRef()
ID_TAB_PRS = wx.NewIdRef()
ID_TAB_BOTH = wx.NewIdRef()
ID_COMMENT_DLG = wx.NewIdRef()


# ── Main frame ──────────────────────────────────────────────────────────


class GhViewerFrame(wx.Frame):
    """Main application window."""

    def __init__(self, repo: str | None = None) -> None:
        super().__init__(
            None,
            title="ghviewer — GitHub Issues & PRs",
            size=(1000, 700),
        )
        self.repo: str | None = None
        self.items: list[Item] = []
        self._all_repos: list[dict] = []

        # View settings
        self.columns: list[str] = list(DEFAULT_COLUMNS)
        self.sort_order: str = SORT_ORDERS[0]
        self.accessibility_mode: str = "quick"  # "quick" or "full"
        self.state_filter: str = "open"  # "open", "closed", "all"
        self.tab_filter: str = "both"  # "issues", "prs", "both"

        self._build_ui()
        self._bind_events()
        self._build_menu()
        self._update_menu_checks()

        if repo:
            self._select_repo(repo)
        else:
            self._load_repos()

        self.Show()

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Top panel: repo chooser
        top_panel = wx.Panel(self, name="repo_chooser_panel")
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(
            wx.StaticText(top_panel, label="Repository:"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT,
            border=5,
        )
        self.repo_combo = wx.ComboBox(
            top_panel,
            name="repo_combo",
            style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER | wx.WANTS_CHARS,
            size=(350, -1),
        )
        top_sizer.Add(self.repo_combo, flag=wx.ALIGN_CENTER_VERTICAL, border=5)
        self.load_btn = wx.Button(top_panel, label="Load", name="load_button")
        top_sizer.Add(self.load_btn, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=5)
        top_panel.SetSizer(top_sizer)

        # Splitter: list (top) + details (bottom)
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(120)

        # List panel
        list_panel = wx.Panel(self.splitter, name="list_panel")
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_ctrl = wx.ListCtrl(
            list_panel,
            name="item_list",
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        list_sizer.Add(self.list_ctrl, proportion=1, flag=wx.EXPAND)
        list_panel.SetSizer(list_sizer)

        # Details panel
        details_panel = wx.Panel(self.splitter, name="details_panel")
        details_sizer = wx.BoxSizer(wx.VERTICAL)
        self.details_text = wx.TextCtrl(
            details_panel,
            name="details_text",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH | wx.TE_WORDWRAP | wx.WANTS_CHARS,
        )
        self._comment_positions: list[tuple[int, int]] = []  # (line, length) per comment
        self._current_comment: int = -1
        details_sizer.Add(
            wx.StaticText(details_panel, label="Details"),
            flag=wx.LEFT | wx.TOP, border=3,
        )
        details_sizer.Add(self.details_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        details_panel.SetSizer(details_sizer)

        self.splitter.SplitHorizontally(list_panel, details_panel, 400)
        self.splitter.SetSashPosition(400)

        # Status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready")

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(top_panel, flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.splitter, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=5)
        self.SetSizer(sizer)

        # Initial columns
        self._rebuild_columns()

    def _rebuild_columns(self) -> None:
        """Rebuild the ListCtrl columns from self.columns."""
        self.list_ctrl.DeleteAllItems()
        self.list_ctrl.DeleteAllColumns()
        widths = {
            "number": 60, "type": 60, "state": 70, "title": 400,
            "author": 120, "created": 100, "updated": 100, "labels": 150,
            "assignees": 120, "comments": 70, "draft": 50, "review": 100,
            "+/-": 90, "files": 50, "base": 100, "head": 100,
        }
        for i, col in enumerate(self.columns):
            self.list_ctrl.InsertColumn(i, col, width=widths.get(col, 100))

    # ── Menu ────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu_bar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()
        file_menu.Append(ID_REFRESH, "Refresh\tCtrl+R")
        file_menu.AppendSeparator()
        file_menu.Append(ID_OPEN_BROWSER, "Open in Browser\tCtrl+O")
        file_menu.Append(ID_CLOSE_ITEM, "Close\tCtrl+W")
        file_menu.Append(ID_REOPEN, "Reopen\tCtrl+Shift+W")
        file_menu.Append(ID_COMMENT, "Add Comment…\tCtrl+M")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "Quit\tCtrl+Q")
        menu_bar.Append(file_menu, "File")

        # View menu
        view_menu = wx.Menu()

        # Accessibility mode submenu
        mode_menu = wx.Menu()
        mode_menu.AppendRadioItem(ID_QUICK_MODE, "Quick Mode (compact)")
        mode_menu.AppendRadioItem(ID_FULL_MODE, "Full Mode (field names for screen reader)")
        view_menu.AppendSubMenu(mode_menu, "Accessibility Mode")

        view_menu.AppendSeparator()

        # Sort order submenu
        sort_menu = wx.Menu()
        self._sort_menu_items = {}
        for i, order in enumerate(SORT_ORDERS):
            item_id = wx.NewIdRef()
            self._sort_menu_items[item_id] = order
            sort_menu.AppendRadioItem(item_id, order)
            self.Bind(wx.EVT_MENU, self.on_sort_selected, id=item_id)
        view_menu.AppendSubMenu(sort_menu, "Sort Order")

        view_menu.AppendSeparator()

        # Columns submenu
        col_menu = wx.Menu()
        self._col_menu_items = {}
        for col in ALL_COLUMNS:
            item_id = wx.NewIdRef()
            self._col_menu_items[item_id] = col
            mi = col_menu.AppendCheckItem(item_id, col)
            self.Bind(wx.EVT_MENU, self.on_column_toggled, id=item_id)
        view_menu.AppendSubMenu(col_menu, "Columns")

        view_menu.AppendSeparator()

        # State filter submenu
        state_menu = wx.Menu()
        state_menu.AppendRadioItem(ID_STATE_OPEN, "Open")
        state_menu.AppendRadioItem(ID_STATE_CLOSED, "Closed")
        state_menu.AppendRadioItem(ID_STATE_ALL, "All")
        view_menu.AppendSubMenu(state_menu, "State")

        # Tab filter submenu
        tab_menu = wx.Menu()
        tab_menu.AppendRadioItem(ID_TAB_ISSUES, "Issues Only")
        tab_menu.AppendRadioItem(ID_TAB_PRS, "PRs Only")
        tab_menu.AppendRadioItem(ID_TAB_BOTH, "Issues & PRs")
        view_menu.AppendSubMenu(tab_menu, "Show")

        menu_bar.Append(view_menu, "View")

        self.SetMenuBar(menu_bar)

        # Bind mode/state/tab menu items
        self.Bind(wx.EVT_MENU, self.on_quick_mode, id=ID_QUICK_MODE)
        self.Bind(wx.EVT_MENU, self.on_full_mode, id=ID_FULL_MODE)
        self.Bind(wx.EVT_MENU, self.on_state_open, id=ID_STATE_OPEN)
        self.Bind(wx.EVT_MENU, self.on_state_closed, id=ID_STATE_CLOSED)
        self.Bind(wx.EVT_MENU, self.on_state_all, id=ID_STATE_ALL)
        self.Bind(wx.EVT_MENU, self.on_tab_issues, id=ID_TAB_ISSUES)
        self.Bind(wx.EVT_MENU, self.on_tab_prs, id=ID_TAB_PRS)
        self.Bind(wx.EVT_MENU, self.on_tab_both, id=ID_TAB_BOTH)

    def _update_menu_checks(self) -> None:
        """Update checkmarks/radio selections to match current settings."""
        menu_bar = self.GetMenuBar()
        # Accessibility mode
        menu_bar.Check(ID_QUICK_MODE, self.accessibility_mode == "quick")
        menu_bar.Check(ID_FULL_MODE, self.accessibility_mode == "full")
        # State filter
        menu_bar.Check(ID_STATE_OPEN, self.state_filter == "open")
        menu_bar.Check(ID_STATE_CLOSED, self.state_filter == "closed")
        menu_bar.Check(ID_STATE_ALL, self.state_filter == "all")
        # Tab filter
        menu_bar.Check(ID_TAB_ISSUES, self.tab_filter == "issues")
        menu_bar.Check(ID_TAB_PRS, self.tab_filter == "prs")
        menu_bar.Check(ID_TAB_BOTH, self.tab_filter == "both")
        # Columns
        for item_id, col in self._col_menu_items.items():
            menu_bar.Check(item_id, col in self.columns)
        # Sort order
        for item_id, order in self._sort_menu_items.items():
            menu_bar.Check(item_id, order == self.sort_order)

    # ── Event binding ───────────────────────────────────────────────────

    def _bind_events(self) -> None:
        self.Bind(wx.EVT_BUTTON, self.on_load_clicked, self.load_btn)
        self.Bind(wx.EVT_COMBOBOX, self.on_repo_selected, self.repo_combo)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_repo_enter, self.repo_combo)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected, self.list_ctrl)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated, self.list_ctrl)
        self.Bind(wx.EVT_LIST_KEY_DOWN, self.on_list_key_down, self.list_ctrl)
        self.details_text.Bind(wx.EVT_CHAR_HOOK, self.on_details_key_down)
        self.Bind(wx.EVT_MENU, self.on_refresh, id=ID_REFRESH)
        self.Bind(wx.EVT_MENU, self.on_open_browser, id=ID_OPEN_BROWSER)
        self.Bind(wx.EVT_MENU, self.on_close_item, id=ID_CLOSE_ITEM)
        self.Bind(wx.EVT_MENU, self.on_reopen, id=ID_REOPEN)
        self.Bind(wx.EVT_MENU, self.on_comment, id=ID_COMMENT)
        self.Bind(wx.EVT_MENU, self.on_quit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_CLOSE, self.on_quit)

    # ── Repo loading ───────────────────────────────────────────────────

    def _load_repos(self) -> None:
        self.SetStatusText("Loading your repositories…")

        def worker() -> None:
            try:
                repos = list_repos(limit=100)
            except GhError as exc:
                wx.CallAfter(self._on_repos_error, str(exc))
                return
            wx.CallAfter(self._on_repos_loaded, repos)

        threading.Thread(target=worker, daemon=True).start()

    def _on_repos_loaded(self, repos: list[dict]) -> None:
        self._all_repos = repos
        self.repo_combo.Clear()
        for repo in repos:
            name = repo.get("nameWithOwner", "")
            desc = repo.get("description") or ""
            label = f"{name} — {desc}" if desc else name
            self.repo_combo.Append(label, clientData=name)
        if repos:
            self.SetStatusText(f"Loaded {len(repos)} repositories. Pick one or type owner/name.")
        else:
            self.SetStatusText("No repositories found. Type owner/name and press Enter.")

    def _on_repos_error(self, msg: str) -> None:
        self.SetStatusText(f"Error loading repos: {msg}")

    def on_repo_selected(self, event: wx.CommandEvent) -> None:
        idx = self.repo_combo.GetSelection()
        if idx != wx.NOT_FOUND:
            name = self.repo_combo.GetClientData(idx)
            if name:
                self._select_repo(name)

    def on_repo_enter(self, event: wx.CommandEvent) -> None:
        value = self.repo_combo.GetValue().strip()
        if value:
            self._select_repo(value)

    def on_load_clicked(self, event: wx.CommandEvent) -> None:
        value = self.repo_combo.GetValue().strip()
        if value:
            self._select_repo(value)

    def _select_repo(self, repo: str) -> None:
        if " — " in repo:
            repo = repo.split(" — ")[0].strip()
        self.repo = repo
        self.repo_combo.SetValue(repo)
        self._load_items()

    # ── Item loading ───────────────────────────────────────────────────

    def _load_items(self) -> None:
        self.SetStatusText(f"Loading {self.repo}…")
        self.list_ctrl.DeleteAllItems()
        self.details_text.Clear()

        def worker() -> None:
            try:
                issues = []
                prs = []
                if self.tab_filter in ("issues", "both"):
                    issues = fetch_issues(self.repo, self.state_filter)
                if self.tab_filter in ("prs", "both"):
                    prs = fetch_prs(self.repo, self.state_filter)
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))
                return
            combined = sort_items(issues + prs, self.sort_order)
            wx.CallAfter(self._on_items_loaded, combined, len(issues), len(prs))

        threading.Thread(target=worker, daemon=True).start()

    def _item_label(self, item: Item, col: str) -> str:
        """Get the display value for a single column, with mode-aware formatting."""
        val = item.to_row(self.columns).get(col, "")
        if self.accessibility_mode == "full":
            return f"{col}: {val}" if val else ""
        return val

    def _on_items_loaded(self, items: list[Item], n_issues: int, n_prs: int) -> None:
        self.items = items
        self.list_ctrl.DeleteAllItems()
        for i, item in enumerate(items):
            for j, col in enumerate(self.columns):
                label = self._item_label(item, col)
                if j == 0:
                    self.list_ctrl.InsertItem(i, label)
                else:
                    self.list_ctrl.SetItem(i, j, label)
        self.SetStatusText(
            f"{self.repo} — {n_issues} issues, {n_prs} PRs ({self.state_filter}). "
            f"Enter=open  C=close  O=reopen  R=refresh  M=comment  "
            f"Mode={self.accessibility_mode}"
        )
        if items:
            # Delay the focus move so it happens after the combo box
            # Enter event has fully completed processing.
            wx.CallLater(100, self._focus_list)

    def _focus_list(self) -> None:
        """Move keyboard focus to the list and select the first item."""
        self.list_ctrl.SetFocus()
        self.list_ctrl.Select(0, on=True)
        self.list_ctrl.Focus(0)
        self._show_details(0)

    def _on_items_error(self, msg: str) -> None:
        self.SetStatusText(f"Error: {msg}")

    # ── Details panel ──────────────────────────────────────────────────

    def _show_details(self, idx: int) -> None:
        """Show details for the item at idx in the details panel."""
        self._comment_positions = []
        self._current_comment = -1
        if idx < 0 or idx >= len(self.items):
            self.details_text.Clear()
            return
        item = self.items[idx]
        lines = []
        lines.append(f"#{item.number} [{item.kind}] {item.title}")
        lines.append(f"State: {item.state_display}")
        lines.append(f"Author: {item.author}")
        lines.append(f"Created: {item.created_at}")
        lines.append(f"Updated: {item.updated_at}")
        lines.append(f"URL: {item.url}")
        if item.labels:
            lines.append(f"Labels: {', '.join(item.labels)}")
        if item.assignees:
            lines.append(f"Assignees: {', '.join(item.assignees)}")
        lines.append(f"Comments: {item.comments}")
        if item.is_pr:
            lines.append(f"Draft: {'Yes' if item.is_draft else 'No'}")
            lines.append(f"Merged: {'Yes' if item.is_merged else 'No'}")
            if item.review_status:
                lines.append(f"Review: {item.review_status}")
            lines.append(f"Branches: {item.head_branch} → {item.base_branch}")
            lines.append(f"Changes: +{item.additions} -{item.deletions} ({item.changed_files} files)")
        lines.append("")
        lines.append("─" * 60)
        lines.append("")
        body = item.body or "(no description)"
        lines.append(body)
        # Show actual comments if we have them, tracking line positions
        if item.comment_list:
            lines.append("")
            lines.append("─" * 60)
            lines.append(f"Comments ({len(item.comment_list)}):")
            lines.append("─" * 60)
            for i, c in enumerate(item.comment_list):
                lines.append("")
                start_line = len(lines)
                header = f"  Comment {i + 1} of {len(item.comment_list)} — {c['author']} ({c['created_at'][:10] if c['created_at'] else ''}):"
                lines.append(header)
                comment_lines = []
                for body_line in c["body"].splitlines():
                    comment_lines.append(f"    {body_line}")
                lines.extend(comment_lines)
                # Track this comment's position: (line index, number of lines)
                self._comment_positions.append((start_line, len(comment_lines) + 1))
        self.details_text.SetValue("\n".join(lines))

    # ── Helpers ─────────────────────────────────────────────────────────

    def _focused_item(self) -> Item | None:
        idx = self.list_ctrl.GetFirstSelected()
        if idx < 0 or idx >= len(self.items):
            return None
        return self.items[idx]

    def _announce(self, msg: str) -> None:
        """Update status bar (screen reader accessible)."""
        self.SetStatusText(msg)

    # ── List events ─────────────────────────────────────────────────────

    def on_item_selected(self, event: wx.ListEvent) -> None:
        idx = event.GetIndex()
        self._show_details(idx)
        if self.accessibility_mode == "full":
            item = self.items[idx] if idx < len(self.items) else None
            if item:
                self._announce(item.to_accessible_string(self.columns))

    def on_item_activated(self, event: wx.ListEvent) -> None:
        """Double-click or Enter — open in browser."""
        item = self._focused_item()
        if item:
            open_in_browser(item)
            self._announce(f"Opened #{item.number} in browser")

    def on_list_key_down(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == ord("C"):
            self._do_close()
        elif key == ord("O"):
            self._do_reopen()
        elif key == ord("R"):
            self._load_items()
        elif key == ord("M"):
            self._do_comment()
        else:
            event.Skip()

    def on_details_key_down(self, event: wx.KeyEvent) -> None:
        """Handle n/p for next/previous comment when focus is in the details box."""
        key = event.GetKeyCode()
        if key == ord("N"):
            self._navigate_comment(1)
            return  # swallow the key
        elif key == ord("P"):
            self._navigate_comment(-1)
            return
        event.Skip()

    def _navigate_comment(self, direction: int) -> None:
        """Move to the next (1) or previous (-1) comment in the details box."""
        if not self._comment_positions:
            self._announce("No comments to navigate.")
            return
        new_idx = self._current_comment + direction
        if new_idx < 0:
            self._announce("Already at first comment.")
            return
        if new_idx >= len(self._comment_positions):
            self._announce("Already at last comment.")
            return
        self._current_comment = new_idx
        line, length = self._comment_positions[new_idx]
        start_pos = self._line_to_position(line)
        end_pos = self._line_to_position(line + length)
        self.details_text.SetFocus()
        self.details_text.SetSelection(start_pos, end_pos)
        self.details_text.ShowPosition(start_pos)
        total = len(self._comment_positions)
        self._announce(f"Comment {new_idx + 1} of {total}")

    def _line_to_position(self, line: int) -> int:
        """Convert a 0-based line index to a character position in the TextCtrl."""
        text = self.details_text.GetValue()
        pos = 0
        current_line = 0
        for ch in text:
            if current_line >= line:
                break
            if ch == '\n':
                current_line += 1
            pos += 1
        return pos

    # ── Menu actions ────────────────────────────────────────────────────

    def on_refresh(self, event: wx.CommandEvent) -> None:
        if self.repo:
            self._load_items()

    def on_open_browser(self, event: wx.CommandEvent) -> None:
        item = self._focused_item()
        if item:
            open_in_browser(item)
            self._announce(f"Opened #{item.number} in browser")

    def on_close_item(self, event: wx.CommandEvent) -> None:
        self._do_close()

    def on_reopen(self, event: wx.CommandEvent) -> None:
        self._do_reopen()

    def on_comment(self, event: wx.CommandEvent) -> None:
        self._do_comment()

    def on_quit(self, event: wx.CommandEvent) -> None:
        self.Destroy()

    # ── View menu actions ───────────────────────────────────────────────

    def on_quick_mode(self, event: wx.CommandEvent) -> None:
        self.accessibility_mode = "quick"
        self._update_menu_checks()
        self._announce("Quick mode: compact display")
        if self.items:
            self._refresh_list_display()

    def on_full_mode(self, event: wx.CommandEvent) -> None:
        self.accessibility_mode = "full"
        self._update_menu_checks()
        self._announce("Full mode: field names included for screen reader")
        if self.items:
            self._refresh_list_display()

    def on_sort_selected(self, event: wx.CommandEvent) -> None:
        self.sort_order = self._sort_menu_items.get(event.GetId(), SORT_ORDERS[0])
        self._update_menu_checks()
        if self.items:
            self.items = sort_items(self.items, self.sort_order)
            self._refresh_list_display()

    def on_column_toggled(self, event: wx.CommandEvent) -> None:
        col = self._col_menu_items.get(event.GetId())
        if not col:
            return
        if col in self.columns:
            self.columns.remove(col)
        else:
            self.columns.append(col)
        self._update_menu_checks()
        self._rebuild_columns()
        self._refresh_list_display()

    def on_state_open(self, event: wx.CommandEvent) -> None:
        self.state_filter = "open"
        self._update_menu_checks()
        if self.repo:
            self._load_items()

    def on_state_closed(self, event: wx.CommandEvent) -> None:
        self.state_filter = "closed"
        self._update_menu_checks()
        if self.repo:
            self._load_items()

    def on_state_all(self, event: wx.CommandEvent) -> None:
        self.state_filter = "all"
        self._update_menu_checks()
        if self.repo:
            self._load_items()

    def on_tab_issues(self, event: wx.CommandEvent) -> None:
        self.tab_filter = "issues"
        self._update_menu_checks()
        if self.repo:
            self._load_items()

    def on_tab_prs(self, event: wx.CommandEvent) -> None:
        self.tab_filter = "prs"
        self._update_menu_checks()
        if self.repo:
            self._load_items()

    def on_tab_both(self, event: wx.CommandEvent) -> None:
        self.tab_filter = "both"
        self._update_menu_checks()
        if self.repo:
            self._load_items()

    # ── List display refresh ───────────────────────────────────────────

    def _refresh_list_display(self) -> None:
        """Re-populate the list from self.items without re-fetching."""
        self.list_ctrl.DeleteAllItems()
        for i, item in enumerate(self.items):
            for j, col in enumerate(self.columns):
                label = self._item_label(item, col)
                if j == 0:
                    self.list_ctrl.InsertItem(i, label)
                else:
                    self.list_ctrl.SetItem(i, j, label)
        if self.items:
            wx.CallLater(100, self._focus_list)

    # ── Actions ─────────────────────────────────────────────────────────

    def _do_close(self) -> None:
        item = self._focused_item()
        if not item:
            return
        kind = "PR" if item.is_pr else "issue"
        confirm = wx.MessageBox(
            f"Close {kind} #{item.number}?\n\n{item.title}",
            "Confirm Close",
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if confirm != wx.YES:
            return
        self._announce(f"Closing #{item.number}…")

        def worker() -> None:
            try:
                close_item(item, self.repo)
                wx.CallAfter(self._on_action_done, f"Closed #{item.number}")
            except GhError as exc:
                wx.CallAfter(self._on_action_error, f"Error closing #{item.number}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _do_reopen(self) -> None:
        item = self._focused_item()
        if not item:
            return
        kind = "PR" if item.is_pr else "issue"
        confirm = wx.MessageBox(
            f"Reopen {kind} #{item.number}?\n\n{item.title}",
            "Confirm Reopen",
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if confirm != wx.YES:
            return
        self._announce(f"Reopening #{item.number}…")

        def worker() -> None:
            try:
                reopen_item(item, self.repo)
                wx.CallAfter(self._on_action_done, f"Reopened #{item.number}")
            except GhError as exc:
                wx.CallAfter(self._on_action_error, f"Error reopening #{item.number}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _do_comment(self) -> None:
        item = self._focused_item()
        if not item:
            return
        dlg = wx.TextEntryDialog(
            self,
            f"Add a comment to #{item.number}:\n{item.title}",
            "Add Comment",
            "",
            style=wx.TE_MULTILINE | wx.OK | wx.CANCEL,
        )
        if dlg.ShowModal() == wx.ID_OK:
            comment = dlg.GetValue().strip()
            if not comment:
                return
            self._announce(f"Adding comment to #{item.number}…")

            def worker() -> None:
                try:
                    add_comment(item, comment, self.repo)
                    wx.CallAfter(self._on_action_done, f"Comment added to #{item.number}")
                except GhError as exc:
                    wx.CallAfter(self._on_action_error, f"Error commenting #{item.number}: {exc}")

            threading.Thread(target=worker, daemon=True).start()
        dlg.Destroy()

    def _on_action_done(self, msg: str) -> None:
        self._announce(f"{msg}. Refreshing…")
        self._load_items()

    def _on_action_error(self, msg: str) -> None:
        self._announce(msg)


# ── Entry point ────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GUI viewer and manager for GitHub issues and pull requests."
    )
    parser.add_argument(
        "--repo",
        metavar="OWNER/NAME",
        default=None,
        help="GitHub repository (owner/name). Skips the repo chooser.",
    )
    args = parser.parse_args()
    app = wx.App(False)
    GhViewerFrame(repo=args.repo)
    app.MainLoop()


if __name__ == "__main__":
    main()