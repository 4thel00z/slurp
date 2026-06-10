"""Tests for the lazy downloader registry used by the worker."""

from slurp.adapters.downloader.registry import DownloaderRegistry


def test_builds_and_caches_lazily():
    """A downloader is built on first use and reused afterwards."""
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return object()

    registry = DownloaderRegistry({"local": factory})

    first = registry.get("local")
    second = registry.get("local")

    assert first is second
    assert calls["n"] == 1


def test_unknown_downloader_returns_none():
    registry = DownloaderRegistry({"local": object})
    assert registry.get("confluence") is None


def test_only_requested_factory_is_invoked():
    """Asking for one connector never constructs the others."""
    built = []
    registry = DownloaderRegistry(
        {
            "local": lambda: built.append("local") or object(),
            "confluence": lambda: built.append("confluence") or object(),
        }
    )

    registry.get("local")

    assert built == ["local"]
