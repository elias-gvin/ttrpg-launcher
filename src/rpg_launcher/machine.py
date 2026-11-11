"""Machine presets: how one computer differs from the defaults."""

from __future__ import annotations

import os
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from rpg_launcher.schema import PresetError, Reader


@dataclass(frozen=True)
class AppSettings:
    """How one application is started on a machine."""

    id: str
    command: tuple[str, ...]
    enabled: bool = True
    process_names: tuple[str, ...] = ()
    # Extra settings that only the component using this application understands.
    options: dict[str, str] = field(default_factory=dict)

    def path(self, option: str, default: Path) -> Path:
        value = self.options.get(option)
        return Path(os.path.expanduser(value)) if value else default


@dataclass(frozen=True)
class Machine:
    id: str
    name: str
    source: str
    hostnames: tuple[str, ...] = ()
    apps: dict[str, AppSettings] = field(default_factory=dict)
    overrides: dict[str, dict] = field(default_factory=dict)
    is_builtin: bool = False

    def app(self, app_id: str) -> AppSettings:
        """Settings for an application; by default it is started by its own name."""
        return self.apps.get(app_id) or AppSettings(id=app_id, command=(app_id,))

    @staticmethod
    def builtin() -> Machine:
        return Machine(
            id="default",
            name="built-in defaults (no machine file)",
            source="(built-in)",
            is_builtin=True,
        )


def parse_machine(
    machine_id: str,
    data: dict,
    source: str,
    app_options: Mapping[str, Collection[str]],
) -> Machine:
    """Read a machine file. `app_options` names the extra keys each app accepts."""
    problems: list[str] = []
    top = Reader(data, source, "", problems)
    name = top.text("name", default=machine_id)
    hostnames = top.texts("hostnames")
    apps_data = top.tables("apps")
    overrides = top.tables("overrides")
    top.done()

    apps = {}
    for app_id, app_data in apps_data.items():
        reader = top.child(f"apps.{app_id}", app_data)
        command = reader.texts("command")
        enabled = reader.flag("enabled", True)
        process_names = reader.texts("process_names")
        options = {key: reader.text(key) for key in app_options.get(app_id, ())}
        reader.done()

        if app_data.get("command") == []:
            problems.append(f"{source}: apps.{app_id}.command: must not be empty")
        apps[app_id] = AppSettings(
            id=app_id,
            command=command or (app_id,),
            enabled=enabled,
            process_names=process_names,
            options={key: value for key, value in options.items() if value},
        )

    if problems:
        raise PresetError(problems)
    return Machine(
        id=machine_id,
        name=name,
        source=source,
        hostnames=hostnames,
        apps=apps,
        overrides=overrides,
    )
