#!/usr/bin/env python3
"""ghviewer — a wxPython GUI for browsing and managing GitHub issues & PRs.

Requires the `gh` CLI (https://cli.github.com/) and wxPython.
"""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from typing import Optional

import wx

import updater
from version import __version__ as APP_VERSION
from pinned_repos import add_pinned, load_pinned, remove_pinned
from favorites import FavoriteEntry, load_favorites, save_favorites, is_favorite, toggle_favorite

from gh_data import (
    ALL_COLUMNS,
    BRANCH_COLUMNS,
    BRANCH_DEFAULT_COLUMNS,
    COMMIT_COLUMNS,
    COMMIT_DEFAULT_COLUMNS,
    DEFAULT_COLUMNS,
    GhError,
    Item,
    LABEL_COLUMNS,
    LABEL_DEFAULT_COLUMNS,
    RELEASE_COLUMNS,
    RELEASE_DEFAULT_COLUMNS,
    SORT_ORDERS,
    TAG_COLUMNS,
    TAG_DEFAULT_COLUMNS,
    WORKFLOW_COLUMNS,
    WORKFLOW_DEFAULT_COLUMNS,
    WORKFLOW_DEF_COLUMNS,
    WORKFLOW_DEF_DEFAULT_COLUMNS,
    ARTIFACT_COLUMNS,
    ARTIFACT_DEFAULT_COLUMNS,
    ASSET_COLUMNS,
    ASSET_DEFAULT_COLUMNS,
    Artifact,
    Branch,
    Commit,
    Label,
    Release,
    ReleaseAsset,
    Tag,
    Workflow,
    WorkflowRun,
    CompareResult,
    DispatchSpec,
    WorkflowInput,
    add_comment,
    close_item,
    create_label,
    detect_repo,
    delete_label,
    delete_workflow_run,
    dispatch_workflow,
    download_artifact,
    fetch_branches,
    fetch_dispatch_spec,
    fetch_run_artifacts,
    fetch_compare,
    fetch_commits,
    fetch_commit_detail,
    fetch_issues,
    fetch_item_by_number,
    fetch_item_detail,
    fetch_labels,
    fetch_prs,
    fetch_release_assets,
    fetch_releases,
    fetch_tags,
    total_downloads,
    fetch_workflow_runs,
    fetch_workflows,
    list_repos,
    open_in_browser,
    parent_repo,
    reopen_item,
    sort_items,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _parse_repo_spec(value: str) -> str | None:
    """Parse a GitHub repo URL or OWNER/NAME into normalized OWNER/NAME.

    Accepts:
      - https://github.com/owner/name
      - https://github.com/owner/name.git
      - git@github.com:owner/name.git
      - owner/name
    Returns None if the input can't be parsed.
    """
    v = value.strip()
    if not v:
        return None
    # SSH form: git@github.com:owner/name.git
    if v.startswith("git@github.com:"):
        v = v[len("git@github.com:"):]
    # HTTPS form: strip scheme + host
    elif "github.com/" in v:
        v = v.split("github.com/", 1)[1]
    # Strip trailing .git
    if v.endswith(".git"):
        v = v[:-4]
    # Strip trailing slash or extra path (e.g. /issues, /pull/123)
    v = v.split("/", 2)
    if len(v) < 2 or not v[0] or not v[1]:
        return None
    owner, name = v[0], v[1].split("?", 1)[0].split("#", 1)[0]
    if not owner or not name:
        return None
    return f"{owner}/{name}"


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
ID_GOTO = wx.NewIdRef()
ID_NEXT_COMMENT = wx.NewIdRef()
ID_PREV_COMMENT = wx.NewIdRef()
ID_VIEW_MORE = wx.NewIdRef()
ID_VIEW_ISSUES = wx.NewIdRef()
ID_VIEW_BRANCHES = wx.NewIdRef()
ID_VIEW_COMMITS = wx.NewIdRef()
ID_VIEW_TAGS = wx.NewIdRef()
ID_VIEW_RELEASES = wx.NewIdRef()
ID_VIEW_WORKFLOWS = wx.NewIdRef()
ID_VIEW_WORKFLOW = wx.NewIdRef()
ID_VIEW_LABELS = wx.NewIdRef()
ID_VIEW_FAVORITES = wx.NewIdRef()
ID_NEW_LABEL = wx.NewIdRef()
ID_DELETE_LABEL = wx.NewIdRef()
ID_BROWSE_LABEL = wx.NewIdRef()
# Actions menu. ID_DELETE_ITEM is one item that deletes whatever the current
# view can delete, so a single Ctrl+D covers labels and workflow runs alike.
# The Run Workflow / Download Artifact entries get their own ids because the
# right-click menus bind ID_RUN_WORKFLOW and ID_DOWNLOAD_ARTIFACT on the popup.
ID_DELETE_ITEM = wx.NewIdRef()
ID_ACT_RUN_WORKFLOW = wx.NewIdRef()
ID_ACT_DOWNLOAD_ARTIFACT = wx.NewIdRef()
ID_FILTER = wx.NewIdRef()
ID_SELECT_BRANCH = wx.NewIdRef()
ID_COMPARE_BRANCHES = wx.NewIdRef()
ID_OPEN_REPO = wx.NewIdRef()
ID_REMOVE_REPO = wx.NewIdRef()
ID_RUN_WORKFLOW = wx.NewIdRef()
ID_DOWNLOAD_ARTIFACT = wx.NewIdRef()
ID_CHECK_UPDATES = wx.NewIdRef()


# View modes
VIEW_ISSUES = "issues"
VIEW_BRANCHES = "branches"
VIEW_COMMITS = "commits"
VIEW_TAGS = "tags"
VIEW_RELEASES = "releases"
VIEW_WORKFLOWS = "workflows"   # workflow definitions (files)
VIEW_WORKFLOW = "workflow"     # workflow runs
VIEW_ARTIFACTS = "artifacts"   # artifacts of a single workflow run (drill-down)
VIEW_ASSETS = "assets"         # files attached to a single release (drill-down)
VIEW_LABELS = "labels"
VIEW_FAVORITES = "favorites"

# Drill-down views: pressing Backspace in the key view returns to its parent.
# These are the views you reach by activating an item in another view
# (a branch's commits, a run's artifacts), so Backspace is a natural "up".
PARENT_VIEW = {
    VIEW_COMMITS: VIEW_BRANCHES,
    VIEW_ARTIFACTS: VIEW_WORKFLOW,
    VIEW_ASSETS: VIEW_RELEASES,
}

# Columns for the favorites view (mixed item types)
FAVORITES_COLUMNS = ["type", "repo", "title", "subtitle"]
FAVORITES_DEFAULT_COLUMNS = ["type", "repo", "title", "subtitle"]

# Column defaults per view mode
VIEW_COLUMNS = {
    VIEW_ISSUES: (DEFAULT_COLUMNS, ALL_COLUMNS),
    VIEW_BRANCHES: (BRANCH_DEFAULT_COLUMNS, BRANCH_COLUMNS),
    VIEW_COMMITS: (COMMIT_DEFAULT_COLUMNS, COMMIT_COLUMNS),
    VIEW_TAGS: (TAG_DEFAULT_COLUMNS, TAG_COLUMNS),
    VIEW_RELEASES: (RELEASE_DEFAULT_COLUMNS, RELEASE_COLUMNS),
    VIEW_WORKFLOWS: (WORKFLOW_DEF_DEFAULT_COLUMNS, WORKFLOW_DEF_COLUMNS),
    VIEW_WORKFLOW: (WORKFLOW_DEFAULT_COLUMNS, WORKFLOW_COLUMNS),
    VIEW_ARTIFACTS: (ARTIFACT_DEFAULT_COLUMNS, ARTIFACT_COLUMNS),
    VIEW_ASSETS: (ASSET_DEFAULT_COLUMNS, ASSET_COLUMNS),
    VIEW_LABELS: (LABEL_DEFAULT_COLUMNS, LABEL_COLUMNS),
    VIEW_FAVORITES: (FAVORITES_DEFAULT_COLUMNS, FAVORITES_COLUMNS),
}


# ── Run Workflow: inputs dialog ─────────────────────────────────────────


class WorkflowInputsDialog(wx.Dialog):
    """Collects ``workflow_dispatch`` input values before a manual run.

    Built at runtime from the schema parsed out of the workflow file, the same
    way GitHub's own "Run workflow" form is. Control per declared type:

        choice / environment → wx.Choice
        boolean              → wx.CheckBox
        number / string      → wx.TextCtrl

    Accessibility: because the form is generated rather than hand-written,
    labelling has to be done deliberately. Every control gets a wx.StaticText
    placed immediately before it in the sizer *and* a matching SetName, so the
    accessible name is right whether the screen reader takes it from the
    associated label or from the control itself. A checkbox carries its own
    label, so it gets the name only — a separate StaticText would make it read
    twice. Controls are added in declaration order, which is the tab order.
    """

    def __init__(
        self,
        parent: wx.Window,
        workflow_name: str,
        branch: str,
        inputs: list["WorkflowInput"],
    ) -> None:
        super().__init__(
            parent,
            title=f"Run {workflow_name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._inputs = inputs
        self._controls: dict[str, wx.Window] = {}

        outer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(self, label=f"Run '{workflow_name}' on {branch}")
        outer.Add(heading, 0, wx.ALL, 10)

        grid = wx.BoxSizer(wx.VERTICAL)
        for spec in inputs:
            label = spec.label
            if spec.required:
                label += " (required)"

            if spec.type == "boolean":
                ctrl = wx.CheckBox(self, label=label)
                ctrl.SetValue(spec.default.strip().lower() == "true")
                ctrl.SetName(label)
                grid.Add(ctrl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
            else:
                text = wx.StaticText(self, label=label)
                grid.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
                if spec.options:
                    ctrl = wx.Choice(self, choices=spec.options)
                    # Preselect the declared default, else the first option —
                    # never leave a Choice unset, which reads as blank.
                    idx = spec.options.index(spec.default) if spec.default in spec.options else 0
                    ctrl.SetSelection(idx)
                else:
                    ctrl = wx.TextCtrl(self, value=spec.default)
                ctrl.SetName(label)
                grid.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

            self._controls[spec.name] = ctrl

        outer.Add(grid, 1, wx.EXPAND)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizerAndFit(outer)
        self.SetMinSize((420, -1))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        if inputs:
            self._controls[inputs[0].name].SetFocus()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """Block OK on an empty required field, naming the field at fault."""
        for spec in self._inputs:
            if not spec.required:
                continue
            ctrl = self._controls[spec.name]
            if isinstance(ctrl, wx.TextCtrl) and not ctrl.GetValue().strip():
                wx.MessageBox(
                    f"{spec.label} is required.",
                    "Run Workflow",
                    wx.OK | wx.ICON_INFORMATION,
                    self,
                )
                ctrl.SetFocus()
                return
        event.Skip()

    def values(self) -> dict[str, str]:
        """The collected inputs, as the strings the dispatch payload wants."""
        out: dict[str, str] = {}
        for spec in self._inputs:
            ctrl = self._controls[spec.name]
            if isinstance(ctrl, wx.CheckBox):
                out[spec.name] = "true" if ctrl.GetValue() else "false"
            elif isinstance(ctrl, wx.Choice):
                out[spec.name] = ctrl.GetStringSelection()
            else:
                out[spec.name] = ctrl.GetValue().strip()
        return out


# ── New label dialog ────────────────────────────────────────────────────


class NewLabelDialog(wx.Dialog):
    """Collects the name, description, and colour for a new label.

    Same labelling discipline as WorkflowInputsDialog: every field gets a
    StaticText immediately before it *and* a matching SetName, so the
    accessible name is right whichever the screen reader picks up. Tab order
    is declaration order: name, description, colour.

    Colour is optional — GitHub picks one when it is left blank, which is the
    fastest path and the reason the field comes last.
    """

    def __init__(self, parent: wx.Window, repo: str) -> None:
        super().__init__(
            parent,
            title="New Label",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(self, label=f"Create a label in {repo}"),
            0, wx.ALL, 10,
        )

        fields = wx.BoxSizer(wx.VERTICAL)

        def add_field(label: str, hint: str = "") -> wx.TextCtrl:
            text = wx.StaticText(self, label=label)
            fields.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
            ctrl = wx.TextCtrl(self)
            ctrl.SetName(label)
            if hint:
                ctrl.SetHint(hint)
            fields.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
            return ctrl

        self.name_ctrl = add_field("Name (required)")
        self.desc_ctrl = add_field("Description")
        self.color_ctrl = add_field(
            "Colour, 6-digit hex (optional — GitHub picks one if blank)",
            "e.g. d73a4a",
        )

        outer.Add(fields, 1, wx.EXPAND)
        outer.Add(
            self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL),
            0, wx.ALIGN_RIGHT | wx.ALL, 10,
        )
        self.SetSizerAndFit(outer)
        self.SetMinSize((460, -1))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.name_ctrl.SetFocus()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """Validate before closing so `gh` never fails on something we can see."""
        if not self.name_ctrl.GetValue().strip():
            wx.MessageBox(
                "A label needs a name.", "New Label",
                wx.OK | wx.ICON_INFORMATION, self,
            )
            self.name_ctrl.SetFocus()
            return
        color = self.color_ctrl.GetValue().strip().lstrip("#")
        if color and (len(color) != 6 or any(c not in "0123456789abcdefABCDEF" for c in color)):
            wx.MessageBox(
                f"'{color}' is not a colour. Give 6 hex digits, such as d73a4a, "
                "or leave the field blank to let GitHub choose.",
                "New Label",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            self.color_ctrl.SetFocus()
            return
        event.Skip()

    def values(self) -> tuple[str, str, str]:
        """(name, colour, description) — colour without its leading #."""
        return (
            self.name_ctrl.GetValue().strip(),
            self.color_ctrl.GetValue().strip().lstrip("#"),
            self.desc_ctrl.GetValue().strip(),
        )


# ── Main frame ──────────────────────────────────────────────────────────


class GhViewerFrame(wx.Frame):
    """Main application window."""

    def __init__(
        self,
        repo: str | None = None,
        update_service: "updater.UpdateService | None" = None,
    ) -> None:
        super().__init__(
            None,
            title="ghviewer — GitHub Issues & PRs",
            size=(1000, 700),
        )
        self.updater = update_service
        self.repo: str | None = None
        self.items: list[Item] = []
        self._all_repos: list[dict] = []
        self._pinned_repos: list[str] = load_pinned()
        self.favorites: list[FavoriteEntry] = load_favorites()

        # View settings
        self.columns: list[str] = list(DEFAULT_COLUMNS)
        self.sort_order: str = SORT_ORDERS[0]
        self.list_mode: str = "quick"  # "quick" or "full"
        self.state_filter: str = "open"  # "open", "closed", "all"
        self.tab_filter: str = "both"  # "issues", "prs", "both"
        self.page_size: int = 100      # how many items to fetch per page
        self.current_limit: int = 100  # current fetch limit (grows via View More)
        self.view_mode: str = VIEW_ISSUES  # current view: issues, branches, commits, etc.
        self.git_items: list = []   # holds Branch/Commit/Tag/Release/WorkflowRun objects
        self.commit_branch: str = ""  # branch for commits view ("" = default branch)
        self.artifacts_run: WorkflowRun | None = None  # run whose artifacts are shown
        self.assets_release: Release | None = None  # release whose assets are shown
        self.filter_text: str = ""  # quick filter text (Ctrl+F, empty = no filter)
        # Every list fetch carries a token. Results whose token is no longer the
        # current one are dropped, because by then they belong to a view or a
        # repo the user has already left. See `_begin_fetch`.
        self._fetch_token: int = 0
        # Label the Issues view is restricted to ("" = no restriction). Set by
        # pressing Enter on a label; unlike the quick filter this is applied by
        # `gh`, so it reaches issues past the current page.
        self.label_filter: str = ""

        self._build_ui()
        self._bind_events()
        self._build_menu()
        self._update_menu_checks()

        if repo:
            self._select_repo(repo)
        else:
            self._load_repos()

        self.Show()

        # Check for updates in the background so startup is never blocked.
        # Must come after Show(): a modal raised against an unshown frame
        # returns immediately instead of waiting for the user.
        if self.updater:
            wx.CallLater(2000, self._start_update_check)

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Main splitter: repo list (left) | issues+details (right)
        self.main_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE, name="main_splitter")
        self.main_splitter.SetMinimumPaneSize(200)

        # Left panel: repo list
        repo_panel = wx.Panel(self.main_splitter, name="repo_panel")
        repo_sizer = wx.BoxSizer(wx.VERTICAL)
        repo_sizer.Add(
            wx.StaticText(repo_panel, label="Repositories"),
            flag=wx.LEFT | wx.TOP, border=3,
        )
        self.repo_list = wx.ListBox(
            repo_panel,
            name="repo_list",
            style=wx.LB_SINGLE | wx.BORDER_SUNKEN,
        )
        repo_sizer.Add(self.repo_list, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        repo_panel.SetSizer(repo_sizer)

        # Right panel: issue list (top) + details (bottom)
        right_panel = wx.Panel(self.main_splitter, name="right_panel")
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        self.splitter = wx.SplitterWindow(right_panel, style=wx.SP_LIVE_UPDATE)
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

        right_sizer.Add(self.splitter, proportion=1, flag=wx.EXPAND)
        right_panel.SetSizer(right_sizer)

        self.main_splitter.SplitVertically(repo_panel, right_panel, 300)
        self.main_splitter.SetSashPosition(300)

        # Status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready")

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.main_splitter, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        self.SetSizer(sizer)

        # Initial columns
        self._rebuild_columns()

    def _rebuild_columns(self) -> None:
        """Rebuild the ListCtrl columns from self.columns."""
        self.list_ctrl.DeleteAllItems()
        self.list_ctrl.DeleteAllColumns()
        widths = {
            # Issues/PRs
            "number": 60, "type": 60, "state": 70, "title": 400,
            "author": 120, "created": 100, "updated": 100, "labels": 150,
            "assignees": 120, "comments": 70, "draft": 50, "review": 100,
            "+/-": 90, "files": 50, "base": 100, "head": 100,
            # Branches
            "branch": 150, "last commit": 400, "date": 100, "protected": 70,
            "ahead": 60, "behind": 60,
            # Commits
            "sha": 80, "message": 400,
            # Tags
            "tag": 150, "commit": 80,
            # Releases
            "tag": 100, "name": 250, "draft": 50, "prerelease": 70,
            # Workflow (runs + definitions) + artifacts
            "name": 150, "status": 100, "result": 100, "event": 100, "#": 50,
            "state": 90, "path": 320, "size": 90, "expired": 70,
            # Labels
            "label": 180, "description": 340, "color": 80, "default": 70,
            # Favorites
            "repo": 180, "subtitle": 250,
        }
        for i, col in enumerate(self.columns):
            self.list_ctrl.InsertColumn(i, col, width=widths.get(col, 100))

    # ── Menu ────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu_bar = wx.MenuBar()

        # File menu — the repository and the list itself
        file_menu = wx.Menu()
        file_menu.Append(ID_OPEN_REPO, "Open Repository…\tCtrl+Shift+O")
        file_menu.Append(ID_REMOVE_REPO, "Remove from List…")
        file_menu.AppendSeparator()
        file_menu.Append(ID_REFRESH, "Refresh\tCtrl+R")
        file_menu.Append(ID_VIEW_MORE, "View More\tCtrl++")
        file_menu.AppendSeparator()
        file_menu.Append(ID_GOTO, "Go To Issue…\tCtrl+G")
        file_menu.Append(ID_FILTER, "Quick Filter…\tCtrl+F")
        file_menu.AppendSeparator()
        file_menu.Append(ID_NEXT_COMMENT, "Next Comment\tAlt+N")
        file_menu.Append(ID_PREV_COMMENT, "Previous Comment\tAlt+P")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "Quit\tCtrl+Q")
        menu_bar.Append(file_menu, "File")

        # Actions menu — everything that acts on what the list is showing.
        # One home for them, whichever view they belong to. Items are re-labelled
        # and enabled per view in `_update_actions_menu`, so the menu is a
        # reliable answer to "what can I do here?" rather than a list to sift.
        actions_menu = wx.Menu()
        actions_menu.Append(ID_OPEN_BROWSER, "Open in Browser\tCtrl+O")
        actions_menu.AppendSeparator()
        self._act_close = actions_menu.Append(ID_CLOSE_ITEM, "Close Issue/PR\tCtrl+W")
        self._act_reopen = actions_menu.Append(ID_REOPEN, "Reopen Issue/PR\tCtrl+Shift+W")
        self._act_comment = actions_menu.Append(ID_COMMENT, "Add Comment…\tCtrl+M")
        actions_menu.AppendSeparator()
        # Ctrl+I and Ctrl+D are safe as accelerators; a bare Delete accelerator
        # would not be, since it would swallow the Delete key inside the list.
        # The bare Insert and Delete keys are handled in `on_char_hook`.
        self._act_new = actions_menu.Append(ID_NEW_LABEL, "New Label…\tCtrl+I")
        self._act_delete = actions_menu.Append(ID_DELETE_ITEM, "Delete\tCtrl+D")
        actions_menu.AppendSeparator()
        self._act_run_workflow = actions_menu.Append(
            ID_ACT_RUN_WORKFLOW, "Run Workflow on Branch…"
        )
        self._act_download = actions_menu.Append(
            ID_ACT_DOWNLOAD_ARTIFACT, "Download Artifact…"
        )
        actions_menu.AppendSeparator()
        self._act_select_branch = actions_menu.Append(
            ID_SELECT_BRANCH, "Select Branch…\tCtrl+B"
        )
        self._act_compare = actions_menu.Append(
            ID_COMPARE_BRANCHES, "Compare Branches…\tCtrl+Shift+B"
        )
        menu_bar.Append(actions_menu, "Actions")
        self._actions_menu = actions_menu

        # View menu
        view_menu = wx.Menu()

        # View Mode submenu — switch between Issues/PRs and Git views.
        # Ctrl+1..Ctrl+8 jump straight to a view; the numbers follow the order
        # of this menu, so the shortcut is readable off the menu itself.
        show_menu = wx.Menu()
        show_menu.AppendRadioItem(ID_VIEW_ISSUES, "Issues & PRs\tCtrl+1")
        show_menu.AppendRadioItem(ID_VIEW_BRANCHES, "Branches\tCtrl+2")
        show_menu.AppendRadioItem(ID_VIEW_COMMITS, "Commits\tCtrl+3")
        show_menu.AppendRadioItem(ID_VIEW_TAGS, "Tags\tCtrl+4")
        show_menu.AppendRadioItem(ID_VIEW_RELEASES, "Releases\tCtrl+5")
        show_menu.AppendRadioItem(ID_VIEW_WORKFLOWS, "Workflows\tCtrl+6")
        show_menu.AppendRadioItem(ID_VIEW_WORKFLOW, "Workflow Runs\tCtrl+7")
        show_menu.AppendRadioItem(ID_VIEW_LABELS, "Labels\tCtrl+8")
        show_menu.AppendRadioItem(ID_VIEW_FAVORITES, "★ Favorites\tCtrl+9")
        view_menu.AppendSubMenu(show_menu, "View Mode")

        view_menu.AppendSeparator()

        # List mode submenu
        mode_menu = wx.Menu()
        mode_menu.AppendRadioItem(ID_QUICK_MODE, "Quick Mode (compact)")
        mode_menu.AppendRadioItem(ID_FULL_MODE, "Full Mode (field names for screen reader)")
        view_menu.AppendSubMenu(mode_menu, "List Mode")

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

        # Columns submenu (rebuilt when view mode changes)
        self._col_menu = wx.Menu()
        self._col_menu_items = {}
        self._rebuild_columns_menu()
        view_menu.AppendSubMenu(self._col_menu, "Columns")

        view_menu.AppendSeparator()

        # State filter submenu
        state_menu = wx.Menu()
        state_menu.AppendRadioItem(ID_STATE_OPEN, "Open")
        state_menu.AppendRadioItem(ID_STATE_CLOSED, "Closed")
        state_menu.AppendRadioItem(ID_STATE_ALL, "All")
        view_menu.AppendSubMenu(state_menu, "State")

        # Filter submenu — which item types to show in Issues & PRs view
        tab_menu = wx.Menu()
        tab_menu.AppendRadioItem(ID_TAB_ISSUES, "Issues Only")
        tab_menu.AppendRadioItem(ID_TAB_PRS, "PRs Only")
        tab_menu.AppendRadioItem(ID_TAB_BOTH, "Issues & PRs")
        view_menu.AppendSubMenu(tab_menu, "Filter")

        menu_bar.Append(view_menu, "View")

        # Help menu
        help_menu = wx.Menu()
        help_menu.Append(ID_CHECK_UPDATES, "Check for Updates…")
        help_menu.Append(wx.ID_ABOUT, "About GHManage")
        menu_bar.Append(help_menu, "Help")

        self.SetMenuBar(menu_bar)

        self.Bind(wx.EVT_MENU, self.on_check_updates, id=ID_CHECK_UPDATES)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)

        # Bind mode/state/tab menu items
        self.Bind(wx.EVT_MENU, self.on_quick_mode, id=ID_QUICK_MODE)
        self.Bind(wx.EVT_MENU, self.on_full_mode, id=ID_FULL_MODE)
        self.Bind(wx.EVT_MENU, self.on_state_open, id=ID_STATE_OPEN)
        self.Bind(wx.EVT_MENU, self.on_state_closed, id=ID_STATE_CLOSED)
        self.Bind(wx.EVT_MENU, self.on_state_all, id=ID_STATE_ALL)
        self.Bind(wx.EVT_MENU, self.on_tab_issues, id=ID_TAB_ISSUES)
        self.Bind(wx.EVT_MENU, self.on_tab_prs, id=ID_TAB_PRS)
        self.Bind(wx.EVT_MENU, self.on_tab_both, id=ID_TAB_BOTH)
        self.Bind(wx.EVT_MENU, self.on_view_issues, id=ID_VIEW_ISSUES)
        self.Bind(wx.EVT_MENU, self.on_view_branches, id=ID_VIEW_BRANCHES)
        self.Bind(wx.EVT_MENU, self.on_view_commits, id=ID_VIEW_COMMITS)
        self.Bind(wx.EVT_MENU, self.on_view_tags, id=ID_VIEW_TAGS)
        self.Bind(wx.EVT_MENU, self.on_view_releases, id=ID_VIEW_RELEASES)
        self.Bind(wx.EVT_MENU, self.on_view_workflows, id=ID_VIEW_WORKFLOWS)
        self.Bind(wx.EVT_MENU, self.on_view_workflow, id=ID_VIEW_WORKFLOW)
        self.Bind(wx.EVT_MENU, self.on_view_labels, id=ID_VIEW_LABELS)
        self.Bind(wx.EVT_MENU, self.on_view_favorites, id=ID_VIEW_FAVORITES)

    # ── Updates ─────────────────────────────────────────────────────────

    def _start_update_check(self) -> None:
        """Background check run once at startup."""
        threading.Thread(
            target=self._check_for_updates, args=(True,), daemon=True
        ).start()

    def on_check_updates(self, event) -> None:
        """Help ▸ Check for Updates — reports the result either way."""
        self._announce("Checking for updates…")
        threading.Thread(
            target=self._check_for_updates, args=(False,), daemon=True
        ).start()

    def _check_for_updates(self, silent: bool = True) -> None:
        """Worker thread. `silent` = the startup check, which never interrupts.

        On startup a found update is only announced in the status bar; it
        installs itself the next time GHManage starts. Stealing focus with a
        modal at launch — and restarting out from under the user — is worse
        than waiting. The Help menu check is user-initiated, so it may prompt.
        """
        if not self.updater:
            if not silent:
                wx.CallAfter(self._show_no_update, portable=True)
            return

        info = self.updater.check_for_update()
        if not info:
            if not silent:
                wx.CallAfter(self._show_no_update, portable=False)
            return

        if silent:
            wx.CallAfter(
                self._announce,
                f"GHManage {info.version} downloaded — "
                "it will be installed next time you start GHManage.",
            )
        else:
            wx.CallAfter(self._show_update_dialog, info.version, info.whats_new_url)

    def _show_no_update(self, portable: bool) -> None:
        if portable:
            msg = (
                f"GHManage {APP_VERSION} is running as a portable copy, "
                "which cannot update itself.\n\n"
                "Install GHManage to receive automatic updates."
            )
        else:
            msg = f"GHManage {APP_VERSION} is up to date."
        wx.MessageBox(msg, "Check for Updates", wx.OK | wx.ICON_INFORMATION, self)

    def _show_update_dialog(self, version: str, url: str) -> None:
        msg = (
            f"GHManage {version} is available. You are running {APP_VERSION}.\n\n"
            "It is downloading in the background. Choose Restart Now to "
            "install it immediately, or Later to install it the next time "
            "you start GHManage."
        )
        dlg = wx.MessageDialog(
            self, msg, "Update Available", wx.YES_NO | wx.ICON_INFORMATION
        )
        dlg.SetYesNoLabels("&Restart Now", "&Later")
        try:
            restart_now = dlg.ShowModal() == wx.ID_YES
        finally:
            dlg.Destroy()

        if not restart_now:
            return  # already downloaded; bootstrap() applies it on next launch

        if not self.updater.apply_update_and_restart(sys.argv[1:]):
            wx.MessageBox(
                "The update could not be applied. It will be retried the next "
                f"time GHManage starts.\n\nRelease notes: {url}",
                "Update Failed",
                wx.OK | wx.ICON_WARNING,
                self,
            )

    def on_about(self, event) -> None:
        wx.MessageBox(
            f"GHManage {APP_VERSION}\n\n"
            "A GUI viewer and manager for GitHub issues and pull requests.\n\n"
            f"{updater.REPO_URL}",
            "About GHManage",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _update_menu_checks(self) -> None:
        """Update checkmarks/radio selections to match current settings."""
        menu_bar = self.GetMenuBar()
        # List mode
        menu_bar.Check(ID_QUICK_MODE, self.list_mode == "quick")
        menu_bar.Check(ID_FULL_MODE, self.list_mode == "full")
        # View mode (Show submenu)
        menu_bar.Check(ID_VIEW_ISSUES, self.view_mode == VIEW_ISSUES)
        menu_bar.Check(ID_VIEW_BRANCHES, self.view_mode == VIEW_BRANCHES)
        menu_bar.Check(ID_VIEW_COMMITS, self.view_mode == VIEW_COMMITS)
        menu_bar.Check(ID_VIEW_TAGS, self.view_mode == VIEW_TAGS)
        menu_bar.Check(ID_VIEW_RELEASES, self.view_mode == VIEW_RELEASES)
        menu_bar.Check(ID_VIEW_WORKFLOWS, self.view_mode == VIEW_WORKFLOWS)
        menu_bar.Check(ID_VIEW_WORKFLOW, self.view_mode == VIEW_WORKFLOW)
        menu_bar.Check(ID_VIEW_LABELS, self.view_mode == VIEW_LABELS)
        menu_bar.Check(ID_VIEW_FAVORITES, self.view_mode == VIEW_FAVORITES)
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
        self._update_actions_menu()

    def _update_actions_menu(self) -> None:
        """Label and enable the Actions items for the current view.

        The Delete entry names what it would delete, so the menu never offers a
        bare "Delete" whose object you have to guess, and is disabled where
        nothing can be deleted — which also parks its Ctrl+D accelerator.
        """
        if not hasattr(self, "_act_delete"):
            return  # called before the menu exists
        issues = self.view_mode == VIEW_ISSUES
        self._act_close.Enable(issues)
        self._act_reopen.Enable(issues)
        self._act_comment.Enable(issues)

        self._act_new.Enable(bool(self.repo))

        if self.view_mode == VIEW_LABELS:
            self._act_delete.SetItemLabel("Delete Label…\tCtrl+D")
            self._act_delete.Enable(True)
        elif self.view_mode == VIEW_WORKFLOW:
            self._act_delete.SetItemLabel("Delete Workflow Run…\tCtrl+D")
            self._act_delete.Enable(True)
        else:
            self._act_delete.SetItemLabel("Delete\tCtrl+D")
            self._act_delete.Enable(False)

        self._act_run_workflow.Enable(self.view_mode == VIEW_WORKFLOWS)
        self._act_download.Enable(self.view_mode == VIEW_ARTIFACTS)
        self._act_select_branch.Enable(self.view_mode == VIEW_COMMITS)
        self._act_compare.Enable(self.view_mode == VIEW_BRANCHES)

    def _rebuild_columns_menu(self) -> None:
        """Rebuild the Columns submenu for the current view mode."""
        # Remove old items
        for item_id in list(self._col_menu_items.keys()):
            self.Unbind(wx.EVT_MENU, id=item_id)
            self._col_menu.DestroyItem(self._col_menu.FindItemById(item_id))
        self._col_menu_items = {}
        # Get available columns for current view
        _, all_cols = VIEW_COLUMNS.get(self.view_mode, (DEFAULT_COLUMNS, ALL_COLUMNS))
        for col in all_cols:
            item_id = wx.NewIdRef()
            self._col_menu_items[item_id] = col
            self._col_menu.AppendCheckItem(item_id, col)
            self.Bind(wx.EVT_MENU, self.on_column_toggled, id=item_id)

    def _switch_view(self, mode: str) -> None:
        """Switch to a different view mode (issues, branches, commits, etc.)."""
        if self.view_mode == mode:
            return
        # Every view but Favorites is a view *of a repo*. Refuse rather than
        # switch to an empty list, and put the radio check back where it was —
        # the menu item has already toggled itself by the time we get here.
        if mode != VIEW_FAVORITES and not self.repo:
            self._update_menu_checks()
            self._announce("Select a repository first.")
            return
        self.view_mode = mode
        # Reset per-view drill-down context and filter when leaving a view
        if mode != VIEW_COMMITS:
            self.commit_branch = ""
        if mode != VIEW_ARTIFACTS:
            self.artifacts_run = None
        if mode != VIEW_ASSETS:
            self.assets_release = None
        if mode != VIEW_ISSUES:
            self.label_filter = ""
        self.filter_text = ""  # clear filter on view switch
        # Update columns for the new view
        default_cols, _ = VIEW_COLUMNS.get(mode, (DEFAULT_COLUMNS, ALL_COLUMNS))
        self.columns = list(default_cols)
        self._rebuild_columns()
        self._rebuild_columns_menu()
        self._update_menu_checks()
        self.current_limit = self.page_size
        if mode == VIEW_FAVORITES:
            self._load_favorites_view()
        elif self.repo:
            self._load_items()

    # ── Event binding ───────────────────────────────────────────────────

    def _bind_events(self) -> None:
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_repo_activated, self.repo_list)
        self.repo_list.Bind(wx.EVT_CHAR_HOOK, self.on_repo_key_down)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected, self.list_ctrl)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated, self.list_ctrl)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_context_menu, self.list_ctrl)
        self.Bind(wx.EVT_LIST_KEY_DOWN, self.on_list_key_down, self.list_ctrl)
        self.details_text.Bind(wx.EVT_CHAR_HOOK, self.on_details_key_down)
        # Frame-level, so Insert/Delete in the Labels view work wherever focus
        # is — including the details panel, which is where the text describing
        # them is read. EVT_LIST_KEY_DOWN only fires for the list itself, which
        # made that text an instruction you could read but not follow.
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_MENU, self.on_refresh, id=ID_REFRESH)
        self.Bind(wx.EVT_MENU, self.on_open_repo, id=ID_OPEN_REPO)
        self.Bind(wx.EVT_MENU, self.on_remove_repo, id=ID_REMOVE_REPO)
        self.Bind(wx.EVT_MENU, self.on_open_browser, id=ID_OPEN_BROWSER)
        self.Bind(wx.EVT_MENU, self.on_close_item, id=ID_CLOSE_ITEM)
        self.Bind(wx.EVT_MENU, self.on_reopen, id=ID_REOPEN)
        self.Bind(wx.EVT_MENU, self.on_comment, id=ID_COMMENT)
        self.Bind(wx.EVT_MENU, self.on_goto, id=ID_GOTO)
        self.Bind(wx.EVT_MENU, self.on_filter, id=ID_FILTER)
        self.Bind(wx.EVT_MENU, self.on_new_label, id=ID_NEW_LABEL)
        self.Bind(wx.EVT_MENU, self.on_delete_label, id=ID_DELETE_LABEL)
        self.Bind(wx.EVT_MENU, self.on_delete_item, id=ID_DELETE_ITEM)
        self.Bind(wx.EVT_MENU, self.on_act_run_workflow, id=ID_ACT_RUN_WORKFLOW)
        self.Bind(wx.EVT_MENU, self.on_act_download_artifact, id=ID_ACT_DOWNLOAD_ARTIFACT)
        self.Bind(wx.EVT_MENU, self.on_select_branch, id=ID_SELECT_BRANCH)
        self.Bind(wx.EVT_MENU, self.on_compare_branches, id=ID_COMPARE_BRANCHES)
        self.Bind(wx.EVT_MENU, self.on_view_more, id=ID_VIEW_MORE)
        self.Bind(wx.EVT_MENU, self.on_next_comment, id=ID_NEXT_COMMENT)
        self.Bind(wx.EVT_MENU, self.on_prev_comment, id=ID_PREV_COMMENT)
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
        self.repo_list.Clear()
        # ★ Favorites entry first — special pseudo-repo
        n_fav = len(self.favorites)
        fav_label = f"★ Favorites ({n_fav})" if n_fav else "★ Favorites"
        self.repo_list.Append(fav_label, clientData="__favorites__")
        # Pinned (added-by-URL) repos next, marked with a pin
        existing = {r.get("nameWithOwner", "") for r in repos}
        shown = set()
        for name in self._pinned_repos:
            if name in shown:
                continue
            shown.add(name)
            # If it's also in the gh list, reuse its description
            desc = ""
            for r in repos:
                if r.get("nameWithOwner", "") == name:
                    desc = r.get("description") or ""
                    break
            label = f"📌 {name} — {desc}" if desc else f"📌 {name}"
            self.repo_list.Append(label, clientData=name)
        # Then the user's own repos from gh
        for repo in repos:
            name = repo.get("nameWithOwner", "")
            if name in shown:
                continue
            shown.add(name)
            desc = repo.get("description") or ""
            label = f"{name} — {desc}" if desc else name
            self.repo_list.Append(label, clientData=name)
        if self.repo_list.GetCount():
            self.SetStatusText(f"Loaded {self.repo_list.GetCount()} repositories. Select one to view issues and PRs.")
            self.repo_list.SetSelection(0)
            self.repo_list.SetFocus()
        else:
            self.SetStatusText("No repositories found.")

    def _on_repos_error(self, msg: str) -> None:
        self.SetStatusText(f"Error loading repos: {msg}")

    def on_repo_activated(self, event: wx.CommandEvent) -> None:
        """Double-click on repo list — load that repo's items."""
        idx = self.repo_list.GetSelection()
        if idx != wx.NOT_FOUND:
            name = self.repo_list.GetClientData(idx)
            if name:
                if name == "__favorites__":
                    self._select_favorites()
                else:
                    self._select_repo(name)

    def on_repo_key_down(self, event: wx.KeyEvent) -> None:
        """Handle Enter key on repo list — load the selected repo."""
        if event.GetKeyCode() == wx.WXK_RETURN:
            idx = self.repo_list.GetSelection()
            if idx != wx.NOT_FOUND:
                name = self.repo_list.GetClientData(idx)
                if name:
                    if name == "__favorites__":
                        self._select_favorites()
                    else:
                        self._select_repo(name)
            return  # swallow the key
        event.Skip()

    def _select_repo(self, repo: str) -> None:
        if " — " in repo:
            repo = repo.split(" — ")[0].strip()
        self.repo = repo
        self.current_limit = self.page_size  # reset to first page
        self.filter_text = ""  # clear filter on repo switch
        self.label_filter = ""  # a label of the old repo means nothing here
        self._update_actions_menu()  # repo-dependent items (New Label…)
        self._update_title()
        # Reset to issues view when switching repos
        if self.view_mode != VIEW_ISSUES:
            self._switch_view(VIEW_ISSUES)
        else:
            self._load_items()

    def _select_favorites(self) -> None:
        """Switch to the Favorites view — shows all favorited items across repos."""
        self.repo = None
        self._update_title()
        self._update_actions_menu()
        if self.view_mode != VIEW_FAVORITES:
            self._switch_view(VIEW_FAVORITES)
        else:
            self._load_favorites_view()

    # ── Item loading ───────────────────────────────────────────────────

    def _begin_fetch(self) -> int:
        """Claim the list for a new load and invalidate any still in flight.

        Fetches run on background threads and come back through `wx.CallAfter`,
        so a slow one can land long after the user has moved on — the issues of
        a big repo arriving into the Labels view, filling it with blank rows
        under the wrong columns and a status bar describing a different view.
        Nothing cancels a `gh` call, so instead every load takes a token and the
        handlers ignore results that are no longer the current one.
        """
        self._fetch_token += 1
        return self._fetch_token

    def _fetch_is_current(self, token: int) -> bool:
        """True if `token` is still the load whose results the list wants."""
        return token == self._fetch_token

    def _load_favorites_view(self) -> None:
        """Populate the list with all favorited items (mixed types, cross-repo)."""
        # Favorites load synchronously from disk, but still take a token — an
        # in-flight repo fetch must not land on top of them.
        self._begin_fetch()
        self.SetStatusText("Loading favorites…")
        self.details_text.Clear()
        self.favorites = load_favorites()
        self.git_items = list(self.favorites)  # favorites are stored as git_items for the list
        self.items = []
        filtered = self._populate_filtered_list(self.favorites)
        n = len(self.favorites)
        self.SetStatusText(
            f"★ Favorites — {n} item{'s' if n != 1 else ''}.  "
            f"F=unfavorite  Enter=open in browser  Ctrl+F=filter  "
            f"Mode={self.list_mode}"
            + self._filter_status_suffix()
        )
        self._update_title()
        if filtered:
            wx.CallLater(100, self._focus_list)

    def _load_items(self) -> None:
        # Name the view as well as the repo: after a Ctrl+<n> switch this is the
        # first confirmation of where you landed.
        view_label = self._VIEW_LABELS.get(self.view_mode, self.view_mode)
        self.SetStatusText(f"Loading {view_label} for {self.repo}…")
        self.list_ctrl.DeleteAllItems()
        self.details_text.Clear()
        # Read the view and repo once, here on the UI thread, so the worker
        # cannot see them change halfway through and dispatch on a mix of both.
        token = self._begin_fetch()
        view = self.view_mode

        def worker() -> None:
            try:
                if view == VIEW_ISSUES:
                    issues = []
                    prs = []
                    if self.tab_filter in ("issues", "both"):
                        issues = fetch_issues(
                            self.repo, self.state_filter, self.current_limit,
                            self.label_filter,
                        )
                    if self.tab_filter in ("prs", "both"):
                        prs = fetch_prs(
                            self.repo, self.state_filter, self.current_limit,
                            self.label_filter,
                        )
                    combined = sort_items(issues + prs, self.sort_order)
                    wx.CallAfter(
                        self._on_items_loaded, token, combined, len(issues), len(prs)
                    )
                elif view == VIEW_BRANCHES:
                    branches = fetch_branches(self.repo, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, branches, "branches")
                elif view == VIEW_COMMITS:
                    commits = fetch_commits(self.repo, self.commit_branch, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, commits, "commits")
                elif view == VIEW_TAGS:
                    tags = fetch_tags(self.repo, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, tags, "tags")
                elif view == VIEW_RELEASES:
                    releases = fetch_releases(self.repo, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, releases, "releases")
                elif view == VIEW_WORKFLOWS:
                    workflows = fetch_workflows(self.repo, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, workflows, "workflows")
                elif view == VIEW_LABELS:
                    labels = fetch_labels(self.repo, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, labels, "labels")
                elif view == VIEW_WORKFLOW:
                    runs = fetch_workflow_runs(self.repo, self.current_limit)
                    wx.CallAfter(self._on_git_items_loaded, token, runs, "workflow runs")
                elif view == VIEW_ARTIFACTS:
                    if self.artifacts_run:
                        arts = fetch_run_artifacts(
                            self.repo, self.artifacts_run.run_id, self.current_limit
                        )
                        wx.CallAfter(self._on_git_items_loaded, token, arts, "artifacts")
                    else:
                        wx.CallAfter(self._on_git_items_loaded, token, [], "artifacts")
                elif view == VIEW_ASSETS:
                    if self.assets_release:
                        assets = fetch_release_assets(
                            self.repo,
                            self.assets_release.id,
                            self.assets_release.tag,
                            self.current_limit,
                        )
                        wx.CallAfter(self._on_git_items_loaded, token, assets, "assets")
                    else:
                        wx.CallAfter(self._on_git_items_loaded, token, [], "assets")
            except GhError as exc:
                wx.CallAfter(self._on_fetch_error, token, str(exc))
                return

        threading.Thread(target=worker, daemon=True).start()

    def _item_label(self, item, col: str) -> str:
        """Get the display value for a single column, with mode-aware formatting."""
        val = item.to_row(self.columns).get(col, "")
        if self.list_mode == "full":
            return f"{col}: {val}" if val else ""
        return val

    def _favorite_prefix(self, item) -> str:
        """Return '★ ' if the item is in favorites, else empty string."""
        url = getattr(item, "url", "") or ""
        if url and is_favorite(url, self.favorites):
            return "★ "
        return ""

    # View-mode display labels for the window title
    _VIEW_LABELS = {
        VIEW_ISSUES: "Issues",
        VIEW_BRANCHES: "Branches",
        VIEW_COMMITS: "Commits",
        VIEW_TAGS: "Tags",
        VIEW_RELEASES: "Releases",
        VIEW_WORKFLOWS: "Workflows",
        VIEW_WORKFLOW: "Workflow Runs",
        VIEW_ARTIFACTS: "Artifacts",
        VIEW_ASSETS: "Release Assets",
        VIEW_LABELS: "Labels",
        VIEW_FAVORITES: "Favorites",
    }

    def _update_title(self) -> None:
        """Set the window title: <view> [<branch>] — <repo> — ghviewer."""
        view_label = self._VIEW_LABELS.get(self.view_mode, self.view_mode.title())
        parts: list[str] = [view_label]
        # Include branch where it matters (commits view)
        if self.view_mode == VIEW_COMMITS and self.commit_branch:
            parts.append(self.commit_branch)
        # Include the run being drilled into (artifacts view)
        if self.view_mode == VIEW_ARTIFACTS and self.artifacts_run:
            parts.append(f"run #{self.artifacts_run.run_number} {self.artifacts_run.name}")
        # Include the release being drilled into (assets view)
        if self.view_mode == VIEW_ASSETS and self.assets_release:
            parts.append(self.assets_release.tag or self.assets_release.name)
        # Include the label the issues list is restricted to
        if self.view_mode == VIEW_ISSUES and self.label_filter:
            parts.append(f"label: {self.label_filter}")
        if self.repo:
            parts.append(self.repo)
        parts.append("ghviewer")
        self.SetTitle(" — ".join(parts))

    def _populate_filtered_list(self, source_items: list, use_favorite_prefix: bool = False) -> None:
        """Populate the list ctrl with items that match the current filter.

        ``source_items`` is the full unfiltered list (self.items, self.git_items,
        or self.favorites). Only items matching ``self.filter_text`` are shown.
        """
        self.list_ctrl.DeleteAllItems()
        filtered = [it for it in source_items if self._matches_filter(it)]
        for i, item in enumerate(filtered):
            prefix = self._favorite_prefix(item) if use_favorite_prefix else ""
            if isinstance(item, FavoriteEntry):
                row = {
                    "type": item.item_type,
                    "repo": item.repo,
                    "title": item.title,
                    "subtitle": item.subtitle,
                }
                for j, col in enumerate(self.columns):
                    label = row.get(col, "")
                    if self.list_mode == "full":
                        label = f"{col}: {label}" if label else ""
                    if j == 0:
                        self.list_ctrl.InsertItem(i, prefix + label)
                    else:
                        self.list_ctrl.SetItem(i, j, label)
            else:
                for j, col in enumerate(self.columns):
                    label = self._item_label(item, col)
                    if j == 0:
                        self.list_ctrl.InsertItem(i, prefix + label)
                    else:
                        self.list_ctrl.SetItem(i, j, label)
        return filtered

    def _on_items_loaded(
        self, token: int, items: list[Item], n_issues: int, n_prs: int
    ) -> None:
        if not self._fetch_is_current(token):
            return  # the user has moved on; these belong to a view they left
        self.items = items
        self.git_items = []
        filtered = self._populate_filtered_list(items, use_favorite_prefix=True)
        # Note fork→parent redirection in the status bar
        upstream = parent_repo(self.repo)
        source = f"{self.repo} (issues from upstream {upstream})" if upstream else self.repo
        label_info = f" labelled '{self.label_filter}'" if self.label_filter else ""
        label_hint = "  Backspace=back to labels" if self.label_filter else ""
        self.SetStatusText(
            f"{source} — {n_issues} issues, {n_prs} PRs ({self.state_filter}){label_info}. "
            f"Showing up to {self.current_limit} newest. "
            f"Ctrl++=view more  R=refresh  M=comment  F=favorite  Ctrl+F=filter"
            f"{label_hint}  "
            f"Mode={self.list_mode}"
            + self._filter_status_suffix()
        )
        self._update_title()
        if filtered:
            wx.CallLater(100, self._focus_list)

    def _on_git_items_loaded(self, token: int, items: list, kind: str) -> None:
        """Handle loaded git items (branches, commits, tags, releases, workflow runs)."""
        if not self._fetch_is_current(token):
            return  # the user has moved on; these belong to a view they left
        self.git_items = items
        self.items = []  # clear issues/PRs
        filtered = self._populate_filtered_list(items, use_favorite_prefix=True)
        # Build status text — include branch name for commits view
        branch_info = ""
        if self.view_mode == VIEW_COMMITS:
            branch_info = f" on {self.commit_branch}" if self.commit_branch else " on default branch"
        compare_hint = "  Ctrl+Shift+B=compare branches" if self.view_mode == VIEW_BRANCHES else ""
        if self.view_mode == VIEW_WORKFLOWS:
            compare_hint = "  Enter=run on branch"
        elif self.view_mode == VIEW_WORKFLOW:
            compare_hint = "  Enter=list artifacts  Delete/Ctrl+D=delete run"
        elif self.view_mode == VIEW_ARTIFACTS:
            compare_hint = "  Enter=download  Backspace=back to runs"
        elif self.view_mode == VIEW_RELEASES:
            compare_hint = "  Enter=list assets"
        elif self.view_mode == VIEW_ASSETS:
            compare_hint = "  Enter=download in browser  Backspace=back to releases"
        elif self.view_mode == VIEW_COMMITS:
            compare_hint = "  Backspace=back to branches"
        elif self.view_mode == VIEW_LABELS:
            compare_hint = (
                "  Enter=browse issues & PRs with it"
                "  Insert/Ctrl+I=new  Delete/Ctrl+D=remove"
            )
        # Download totals lead the status line where they are the point of the view
        totals = ""
        if self.view_mode == VIEW_RELEASES:
            totals = f" {total_downloads(items):,} downloads across them."
        elif self.view_mode == VIEW_ASSETS:
            totals = f" {sum(a.download_count for a in items):,} downloads in total."
        # Ctrl+B only picks a branch in the Commits view — offering it in the
        # tags, releases, or labels list is advertising a key that answers
        # "Select Branch is only available in Commits view."
        branch_hint = "  Ctrl+B=select branch" if self.view_mode == VIEW_COMMITS else ""
        self.SetStatusText(
            f"{self.repo} — {len(items)} {kind}{branch_info}.{totals} "
            f"Showing up to {self.current_limit}. "
            f"Ctrl++=view more  R=refresh{branch_hint}  Ctrl+F=filter{compare_hint}  "
            f"Mode={self.list_mode}"
            + self._filter_status_suffix()
        )
        self._update_title()
        if filtered:
            wx.CallLater(100, self._focus_list)

    def _focus_list(self) -> None:
        """Move keyboard focus to the list and select the first item."""
        self.list_ctrl.SetFocus()
        self.list_ctrl.Select(0, on=True)
        self.list_ctrl.Focus(0)
        self._show_details(0)

    def _on_items_error(self, msg: str) -> None:
        self.SetStatusText(f"Error: {msg}")
        self._update_title()

    def _on_fetch_error(self, token: int, msg: str) -> None:
        """Error from a list load — swallowed if that load is no longer current.

        A failure in a view you have already left is not worth replacing the
        status of the view you are now looking at.
        """
        if not self._fetch_is_current(token):
            return
        self._on_items_error(msg)

    # ── Details panel ──────────────────────────────────────────────────

    def _show_details(self, idx: int) -> None:
        """Show details for the item at idx in the details panel."""
        self._comment_positions = []
        self._current_comment = -1
        if self.view_mode == VIEW_ISSUES:
            self._show_issue_details(idx)
        elif self.view_mode == VIEW_FAVORITES:
            self._show_favorite_details(idx)
        else:
            self._show_git_details(idx)

    def _show_favorite_details(self, idx: int) -> None:
        """Show details for a favorited item in the details panel."""
        if idx < 0 or idx >= len(self.favorites):
            self.details_text.Clear()
            return
        fav = self.favorites[idx]
        lines = []
        lines.append(f"★ {fav.title}")
        lines.append(f"Type: {fav.item_type}")
        lines.append(f"Repo: {fav.repo}")
        if fav.subtitle:
            lines.append(f"Detail: {fav.subtitle}")
        if fav.added_at:
            lines.append(f"Favorited: {fav.added_at[:10]}")
        lines.append(f"URL: {fav.url}")
        lines.append("")
        lines.append("─" * 60)
        lines.append("")
        lines.append("Press Enter to open in browser.")
        lines.append("Press F to remove from favorites.")
        self.details_text.SetValue("\n".join(lines))

    def _show_issue_details(self, idx: int) -> None:
        """Show details for an issue/PR."""
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

    def _show_git_details(self, idx: int) -> None:
        """Show details for a git item (branch, commit, tag, release, workflow run)."""
        if idx < 0 or idx >= len(self.git_items):
            self.details_text.Clear()
            return
        item = self.git_items[idx]
        lines = []
        if isinstance(item, Branch):
            lines.append(f"Branch: {item.name}")
            lines.append(f"Last commit: {item.commit_sha}")
            lines.append(f"Message: {item.commit_message}")
            lines.append(f"Author: {item.commit_author}")
            lines.append(f"Date: {item.commit_date}")
            lines.append(f"Protected: {'Yes' if item.protected else 'No'}")
            if item.ahead:
                lines.append(f"Ahead: {item.ahead}")
            if item.behind:
                lines.append(f"Behind: {item.behind}")
            lines.append(f"URL: {item.url}")
        elif isinstance(item, Commit):
            lines.append(f"Commit: {item.sha}")
            lines.append(f"Short SHA: {item.short_sha}")
            branch = self.commit_branch if self.commit_branch else "default branch"
            lines.append(f"Branch: {branch}")
            lines.append(f"Author: {item.author}")
            lines.append(f"Date: {item.date}")
            lines.append(f"URL: {item.url}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            lines.append(item.message or "(no message)")
            if item.files:
                lines.append("")
                lines.append("─" * 60)
                lines.append(f"Files changed ({item.files_changed}):")
                lines.append("─" * 60)
                for f in item.files:
                    status = f.get("status", "")
                    fname = f.get("filename", "")
                    adds = f.get("additions", 0)
                    dels = f.get("deletions", 0)
                    lines.append(f"  {status}: {fname} (+{adds} -{dels})")
            if item.additions or item.deletions:
                lines.append("")
                lines.append(f"Total: +{item.additions} -{item.deletions} ({item.files_changed} files)")
        elif isinstance(item, Tag):
            lines.append(f"Tag: {item.name}")
            lines.append(f"Commit: {item.commit_sha}")
            lines.append(f"URL: {item.url}")
        elif isinstance(item, Label):
            lines.append(f"Label: {item.name}")
            lines.append(f"Description: {item.description or '(none)'}")
            lines.append(f"Colour: {'#' + item.color if item.color else '(none)'}")
            lines.append(f"Default label: {'Yes' if item.is_default else 'No'}")
            lines.append(f"URL: {item.url}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            lines.append("Keys, from the list or from here:")
            lines.append("")
            lines.append("  Enter             list the issues and PRs with this label")
            lines.append("  Insert or Ctrl+I  create a new label")
            lines.append(f"  Delete or Ctrl+D  delete '{item.name}' — GHManage asks first")
            lines.append("")
            lines.append("The Actions menu has all three.")
            lines.append("")
            lines.append("Deleting a label strips it from every issue and PR that")
            lines.append("has it, and GitHub offers no way to undo that.")
        elif isinstance(item, Release):
            lines.append(f"Release: {item.name}")
            lines.append(f"Tag: {item.tag}")
            lines.append(f"Date: {item.created_at}")
            lines.append(f"Draft: {'Yes' if item.draft else 'No'}")
            lines.append(f"Prerelease: {'Yes' if item.prerelease else 'No'}")
            lines.append(f"Downloads: {item.downloads:,} across {len(item.assets)} assets")
            lines.append(f"URL: {item.url}")
            if item.assets:
                lines.append("")
                lines.append("─" * 60)
                lines.append("Downloads by asset:")
                lines.append("─" * 60)
                # Most-downloaded first — the number is why you are looking here
                for a in sorted(item.assets, key=lambda x: x.download_count, reverse=True):
                    lines.append(f"  {a.download_count:>7,}  {a.name}  ({a.size_human()})")
                lines.append("")
                lines.append("Press Enter to open these assets as their own list.")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            lines.append(item.body or "(no release notes)")
        elif isinstance(item, Workflow):
            lines.append(f"Workflow: {item.name}")
            lines.append(f"State: {item.state}")
            lines.append(f"File: {item.path}")
            lines.append(f"ID: {item.id}")
            lines.append(f"URL: {item.url}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            lines.append("Press Enter to run this workflow on a branch you choose")
            lines.append("(only works if the workflow supports manual runs /")
            lines.append("workflow_dispatch). Right-click for the same option.")
        elif isinstance(item, WorkflowRun):
            lines.append(f"Workflow: {item.name}")
            lines.append(f"Run #: {item.run_number}")
            lines.append(f"Status: {item.status}")
            lines.append(f"Result: {item.conclusion or '(running)'}")
            lines.append(f"Branch: {item.branch}")
            lines.append(f"Event: {item.event}")
            lines.append(f"Date: {item.created_at}")
            lines.append(f"URL: {item.url}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            lines.append("Press Enter to list this run's artifacts.")
            lines.append("Delete or Ctrl+D deletes this run — GHManage asks first.")
        elif isinstance(item, Artifact):
            lines.append(f"Artifact: {item.name}")
            lines.append(f"Size: {item.size_human()}")
            lines.append(f"Expired: {'Yes' if item.expired else 'No'}")
            lines.append(f"Created: {item.created_at}")
            lines.append(f"ID: {item.id}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            if item.expired:
                lines.append("This artifact has expired and can no longer be downloaded.")
            else:
                lines.append("Press Enter to download this artifact into a folder you choose.")
            lines.append("Press Backspace to return to the workflow runs.")
        elif isinstance(item, ReleaseAsset):
            lines.append(f"Asset: {item.name}")
            lines.append(f"Downloads: {item.download_count:,}")
            lines.append(f"Size: {item.size_human()}")
            if item.release_tag:
                lines.append(f"Release: {item.release_tag}")
            lines.append(f"Updated: {item.updated_at}")
            lines.append(f"ID: {item.id}")
            lines.append(f"URL: {item.url}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")
            lines.append("The download count is a lifetime running total kept by GitHub.")
            lines.append("It is not broken down by date, and no API offers that — to see")
            lines.append("downloads over time you have to record these numbers yourself")
            lines.append("and compare them later.")
            lines.append("")
            lines.append("Press Enter to download this file in your browser.")
            lines.append("Press Backspace to return to the releases.")
        self.details_text.SetValue("\n".join(lines))

    # ── Helpers ─────────────────────────────────────────────────────────

    def _focused_item(self):
        """Return the currently focused item (issue/PR, git item, or favorite)."""
        idx = self.list_ctrl.GetFirstSelected()
        if idx < 0:
            return None
        if self.view_mode == VIEW_ISSUES:
            if idx < len(self.items):
                return self.items[idx]
        elif self.view_mode == VIEW_FAVORITES:
            if idx < len(self.favorites):
                return self.favorites[idx]
        else:
            if idx < len(self.git_items):
                return self.git_items[idx]
        return None

    def _announce(self, msg: str) -> None:
        """Update status bar (screen reader accessible)."""
        self.SetStatusText(msg)

    # ── List events ─────────────────────────────────────────────────────

    def on_item_selected(self, event: wx.ListEvent) -> None:
        idx = event.GetIndex()
        self._show_details(idx)
        if self.list_mode == "full":
            item = self._focused_item()
            if item:
                if isinstance(item, FavoriteEntry):
                    self._announce(
                        f"type: {item.item_type}, repo: {item.repo}, "
                        f"title: {item.title}, subtitle: {item.subtitle}"
                    )
                else:
                    self._announce(item.to_accessible_string(self.columns))

    def on_item_activated(self, event: wx.ListEvent) -> None:
        """Double-click or Enter — context-dependent action."""
        item = self._focused_item()
        if not item:
            return
        # In Branches view, Enter switches to Commits for that branch
        if self.view_mode == VIEW_BRANCHES and isinstance(item, Branch):
            self.commit_branch = item.name
            self._switch_view(VIEW_COMMITS)
            self._announce(f"Showing commits on branch {item.name}")
            return
        # In Labels view, Enter shows the issues and PRs carrying that label
        if self.view_mode == VIEW_LABELS and isinstance(item, Label):
            self._browse_label(item)
            return
        # In Workflows view, Enter offers to run the workflow on a branch
        if self.view_mode == VIEW_WORKFLOWS and isinstance(item, Workflow):
            self._run_workflow_flow(item)
            return
        # In Workflow Runs view, Enter drills into that run's artifacts
        if self.view_mode == VIEW_WORKFLOW and isinstance(item, WorkflowRun):
            self.artifacts_run = item
            self._switch_view(VIEW_ARTIFACTS)
            self._announce(f"Showing artifacts for run #{item.run_number} {item.name}")
            return
        # In Artifacts view, Enter downloads the selected artifact
        if self.view_mode == VIEW_ARTIFACTS and isinstance(item, Artifact):
            self._download_artifact_flow(item)
            return
        # In Releases view, Enter drills into that release's assets and their counts
        if self.view_mode == VIEW_RELEASES and isinstance(item, Release):
            if not item.assets:
                self._announce(f"{item.tag} has no assets attached")
                return
            self.assets_release = item
            self._switch_view(VIEW_ASSETS)
            self._announce(
                f"Showing {len(item.assets)} assets for {item.tag}, "
                f"{item.downloads:,} downloads in total"
            )
            return
        # In Favorites view, Enter opens in browser
        if self.view_mode == VIEW_FAVORITES and isinstance(item, FavoriteEntry):
            if item.url:
                webbrowser.open(item.url)
                self._announce(f"Opened {item.title} in browser")
            else:
                self._announce("No URL for this favorite")
            return
        # All other views: open in browser
        url = getattr(item, "url", "") or ""
        if url:
            webbrowser.open(url)
            label = getattr(item, "number", None) or getattr(item, "name", "") or getattr(item, "short_sha", "")
            self._announce(f"Opened {label} in browser")
        else:
            self._announce("No URL for this item")

    def on_item_context_menu(self, event: wx.ListEvent) -> None:
        """Right-click / Menu key — offer item-specific actions."""
        item = self._focused_item()
        if self.view_mode == VIEW_WORKFLOWS and isinstance(item, Workflow):
            menu = wx.Menu()
            menu.Append(ID_RUN_WORKFLOW, "Run on branch…")
            menu.Bind(
                wx.EVT_MENU,
                lambda evt, wf=item: self._run_workflow_flow(wf),
                id=ID_RUN_WORKFLOW,
            )
            self.list_ctrl.PopupMenu(menu)
            menu.Destroy()
        elif self.view_mode == VIEW_LABELS:
            menu = wx.Menu()
            if isinstance(item, Label):
                menu.Append(ID_BROWSE_LABEL, "Browse issues && PRs with this label")
                menu.Bind(
                    wx.EVT_MENU,
                    lambda evt, lb=item: self._browse_label(lb),
                    id=ID_BROWSE_LABEL,
                )
            menu.Append(ID_NEW_LABEL, "New label…")
            menu.Bind(wx.EVT_MENU, self.on_new_label, id=ID_NEW_LABEL)
            if isinstance(item, Label):
                menu.Append(ID_DELETE_LABEL, "Delete label…")
                menu.Bind(wx.EVT_MENU, self.on_delete_label, id=ID_DELETE_LABEL)
            self.list_ctrl.PopupMenu(menu)
            menu.Destroy()
        elif self.view_mode == VIEW_ARTIFACTS and isinstance(item, Artifact):
            menu = wx.Menu()
            dl = menu.Append(ID_DOWNLOAD_ARTIFACT, "Download…")
            dl.Enable(not item.expired)
            menu.Bind(
                wx.EVT_MENU,
                lambda evt, art=item: self._download_artifact_flow(art),
                id=ID_DOWNLOAD_ARTIFACT,
            )
            self.list_ctrl.PopupMenu(menu)
            menu.Destroy()

    # ── Run a workflow (workflow_dispatch) ──────────────────────────────

    def _run_workflow_flow(self, wf: "Workflow") -> None:
        """Start the 'run this workflow' flow.

        Branch first, then inputs. That order is deliberate and matches the web
        UI: a workflow's inputs are declared in the workflow file, so a branch
        that adds or changes an input has a different form from the default
        branch. Reading the file before the branch is known would show the
        wrong set of inputs and silently drop the values the user typed.

        Nothing is triggered until the user confirms.
        """
        if not self.repo:
            self._announce("No repository loaded.")
            return
        self._announce(f"Loading branches for {wf.name}…")

        def worker() -> None:
            try:
                names = [b.name for b in fetch_branches(self.repo, 200)]
                wx.CallAfter(self._on_workflow_branches_ready, wf, names)
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_workflow_branches_ready(self, wf: "Workflow", names: list[str]) -> None:
        """Ask which branch to run on, then read that branch's workflow file."""
        if not names:
            self._announce("No branches found to run against.")
            return
        dlg = wx.SingleChoiceDialog(
            self,
            f"Run '{wf.name}' on which branch?",
            "Run Workflow",
            names,
        )
        dlg.SetSelection(0)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            self._announce("Run cancelled.")
            return
        branch = dlg.GetStringSelection()
        dlg.Destroy()
        if not branch:
            return

        self._announce(f"Checking how {wf.name} can be run on {branch}…")

        def worker() -> None:
            try:
                spec = fetch_dispatch_spec(self.repo, wf.path, branch)
                wx.CallAfter(self._on_workflow_dispatch_ready, wf, branch, spec)
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_workflow_dispatch_ready(
        self, wf: "Workflow", branch: str, spec: "DispatchSpec"
    ) -> None:
        """Collect inputs if the workflow declares any, then dispatch."""
        if not spec.supports_dispatch:
            msg = (
                f"'{wf.name}' can't be run manually because it doesn't declare a "
                f"workflow_dispatch trigger on {branch}.\n\n"
                "Add `on: workflow_dispatch` to the workflow file to enable "
                "manual runs and branch selection."
            )
            self._announce(f"{wf.name} doesn't support manual runs on {branch}.")
            wx.MessageBox(msg, "Run Workflow", wx.OK | wx.ICON_INFORMATION, self)
            return

        # No inputs declared: nothing to ask, so don't put an empty dialog in
        # the way — this is the original behaviour and stays unchanged.
        if not spec.inputs:
            self._dispatch_workflow(wf, branch, {})
            return

        dlg = WorkflowInputsDialog(self, wf.name, branch, spec.inputs)
        if dlg.ShowModal() == wx.ID_OK:
            values = dlg.values()
            dlg.Destroy()
            self._dispatch_workflow(wf, branch, values)
        else:
            dlg.Destroy()
            self._announce("Run cancelled.")

    def _dispatch_workflow(
        self, wf: "Workflow", branch: str, inputs: dict[str, str]
    ) -> None:
        """Trigger the workflow on ``branch`` in the background."""
        summary = ", ".join(f"{k}={v}" for k, v in inputs.items())
        self._announce(
            f"Starting '{wf.name}' on {branch}"
            + (f" with {summary}…" if summary else "…")
        )

        def worker() -> None:
            try:
                dispatch_workflow(self.repo, wf.id, branch, inputs)
                wx.CallAfter(
                    self._announce,
                    f"Started '{wf.name}' on {branch}"
                    + (f" with {summary}. " if summary else ". ")
                    + "Switch to Workflow Runs and refresh to watch it.",
                )
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    # ── Download an artifact ────────────────────────────────────────────

    def _download_artifact_flow(self, art: "Artifact") -> None:
        """Prompt for a destination folder, then download the artifact into it."""
        if not self.repo:
            self._announce("No repository loaded.")
            return
        if art.expired:
            self._announce(f"'{art.name}' has expired and can't be downloaded.")
            wx.MessageBox(
                f"'{art.name}' has expired and can no longer be downloaded.",
                "Download Artifact",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        dlg = wx.DirDialog(
            self,
            f"Choose a folder to download '{art.name}' into",
            style=wx.DD_DEFAULT_STYLE,
        )
        if dlg.ShowModal() == wx.ID_OK:
            dest = dlg.GetPath()
            dlg.Destroy()
            self._do_download_artifact(art, dest)
        else:
            dlg.Destroy()
            self._announce("Download cancelled.")

    def _do_download_artifact(self, art: "Artifact", dest: str) -> None:
        """Download ``art`` into ``dest`` in the background."""
        run_id = art.run_id or (self.artifacts_run.run_id if self.artifacts_run else 0)
        self._announce(f"Downloading '{art.name}'…")

        def worker() -> None:
            try:
                download_artifact(self.repo, run_id, art.name, dest)
                wx.CallAfter(
                    self._announce,
                    f"Downloaded '{art.name}' into {dest}.",
                )
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def on_char_hook(self, event: wx.KeyEvent) -> None:
        """Frame-wide keys that must not depend on which pane has focus.

        The bare Insert and Delete keys are handled here rather than in
        ``on_list_key_down`` so they work from the details panel too — that panel
        is where the text describing them is read. They cannot be menu
        accelerators: a bare Delete accelerator would swallow the Delete key
        everywhere in the window. Their Ctrl+I / Ctrl+D twins in the Actions menu
        are ordinary accelerators, which is why those need nothing here.

        Everything else is skipped, so the focused control keeps first claim on
        its own keys.
        """
        # Not from the repository list: Delete there reads as "remove this
        # repo", and acting on the item list from another pane is a surprise.
        if self.FindFocus() is self.repo_list:
            event.Skip()
            return
        key = event.GetKeyCode()
        if key == wx.WXK_INSERT and self.view_mode == VIEW_LABELS:
            self._do_new_label()
            return
        if key == wx.WXK_DELETE and self.view_mode in (VIEW_LABELS, VIEW_WORKFLOW):
            self._delete_focused_item()
            return
        event.Skip()

    def on_list_key_down(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._clear_filter()
        elif key == ord("F"):
            self._toggle_favorite()
        elif key == ord("R"):
            if self.view_mode == VIEW_FAVORITES:
                self._load_favorites_view()
            else:
                self._load_items()
        elif key == wx.WXK_BACK and self.view_mode in PARENT_VIEW:
            # Backspace steps back up a drill-down (artifacts -> runs, commits -> branches)
            parent = PARENT_VIEW[self.view_mode]
            self._switch_view(parent)
            self._announce(f"Back to {self._VIEW_LABELS.get(parent, parent).lower()}")
        elif key == wx.WXK_BACK and self.view_mode == VIEW_ISSUES and self.label_filter:
            # Issues restricted to a label is a drill-down too, even though the
            # view mode is the same one you reach with Ctrl+1.
            self._switch_view(VIEW_LABELS)
            self._announce("Back to labels")
        elif self.view_mode == VIEW_ISSUES:
            # Issue/PR-specific keys
            if key == ord("C"):
                self._do_close()
            elif key == ord("O"):
                self._do_reopen()
            elif key == ord("M"):
                self._do_comment()
            else:
                event.Skip()
        else:
            event.Skip()

    def _toggle_favorite(self) -> None:
        """Toggle favorite status on the currently focused item (F key)."""
        item = self._focused_item()
        if not item:
            return

        # In the favorites view, F unfavorites the item
        if self.view_mode == VIEW_FAVORITES and isinstance(item, FavoriteEntry):
            self.favorites = [f for f in self.favorites if f.url != item.url]
            save_favorites(self.favorites)
            self._announce(f"Removed '{item.title}' from favorites")
            self._load_favorites_view()
            self._refresh_repo_list_fav_count()
            return

        # In other views, F toggles favorite on the current item
        url = getattr(item, "url", "") or ""
        if not url:
            self._announce("No URL for this item — can't favorite.")
            return

        entry = self._build_favorite_entry(item)
        if entry is None:
            self._announce("Can't determine item type for favorite.")
            return

        self.favorites, was_added = toggle_favorite(entry, self.favorites)
        if was_added:
            self._announce(f"★ Added '{entry.title}' to favorites")
        else:
            self._announce(f"Removed '{entry.title}' from favorites")
        self._refresh_repo_list_fav_count()

    def _build_favorite_entry(self, item) -> FavoriteEntry | None:
        """Build a FavoriteEntry from any item type (Item, Branch, Commit, etc.)."""
        url = getattr(item, "url", "") or ""
        repo = self.repo or ""
        if isinstance(item, Item):
            item_type = "PR" if item.is_pr else "issue"
            title = f"#{item.number} — {item.title}"
            subtitle = item.state_display
        elif isinstance(item, Branch):
            item_type = "branch"
            title = item.name
            subtitle = item.commit_message[:60] if item.commit_message else ""
        elif isinstance(item, Commit):
            item_type = "commit"
            title = item.short_sha
            subtitle = item.message[:60] if item.message else ""
        elif isinstance(item, Tag):
            item_type = "tag"
            title = item.name
            subtitle = item.commit_sha
        elif isinstance(item, Label):
            item_type = "label"
            title = item.name
            subtitle = item.description[:60] if item.description else ""
        elif isinstance(item, Release):
            item_type = "release"
            title = item.tag
            subtitle = item.name
        elif isinstance(item, Workflow):
            item_type = "workflow"
            title = item.name
            subtitle = f"{item.state} — {item.path}"
        elif isinstance(item, WorkflowRun):
            item_type = "workflow run"
            title = f"#{item.run_number} {item.name}"
            subtitle = f"{item.conclusion or item.status} on {item.branch}"
        else:
            return None

        from datetime import datetime
        return FavoriteEntry(
            repo=repo,
            item_type=item_type,
            url=url,
            title=title,
            subtitle=subtitle,
            added_at=datetime.now().isoformat(timespec="seconds"),
        )

    def _refresh_repo_list_fav_count(self) -> None:
        """Update the ★ Favorites count in the repo list without full reload."""
        for i in range(self.repo_list.GetCount()):
            data = self.repo_list.GetClientData(i)
            if data == "__favorites__":
                n = len(self.favorites)
                label = f"★ Favorites ({n})" if n else "★ Favorites"
                self.repo_list.SetString(i, label)
                break

    def on_details_key_down(self, event: wx.KeyEvent) -> None:
        """Pass key events through — comment navigation is handled via Alt+N/Alt+P menu accelerators."""
        event.Skip()

    def on_next_comment(self, event: wx.CommandEvent) -> None:
        """Alt+N — jump to the next comment in the details box."""
        self._navigate_comment(1)

    def on_prev_comment(self, event: wx.CommandEvent) -> None:
        """Alt+P — jump to the previous comment in the details box."""
        self._navigate_comment(-1)

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
            self.current_limit = self.page_size  # reset to first page
            self._load_items()

    def on_view_more(self, event: wx.CommandEvent) -> None:
        """Increase the fetch limit and reload to show more items."""
        if not self.repo:
            return
        self.current_limit += self.page_size
        self._load_items()

    def on_open_browser(self, event: wx.CommandEvent) -> None:
        item = self._focused_item()
        if not item:
            return
        url = getattr(item, "url", "") or ""
        if url:
            webbrowser.open(url)
            if isinstance(item, FavoriteEntry):
                self._announce(f"Opened {item.title} in browser")
            else:
                label = getattr(item, "number", None) or getattr(item, "name", "") or getattr(item, "short_sha", "")
                self._announce(f"Opened {label} in browser")
        else:
            self._announce("No URL for this item")

    def on_close_item(self, event: wx.CommandEvent) -> None:
        self._do_close()

    def on_reopen(self, event: wx.CommandEvent) -> None:
        self._do_reopen()

    def on_comment(self, event: wx.CommandEvent) -> None:
        self._do_comment()

    def on_open_repo(self, event: wx.CommandEvent) -> None:
        """Ctrl+Shift+O — open any repo by URL or OWNER/NAME without cloning."""
        dlg = wx.TextEntryDialog(
            self,
            "Enter a GitHub repository URL or OWNER/NAME\n"
            "(e.g. https://github.com/Community-Access/quill or Community-Access/quill)",
            "Open Repository",
            "",
        )
        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.GetValue().strip()
            dlg.Destroy()
            if not value:
                return
            repo = _parse_repo_spec(value)
            if not repo:
                self._announce(
                    "Couldn't parse that. Use a github.com URL or OWNER/NAME."
                )
                return
            # Pin it so it shows in the left list across sessions
            self._pinned_repos = add_pinned(repo)
            self._refresh_repo_list()
            self._select_repo(repo)
        else:
            dlg.Destroy()

    def on_remove_repo(self, event: wx.CommandEvent) -> None:
        """Remove the currently selected repo from the pinned list."""
        idx = self.repo_list.GetSelection()
        if idx == wx.NOT_FOUND:
            self._announce("Select a repository in the list first.")
            return
        name = self.repo_list.GetClientData(idx)
        if not name:
            return
        if name not in self._pinned_repos:
            self._announce(
                f"{name} is one of your own repositories and can't be removed from here."
            )
            return
        self._pinned_repos = remove_pinned(name)
        self._refresh_repo_list()
        self._announce(f"Removed {name} from the pinned list.")

    def _refresh_repo_list(self) -> None:
        """Rebuild the repo list from cached gh results + current pinned repos."""
        self._on_repos_loaded(self._all_repos)

    def on_goto(self, event: wx.CommandEvent) -> None:
        """Ctrl+G — open a dialog to jump to a specific issue/PR by number."""
        if self.view_mode != VIEW_ISSUES:
            self._announce("Go To is only available in Issues & PRs view.")
            return
        if not self.items:
            self._announce("No items loaded. Load a repository first.")
            return
        dlg = wx.NumberEntryDialog(
            self,
            "Enter the issue or PR number:",
            "Go To Issue #",
            "Go To Issue",
            1,
            1,
            1000000,
        )
        if dlg.ShowModal() == wx.ID_OK:
            number = dlg.GetValue()
            self._goto_issue(number)
        dlg.Destroy()

    def on_filter(self, event: wx.CommandEvent) -> None:
        """Ctrl+F — quick filter the current list by text across all columns."""
        dlg = wx.TextEntryDialog(
            self,
            "Filter the current list (case-insensitive).\n"
            "Matches against all visible columns.\n"
            "Leave empty to clear the filter.",
            "Quick Filter",
            self.filter_text,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.filter_text = dlg.GetValue().strip()
            self._refresh_list_display()
            if self.filter_text:
                self._announce(f"Filter: '{self.filter_text}' applied")
            else:
                self._announce("Filter cleared")
        dlg.Destroy()

    def _clear_filter(self) -> None:
        """Clear the quick filter and refresh the display."""
        if not self.filter_text:
            self._announce("No filter active.")
            return
        self.filter_text = ""
        self._refresh_list_display()
        self._announce("Filter cleared")

    def _matches_filter(self, item) -> bool:
        """Return True if the item matches the current filter text (or no filter)."""
        if not self.filter_text:
            return True
        needle = self.filter_text.lower()
        if isinstance(item, FavoriteEntry):
            haystack = " ".join([
                item.item_type, item.repo, item.title, item.subtitle,
            ]).lower()
            return needle in haystack
        row = item.to_row(self.columns)
        haystack = " ".join(str(v) for v in row.values()).lower()
        return needle in haystack

    def _filtered_items(self) -> list:
        """Return the filtered list for the current view mode."""
        if self.view_mode == VIEW_ISSUES:
            return [it for it in self.items if self._matches_filter(it)]
        elif self.view_mode == VIEW_FAVORITES:
            return [fav for fav in self.favorites if self._matches_filter(fav)]
        else:
            return [it for it in self.git_items if self._matches_filter(it)]

    def _filter_status_suffix(self) -> str:
        """Return a status-bar fragment showing the filter state."""
        if not self.filter_text:
            return ""
        total = len(self.items) if self.view_mode == VIEW_ISSUES else (
            len(self.favorites) if self.view_mode == VIEW_FAVORITES else len(self.git_items)
        )
        shown = len(self._filtered_items())
        return f"  Filter: '{self.filter_text}' ({shown}/{total})"

    def _goto_issue(self, number: int) -> None:
        """Select the item with the given number and focus the details box.

        If the item isn't in the currently loaded list (e.g. it's closed, or
        beyond the fetch limit), it's fetched on-demand via ``gh`` and inserted
        into the list so the user can still view it.
        """
        for i, item in enumerate(self.items):
            if item.number == number:
                self.list_ctrl.SetFocus()
                self.list_ctrl.Select(i, on=True)
                self.list_ctrl.Focus(i)
                self._show_details(i)
                # Move focus to the details box so user can read/navigate comments
                wx.CallLater(100, self.details_text.SetFocus)
                self._announce(f"Jumped to #{number} — {item.title}")
                return
        # Not in the current list — fetch it on-demand in the background
        self._announce(f"#{number} not in current list, fetching…")

        def worker() -> None:
            try:
                item = fetch_item_by_number(number, self.repo)
            except GhError as exc:
                wx.CallAfter(self._goto_error, number, str(exc))
                return
            wx.CallAfter(self._on_goto_fetched, item, number)

        threading.Thread(target=worker, daemon=True).start()

    def _goto_error(self, number: int, msg: str) -> None:
        """Show an error dialog when a Go To fetch fails."""
        self._announce(f"Error fetching #{number}: {msg}")
        wx.MessageBox(
            f"Could not fetch #{number}:\n{msg}",
            "Go To Error",
            wx.OK | wx.ICON_WARNING,
            self,
        )

    def _on_goto_fetched(self, item: Optional[Item], number: int) -> None:
        """Called when an on-demand fetch for Go To completes."""
        # Go To inserts into the issues list. If the view moved on while the
        # fetch was running, that list is not what is on screen any more.
        if self.view_mode != VIEW_ISSUES:
            self._announce(f"Left the issues list before #{number} arrived.")
            return
        if item is None:
            self._announce(f"#{number} not found in {self.repo}.")
            wx.MessageBox(
                f"#{number} does not exist as an issue or PR in {self.repo}.",
                "Not Found",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        # Insert the fetched item into the list and select it
        self.items.append(item)
        self.items = sort_items(self.items, self.sort_order)
        idx = next((i for i, it in enumerate(self.items) if it.number == number), -1)
        if idx < 0:
            self._announce(f"#{number} could not be added to the list.")
            return
        # Rebuild the list ctrl to reflect the new sorted order
        self._populate_filtered_list(self.items, use_favorite_prefix=True)
        self.list_ctrl.SetFocus()
        self.list_ctrl.Select(idx, on=True)
        self.list_ctrl.Focus(idx)
        self._show_details(idx)
        wx.CallLater(100, self.details_text.SetFocus)
        self._announce(f"Jumped to #{number} — {item.title}")

    def on_select_branch(self, event: wx.CommandEvent) -> None:
        """Ctrl+B — select which branch to view commits for."""
        if self.view_mode != VIEW_COMMITS:
            self._announce("Select Branch is only available in Commits view.")
            return
        if not self.repo:
            self._announce("No repository loaded.")
            return
        # Fetch branch names in background, then show a selection dialog
        self._announce("Loading branches…")

        def worker() -> None:
            try:
                branches = fetch_branches(self.repo, 200)
                names = [b.name for b in branches]
                wx.CallAfter(self._show_branch_picker, names)
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _show_branch_picker(self, names: list[str]) -> None:
        """Show a dialog to pick a branch for the commits view."""
        if not names:
            self._announce("No branches found.")
            return
        current = self.commit_branch if self.commit_branch else names[0]
        dlg = wx.SingleChoiceDialog(
            self,
            "Select a branch to view commits:",
            "Select Branch",
            names,
        )
        # Try to pre-select the current branch
        if current in names:
            dlg.SetSelection(names.index(current))
        if dlg.ShowModal() == wx.ID_OK:
            selected = dlg.GetStringSelection()
            dlg.Destroy()
            if selected and selected != self.commit_branch:
                self.commit_branch = selected
                self.current_limit = self.page_size
                self._load_items()
                self._announce(f"Showing commits on branch {selected}")
        else:
            dlg.Destroy()

    def on_compare_branches(self, event: wx.CommandEvent) -> None:
        """Ctrl+Shift+B — compare two branches (ahead/behind, commits, files)."""
        if not self.repo:
            self._announce("No repository loaded.")
            return
        # Fetch branch names in the background, then run the pickers.
        self._announce("Loading branches for comparison…")

        def worker() -> None:
            try:
                branches = fetch_branches(self.repo, 200)
                names = [b.name for b in branches]
                wx.CallAfter(self._show_compare_pickers, names)
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _show_compare_pickers(self, names: list[str]) -> None:
        """Pick the base and head branches via two accessible dialogs."""
        if not names:
            self._announce("No branches found to compare.")
            return
        if len(names) < 2:
            self._announce("Need at least two branches to compare.")
            return

        # Sensible defaults: head = the branch currently focused (if any),
        # base = the first branch (usually the repo's default branch).
        focused = self._focused_item()
        head_default = focused.name if isinstance(focused, Branch) else names[1]

        # Step 1 — base branch (compare FROM).
        base_dlg = wx.SingleChoiceDialog(
            self,
            "Step 1 of 2 — choose the BASE branch (compare FROM, e.g. main):",
            "Compare Branches — Base",
            names,
        )
        base_dlg.SetSelection(0)
        if base_dlg.ShowModal() != wx.ID_OK:
            base_dlg.Destroy()
            self._announce("Compare cancelled.")
            return
        base = base_dlg.GetStringSelection()
        base_dlg.Destroy()

        # Step 2 — head branch (compare TO).
        head_dlg = wx.SingleChoiceDialog(
            self,
            f"Step 2 of 2 — choose the HEAD branch to compare against '{base}' "
            "(compare TO):",
            "Compare Branches — Head",
            names,
        )
        if head_default in names:
            head_dlg.SetSelection(names.index(head_default))
        if head_dlg.ShowModal() != wx.ID_OK:
            head_dlg.Destroy()
            self._announce("Compare cancelled.")
            return
        head = head_dlg.GetStringSelection()
        head_dlg.Destroy()

        if base == head:
            self._announce("Base and head are the same branch — nothing to compare.")
            wx.MessageBox(
                "Pick two different branches to compare.",
                "Compare Branches",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        self._run_compare(base, head)

    def _run_compare(self, base: str, head: str) -> None:
        """Fetch the comparison in the background and show the result."""
        self._announce(f"Comparing {base}…{head}…")

        def worker() -> None:
            try:
                result = fetch_compare(self.repo, base, head)
                wx.CallAfter(self._show_compare_result, result)
            except GhError as exc:
                wx.CallAfter(self._on_items_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _show_compare_result(self, result: CompareResult) -> None:
        """Display a branch comparison in an accessible, focusable text dialog."""
        text = self._format_compare(result)
        summary = (
            f"identical to '{result.base}'"
            if result.ahead_by == 0 and result.behind_by == 0
            else f"{result.ahead_by} ahead, {result.behind_by} behind '{result.base}'"
        )
        self._announce(f"'{result.head}' is {summary}.")
        self._show_text_dialog(
            f"Compare: {result.base} … {result.head}", text
        )

    def _format_compare(self, r: CompareResult) -> str:
        """Render a CompareResult as readable, screen-reader-friendly text."""
        sep = "─" * 60
        lines = [
            f"Comparing branches in {self.repo or 'this repository'}",
            "",
            f"Base (compare from): {r.base}",
            f"Head (compare to):   {r.head}",
            "",
        ]
        if r.ahead_by == 0 and r.behind_by == 0:
            lines.append(f"'{r.head}' and '{r.base}' are identical — no differences.")
            return "\n".join(lines)
        lines += [
            f"'{r.head}' is {r.ahead_by} commit(s) AHEAD of '{r.base}' "
            f"and {r.behind_by} commit(s) BEHIND.",
            "",
            f"  Ahead {r.ahead_by}: commits on '{r.head}' not on '{r.base}'.",
            f"  Behind {r.behind_by}: commits on '{r.base}' not on '{r.head}'.",
            "",
            sep,
        ]
        shown = len(r.commits)
        if r.ahead_by > shown:
            lines.append(f"Commits added on '{r.head}' (showing {shown} of {r.ahead_by}):")
        else:
            lines.append(f"Commits added on '{r.head}' ({shown}):")
        lines.append(sep)
        if r.commits:
            for c in r.commits:
                sha = (c.get("sha") or "")[:8]
                msg = c.get("message") or ""
                first_line = msg.splitlines()[0] if msg else ""
                lines.append(f"  {sha}  {first_line}")
        else:
            lines.append("  (none)")
        lines += ["", sep]
        total_add = sum(f.get("additions", 0) for f in r.files)
        total_del = sum(f.get("deletions", 0) for f in r.files)
        lines.append(f"Files changed ({len(r.files)}):")
        lines.append(sep)
        if r.files:
            for f in r.files:
                status = f.get("status", "")
                fname = f.get("filename", "")
                adds = f.get("additions", 0)
                dels = f.get("deletions", 0)
                lines.append(f"  {status}: {fname} (+{adds} -{dels})")
            if len(r.files) >= 100:
                lines.append("  … (file list capped at 100)")
            lines += ["", f"Total: +{total_add} -{total_del} across {len(r.files)} file(s)"]
        else:
            lines.append("  (none)")
        return "\n".join(lines)

    def _show_text_dialog(self, title: str, text: str) -> None:
        """Show read-only, focusable, scrollable text in a modal dialog.

        Used for content a screen reader needs to navigate line by line
        (e.g. a branch comparison). The text control receives focus so the
        user lands directly on the content.
        """
        dlg = wx.Dialog(
            self, title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(680, 500),
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        txt = wx.TextCtrl(
            dlg, value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        txt.SetName(title)
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 8)
        btn_sizer = dlg.CreateButtonSizer(wx.OK)
        if btn_sizer:
            sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)
        dlg.SetSizer(sizer)
        txt.SetInsertionPoint(0)
        wx.CallAfter(txt.SetFocus)
        dlg.ShowModal()
        dlg.Destroy()

    def on_quit(self, event: wx.CommandEvent) -> None:
        # A downloaded update is left staged: updater.bootstrap() applies it on
        # the next launch, before any window appears. Applying here instead
        # would mean racing our own shutdown for a lock on the install dir.
        self.Destroy()

    # ── View menu actions ───────────────────────────────────────────────

    def on_quick_mode(self, event: wx.CommandEvent) -> None:
        self.list_mode = "quick"
        self._update_menu_checks()
        self._announce("Quick mode: compact display")
        if self.items or self.git_items:
            self._refresh_list_display()

    def on_full_mode(self, event: wx.CommandEvent) -> None:
        self.list_mode = "full"
        self._update_menu_checks()
        self._announce("Full mode: field names included for screen reader")
        if self.items or self.git_items:
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
            self.current_limit = self.page_size
            self._load_items()

    def on_state_closed(self, event: wx.CommandEvent) -> None:
        self.state_filter = "closed"
        self._update_menu_checks()
        if self.repo:
            self.current_limit = self.page_size
            self._load_items()

    def on_state_all(self, event: wx.CommandEvent) -> None:
        self.state_filter = "all"
        self._update_menu_checks()
        if self.repo:
            self.current_limit = self.page_size
            self._load_items()

    def on_tab_issues(self, event: wx.CommandEvent) -> None:
        self.tab_filter = "issues"
        self._update_menu_checks()
        if self.repo:
            self.current_limit = self.page_size
            self._load_items()

    def on_tab_prs(self, event: wx.CommandEvent) -> None:
        self.tab_filter = "prs"
        self._update_menu_checks()
        if self.repo:
            self.current_limit = self.page_size
            self._load_items()

    def on_tab_both(self, event: wx.CommandEvent) -> None:
        self.tab_filter = "both"
        self._update_menu_checks()
        if self.repo:
            self.current_limit = self.page_size
            self._load_items()

    # ── View mode switching (Show submenu) ──────────────────────────────

    def on_view_issues(self, event: wx.CommandEvent) -> None:
        # Asking for Issues & PRs by name means all of them: drop any label
        # drill-down, including when that leaves the view mode unchanged.
        if self.view_mode == VIEW_ISSUES:
            if self.label_filter:
                self.label_filter = ""
                self.current_limit = self.page_size
                self._load_items()
                self._announce("Showing all issues and PRs")
            return
        self.label_filter = ""
        self._switch_view(VIEW_ISSUES)

    def on_view_branches(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_BRANCHES)

    def on_view_commits(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_COMMITS)

    def on_view_tags(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_TAGS)

    def on_view_releases(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_RELEASES)

    def on_view_workflows(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_WORKFLOWS)

    def on_view_workflow(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_WORKFLOW)

    def on_view_labels(self, event: wx.CommandEvent) -> None:
        self._switch_view(VIEW_LABELS)

    def on_view_favorites(self, event: wx.CommandEvent) -> None:
        self._select_favorites()

    # ── List display refresh ───────────────────────────────────────────

    def _refresh_list_display(self) -> None:
        """Re-populate the list from current data without re-fetching."""
        if self.view_mode == VIEW_FAVORITES:
            self._load_favorites_view()
            return
        items = self.items if self.view_mode == VIEW_ISSUES else self.git_items
        filtered = self._populate_filtered_list(items, use_favorite_prefix=True)
        if filtered:
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

    # ── Labels ──────────────────────────────────────────────────────────

    def _browse_label(self, label: "Label") -> None:
        """Show the issues and PRs carrying ``label``.

        This reuses the Issues & PRs view rather than inventing a new one, so
        the state filter, columns, sorting, and every issue action still work.
        The restriction is applied by `gh`, not by the quick filter, so it
        finds items that were never on the current page.
        """
        self.label_filter = label.name
        self.current_limit = self.page_size
        if self.view_mode == VIEW_ISSUES:
            self._load_items()
        else:
            self._switch_view(VIEW_ISSUES)
        self._announce(
            f"Showing issues and PRs labelled '{label.name}'. "
            "Backspace returns to the labels."
        )

    def on_new_label(self, event: wx.CommandEvent) -> None:
        self._do_new_label()

    def on_delete_label(self, event: wx.CommandEvent) -> None:
        self._do_delete_label()

    def on_delete_item(self, event: wx.CommandEvent) -> None:
        """Actions ▸ Delete (Ctrl+D) — deletes whatever this view can delete."""
        self._delete_focused_item()

    def on_act_run_workflow(self, event: wx.CommandEvent) -> None:
        item = self._focused_item()
        if isinstance(item, Workflow):
            self._run_workflow_flow(item)
        else:
            self._announce("Select a workflow first.")

    def on_act_download_artifact(self, event: wx.CommandEvent) -> None:
        item = self._focused_item()
        if isinstance(item, Artifact):
            self._download_artifact_flow(item)
        else:
            self._announce("Select an artifact first.")

    def _delete_focused_item(self) -> None:
        """Route Delete/Ctrl+D to the deletion this view supports.

        One entry point for the key and the menu item, so the two can never
        disagree about what Delete means in a given view.
        """
        if self.view_mode == VIEW_LABELS:
            self._do_delete_label()
        elif self.view_mode == VIEW_WORKFLOW:
            self._do_delete_run()
        else:
            self._announce(
                "Nothing here can be deleted. Labels and workflow runs can."
            )

    def _do_new_label(self) -> None:
        """Create a label (Insert in the Labels view, or the File menu)."""
        if not self.repo:
            self._announce("Select a repository first.")
            return
        dlg = NewLabelDialog(self, self.repo)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            self._announce("New label cancelled.")
            return
        name, color, description = dlg.values()
        dlg.Destroy()
        self._announce(f"Creating label '{name}'…")

        def worker() -> None:
            try:
                create_label(self.repo, name, color, description)
                wx.CallAfter(self._on_label_action_done, f"Created label '{name}'")
            except GhError as exc:
                wx.CallAfter(
                    self._on_action_error, f"Error creating label '{name}': {exc}"
                )

        threading.Thread(target=worker, daemon=True).start()

    def _do_delete_label(self) -> None:
        """Delete the focused label (Delete in the Labels view, or the File menu)."""
        if self.view_mode != VIEW_LABELS:
            self._announce("Switch to the Labels view to delete a label (Ctrl+8).")
            return
        item = self._focused_item()
        if not isinstance(item, Label):
            self._announce("Select a label first.")
            return
        confirm = wx.MessageBox(
            f"Delete the label '{item.name}'?\n\n"
            f"{item.description or '(no description)'}\n\n"
            "It will be removed from every issue and pull request that carries "
            "it. This cannot be undone.",
            "Confirm Delete Label",
            wx.YES_NO | wx.ICON_WARNING,
            self,
        )
        if confirm != wx.YES:
            return
        name = item.name
        self._announce(f"Deleting label '{name}'…")

        def worker() -> None:
            try:
                delete_label(self.repo, name)
                wx.CallAfter(self._on_label_action_done, f"Deleted label '{name}'")
            except GhError as exc:
                wx.CallAfter(
                    self._on_action_error, f"Error deleting label '{name}': {exc}"
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_label_action_done(self, msg: str) -> None:
        """Refresh the labels list after a create/delete.

        Separate from ``_on_action_done`` because that one refreshes whatever
        view is current, and a label can be created from anywhere via the File
        menu — refreshing the Releases list after creating a label would be a
        surprise, and would hide the label that was just made.
        """
        self._announce(f"{msg}. Refreshing labels…")
        if self.view_mode == VIEW_LABELS:
            self._load_items()
        else:
            self._switch_view(VIEW_LABELS)

    def _do_delete_run(self) -> None:
        """Delete the focused workflow run (Delete key in Workflow view)."""
        item = self._focused_item()
        if not item or not isinstance(item, WorkflowRun):
            return
        confirm = wx.MessageBox(
            f"Delete workflow run #{item.run_number}?\n\n{item.name} "
            f"({item.conclusion or item.status} on {item.branch})\n\n"
            "This cannot be undone.",
            "Confirm Delete Run",
            wx.YES_NO | wx.ICON_WARNING,
            self,
        )
        if confirm != wx.YES:
            return
        self._announce(f"Deleting run #{item.run_number}…")

        run_id = item.run_id
        run_number = item.run_number

        def worker() -> None:
            try:
                delete_workflow_run(self.repo, run_id)
                wx.CallAfter(self._on_action_done, f"Deleted run #{run_number}")
            except GhError as exc:
                wx.CallAfter(self._on_action_error, f"Error deleting run #{run_number}: {exc}")

        threading.Thread(target=worker, daemon=True).start()


# ── Entry point ────────────────────────────────────────────────────────


def main() -> None:
    # Must run before argparse: Velopack relaunches the app with its own hook
    # arguments during install/update/uninstall, and this handles and exits.
    updater.bootstrap()

    parser = argparse.ArgumentParser(
        description="GUI viewer and manager for GitHub issues and pull requests."
    )
    parser.add_argument(
        "--repo",
        metavar="OWNER/NAME",
        default=None,
        help="GitHub repository (owner/name). Skips the repo chooser.",
    )
    parser.add_argument(
        "--update-feed",
        metavar="DIR",
        default=None,
        help="Check this local folder of vpk output for updates instead of "
             "GitHub Releases (for testing the update cycle offline).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GHManage {APP_VERSION}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Write verbose update logging to the update log.",
    )
    args = parser.parse_args()

    updater.configure_logging(debug=args.debug)
    service = updater.UpdateService(APP_VERSION, feed=args.update_feed)

    app = wx.App(False)
    GhViewerFrame(repo=args.repo, update_service=service)
    app.MainLoop()


if __name__ == "__main__":
    main()