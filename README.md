# RPG Session Launcher

Pick a game, and the launcher starts the applications and browser pages that
game needs, tells you what happened to each, and gives you the invitation to
send to players.

It starts the tools you already use (OBS, Chromium, Discord, VDO.Ninja pages)
and leaves their settings to them. See [docs/PRD.md](docs/PRD.md) for the
requirements; its section 17 records the decisions made, the GM's preferences
and what is still open.

## Install

The launcher is packaged with Nix. Linux only.

**NixOS:** add this repository as a flake input and enable the module. It
installs the launcher, OBS and Chromium.

```nix
{
  inputs.rpg-launcher.url = "git+file:///path/to/rpg_launcher";

  # in your system configuration:
  imports = [ inputs.rpg-launcher.nixosModules.default ];
  programs.rpg-launcher.enable = true;
  # To add Discord (unfree):
  # programs.rpg-launcher.apps = [ pkgs.obs-studio pkgs.chromium pkgs.discord ];
}
```

**Other distributions (Arch and so on):** install the launcher with Nix and
the applications with your usual package manager or Flatpak.

```sh
nix profile install /path/to/rpg_launcher
```

Then run `rpg-launcher doctor` to see whether everything the games need is
installed on this machine.

## Presets

Presets are plain TOML files in a directory of your own, kept outside this
repository because VDO.Ninja links carry room names and passwords.

```text
~/.config/rpg-launcher/
  games/samosbor.toml      one file per game
  games/frostpunk.toml
  machines/desktop.toml    one file per computer (optional)
  machines/laptop.toml
```

Another location can be given with `--presets DIR` or `$RPG_LAUNCHER_PRESETS`.
To start, copy [examples/presets](examples/presets) there and replace the
placeholder links.

A `presets/` directory inside a checkout of this repository is ignored by git,
so presets can also sit next to the code:

```sh
export RPG_LAUNCHER_PRESETS=/path/to/rpg_launcher/presets
```

## Use

```sh
rpg-launcher                          # choose a game, launch it, copy invitations
rpg-launcher launch samosbor          # launch a game directly
rpg-launcher launch samosbor --dry-run   # show what would be started, start nothing
rpg-launcher invite samosbor          # show the invitation again at any time
rpg-launcher invite samosbor --player 2 --copy   # copy one player's message
rpg-launcher doctor                   # check presets and installed software
rpg-launcher list                     # games and machines
```

After a launch the launcher stays open with a small menu for copying each
player's invitation. Quitting it leaves the applications running.

## Editing presets

**Change a link.** Edit the `url` line in the game file. The URL is used
exactly as written, so every VDO.Ninja option stays in the URL.

**Add a game.** Add a file to `games/`. The file name is the game's id.

```toml
name = "Frostpunk"

[obs]
scene = "Frostpunk"

[open.director]
label = "Director"
url = "https://vdo.ninja/?director=ROOM&password=..."

[invitation.shared.join]
label = "Join game"
url = "https://vdo.ninja/?room=ROOM&hash=..."
```

**Add a computer.** Add a file to `machines/`. List only what differs from the
defaults; game files are not copied or changed.

```toml
name = "Desktop"
hostnames = ["archlinux"]

[apps.obs]
command = ["flatpak", "run", "com.obsproject.Studio"]
config_dir = "~/.var/app/com.obsproject.Studio/config/obs-studio"
```

**Change one game on one computer.** Put the difference under
`[overrides.<game id>]` in the machine file. Everything else is inherited.

```toml
[overrides.samosbor.open.board]
window = false
```

### Game file

| Key | Meaning |
|---|---|
| `name` | Name shown in the launcher. Defaults to the file name. |
| `apps` | Other applications to start, for example `["discord"]`. |
| `checks` | Reminders for the game as a whole. |
| `[obs]` | Start OBS. Optional `profile`, `collection` and `scene` are the names OBS shows. `record = true` starts recording at once; the default is `false`. |
| `[open.<id>]` | A page for your browser: `url`, optional `label`, `window = true` for its own window. |
| `[invitation]` | Optional `intro`, `note` and `player_link_label`. |
| `[invitation.shared.<id>]` | A link every player gets: `label`, `url`. |
| `[invitation.players.<id>]` | A player with their own link: `name`, `url`. |

`[obs]` and every `[open.<id>]` also take `checks = [...]`, reminders shown
after launch, and `enabled = false`, mainly for machine overrides.

Only links under `[invitation]` are ever shown to players. Pages under
`[open]` are yours and cannot end up in an invitation.

### Machine file

| Key | Meaning |
|---|---|
| `name` | Name shown in the launcher. |
| `hostnames` | Hostnames this file applies to. A file named after the hostname also matches. `--machine ID` or `$RPG_LAUNCHER_MACHINE` picks one by hand. |
| `[apps.<id>]` | `command` to start the application (default: its id). `enabled = false` if this computer never runs it. |
| `[apps.obs]` | Also `config_dir`, where OBS keeps its settings. |
| `[apps.chromium]` | Also `user_data_dir`, the browser profile used for game pages. |
| `[overrides.<game id>]` | Changes to one game on this computer. |

With no machine files at all, the defaults are used on every computer.

## What the launcher does and does not check

"Started" and "opened" mean the command ran. The launcher does not verify
sound, screen sharing or recording. It lists your `checks` after every launch
as things to confirm yourself, and it says so when it could not check
something.

`doctor` checks that presets are valid, that each application can be found,
that the OBS profile, scene collection and scene named in a game exist, and
that every game has at least one player link.

## Behaviour worth knowing

- **Browser profile.** Game pages open in a separate Chromium profile
  (`~/.local/share/rpg-launcher/chromium-profile`), apart from your everyday
  browsing. On each computer, sign in to Google and YouTube there once.
- **OBS already running.** The launcher leaves it alone and tells you that the
  profile and scene were not applied.
- **Recording.** Never started unless the game says `record = true`.
- **Failures.** One application failing does not stop the others. Output of
  each started application is kept in `~/.local/state/rpg-launcher/logs/`.
- **Window placement.** Not controlled by the launcher.

## Development

```sh
nix develop
python -m unittest discover -s tests
python -m rpg_launcher --presets examples/presets launch samosbor --dry-run
nix flake check    # builds the package and runs the tests
```

### Adding a component

A component is one kind of thing a game can start. OBS, plain applications
and browser pages are the three built in, each one module in
[src/rpg_launcher/components](src/rpg_launcher/components). To add another:

1. Write a module there with a class that subclasses `Component` from
   `base.py`. Give it a `key`, the name of its table in a game preset, and
   these methods:
   - `parse` reads that table and returns the component's settings.
   - `start` starts things through `context.spawn()` and yields an `Outcome`
     for each.
   - `needed_apps` and `diagnose` are optional and feed `doctor`.
2. Add an instance to `COMPONENTS` in `components/__init__.py`. The order
   there is the launch order.

Preset validation, machine overrides, dry runs, status output, manual checks
and `doctor` then cover the new component without further changes. Extra
machine settings for its application are declared with `app_options`.
`apps.py` is the shortest example; `tests/test_components.py` adds a made-up
component from outside.
