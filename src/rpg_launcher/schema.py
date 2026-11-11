"""Reading preset tables with error messages the GM can act on."""

from __future__ import annotations

import difflib
import tomllib
from pathlib import Path


class PresetError(Exception):
    """One or more problems in the preset files that the GM can fix."""

    def __init__(self, problems: list[str] | str):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("\n".join(self.problems))


_MISSING = object()


class Reader:
    """Reads one TOML table, recording wrong types and unknown keys.

    Every key that is asked for counts as known. Call done() after the last
    one, and any other key in the table is reported as unknown.
    """

    def __init__(self, data: dict, source: str, path: str, problems: list[str]):
        self.data = data
        self.source = source
        self.path = path
        self.problems = problems
        self.known: set[str] = set()

    def _where(self, key: str | None = None) -> str:
        parts = [part for part in (self.path, key) if part]
        return f"{self.source}: {'.'.join(parts)}" if parts else self.source

    def _take(self, key: str, required: bool = False):
        self.known.add(key)
        if key not in self.data:
            if required:
                self.problems.append(f"{self._where()}: '{key}' is required")
            return _MISSING
        return self.data[key]

    def bad(self, key: str, expected: str) -> None:
        self.problems.append(f"{self._where(key)}: must be {expected}")

    def text(self, key: str, default: str | None = None, required: bool = False):
        value = self._take(key, required)
        if value is _MISSING:
            return default
        if not isinstance(value, str) or not value.strip():
            self.bad(key, "non-empty text")
            return default
        return value

    def url(self, key: str) -> str:
        """A required URL, returned exactly as written."""
        value = self.text(key, default="", required=True)
        if value and (value.startswith("-") or any(c.isspace() for c in value)):
            self.bad(key, "a URL without spaces")
        return value

    def flag(self, key: str, default: bool) -> bool:
        value = self._take(key)
        if value is _MISSING:
            return default
        if not isinstance(value, bool):
            self.bad(key, "true or false")
            return default
        return value

    def texts(self, key: str) -> tuple[str, ...]:
        value = self._take(key)
        if value is _MISSING:
            return ()
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            self.bad(key, 'a list of texts, like ["one", "two"]')
            return ()
        return tuple(value)

    def table(self, key: str) -> dict | None:
        value = self._take(key)
        if value is _MISSING:
            return None
        if not isinstance(value, dict):
            self.bad(key, f"a table, written as [{'.'.join(filter(None, (self.path, key)))}]")
            return None
        return value

    def tables(self, key: str) -> dict[str, dict]:
        """A table of named tables, such as [open.music] and [open.board]."""
        value = self.table(key)
        if value is None:
            return {}
        result = {}
        for name, entry in value.items():
            if isinstance(entry, dict):
                result[name] = entry
            else:
                where = ".".join(filter(None, (self.path, key)))
                self.problems.append(
                    f"{self.source}: {where}.{name}: must be a table, "
                    f"written as [{where}.<id>] with keys below it"
                )
        return result

    def child(self, key: str, data: dict) -> Reader:
        path = ".".join(filter(None, (self.path, key)))
        return Reader(data, self.source, path, self.problems)

    def done(self) -> None:
        for key in self.data:
            if key in self.known:
                continue
            close = difflib.get_close_matches(key, sorted(self.known), n=1)
            hint = f" (did you mean '{close[0]}'?)" if close else ""
            self.problems.append(f"{self._where(key)}: unknown key{hint}")


def merge(base: dict, override: dict) -> dict:
    """Layer `override` on `base`: tables merge, every other value replaces."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def read_toml(path: Path, shown: str) -> dict:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise PresetError(f"{shown}: file not found") from None
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise PresetError(f"{shown}: not valid TOML: {error}") from None
    except OSError as error:
        raise PresetError(f"{shown}: cannot be read: {error.strerror}") from None
