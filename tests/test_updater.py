"""The self-updater, with Velopack replaced by a fake."""

from __future__ import annotations

import sys
import types

import pytest

import updater


class FakeManager:
    def __init__(self, source, *, portable=False, update=None, check_error=None,
                 download_error=None, apply_error=None):
        self.source = source
        self.portable = portable
        self.update = update
        self.check_error = check_error
        self.download_error = download_error
        self.apply_error = apply_error
        self.applied = None

    def get_is_portable(self):
        return self.portable

    def get_current_version(self):
        return "0.8.0"

    def check_for_updates(self):
        if self.check_error:
            raise self.check_error
        return self.update

    def download_updates(self, update):
        if self.download_error:
            raise self.download_error

    def apply_updates_and_restart_with_args(self, update, args):
        if self.apply_error:
            raise self.apply_error
        self.applied = (update, args)


def _update(version="9.9.9"):
    return types.SimpleNamespace(TargetFullRelease=types.SimpleNamespace(Version=version))


class FakeVelopack:
    """What the fake velopack module builds. Set ``config`` before the first
    check; each UpdateManager it makes lands in ``made``."""

    def __init__(self) -> None:
        self.config: dict = {}
        self.made: list[FakeManager] = []

    def service(self, feed=None, **config) -> updater.UpdateService:
        self.config.update(config)
        return updater.UpdateService("0.8.0", feed=feed)


@pytest.fixture
def velopack(monkeypatch) -> FakeVelopack:
    fake = FakeVelopack()

    def make(source):
        mgr = FakeManager(source, **fake.config)
        fake.made.append(mgr)
        return mgr

    module = types.SimpleNamespace(
        UpdateManager=make,
        GithubSource=lambda url: ("github", url),
    )
    monkeypatch.setitem(sys.modules, "velopack", module)
    return fake


def test_no_velopack_means_no_updates(monkeypatch):
    monkeypatch.setitem(sys.modules, "velopack", None)   # import raises ImportError
    svc = updater.UpdateService("0.8.0")
    assert svc.check_for_update() is None
    assert svc.apply_update_and_restart() is False


def test_up_to_date(velopack):
    svc = velopack.service(update=None)
    assert svc.check_for_update() is None
    assert not svc.is_update_pending


def test_update_found_downloads_and_applies(velopack):
    svc = velopack.service(update=_update("1.2.3"))
    info = svc.check_for_update()
    assert info.version == "1.2.3"
    assert info.whats_new_url == "https://github.com/kellylford/GHManage/releases/tag/v1.2.3"
    assert svc.is_update_pending
    svc._download_thread.join(5)
    assert svc.is_download_complete
    assert svc.apply_update_and_restart(["--debug"]) is True
    assert velopack.made[0].applied[1] == ["--debug"]
    assert velopack.made[0].source == ("github", updater.REPO_URL)


def test_local_feed_overrides_github(velopack):
    svc = velopack.service(feed=r"C:\feed")
    svc.check_for_update()
    assert velopack.made[0].source == r"C:\feed"


def test_manager_is_resolved_once(velopack):
    svc = velopack.service()
    svc.check_for_update()
    svc.check_for_update()
    assert len(velopack.made) == 1


def test_failed_check_is_quiet(velopack):
    svc = velopack.service(check_error=RuntimeError("offline"))
    assert svc.check_for_update() is None


def test_failed_download_is_not_applied(velopack):
    svc = velopack.service(update=_update(), download_error=RuntimeError("disk full"))
    svc.check_for_update()
    svc._download_thread.join(5)
    assert not svc.is_download_complete
    assert svc.apply_update_and_restart() is False
    assert velopack.made[0].applied is None


def test_failed_apply_returns_false(velopack):
    svc = velopack.service(update=_update(), apply_error=RuntimeError("locked"))
    svc.check_for_update()
    svc._download_thread.join(5)
    assert svc.apply_update_and_restart() is False


def test_nothing_pending_cannot_apply(velopack):
    svc = velopack.service()
    assert svc.apply_update_and_restart() is False


@pytest.mark.parametrize("platform, enabled", [("win32", False), ("darwin", True)])
def test_portable_check_is_windows_only(velopack, monkeypatch, platform, enabled):
    # Velopack reports every Mac .app as portable, so the guard must not apply there
    monkeypatch.setattr(updater.sys, "platform", platform)
    svc = velopack.service(portable=True, update=_update())
    assert (svc.check_for_update() is not None) is enabled
