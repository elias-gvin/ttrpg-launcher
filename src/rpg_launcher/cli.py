"""Command line interface: pick a game, launch it, hand out player links."""

from __future__ import annotations

import argparse
import os
import shlex
import sys

from rpg_launcher import __version__, clipboard, doctor, invitation, paths
from rpg_launcher.launcher import Launcher, Outcome, Status, manual_checks
from rpg_launcher.presets import (
    Game,
    Machine,
    Player,
    PresetError,
    PresetStore,
    find_presets_dir,
)

_COLORS = {"green": "32", "yellow": "33", "red": "31", "bold": "1", "dim": "2"}


class _Quit(Exception):
    """The GM backed out of a prompt."""


def _paint(text: str, color: str) -> str:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{_COLORS[color]}m{text}\033[0m"


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise _Quit from None


def _pick(title: str, options: list[tuple[str, str]]) -> str:
    """Show a numbered list and return the key of the chosen option."""
    print(f"{title}:")
    for number, (_, text) in enumerate(options, start=1):
        print(f"  [{number}] {text}")
    while True:
        answer = _ask("Number (q to quit): ")
        if answer.casefold() in ("q", "quit", ""):
            raise _Quit
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        print(f"Please type a number from 1 to {len(options)}.")


def _open_store(args: argparse.Namespace) -> tuple[PresetStore, Machine]:
    store = PresetStore(find_presets_dir(getattr(args, "presets", None)))
    return store, store.resolve_machine(getattr(args, "machine", None))


def _choose_game(store: PresetStore, wanted: str | None) -> str:
    if wanted:
        return store.find_game(wanted)
    game_ids = store.game_ids()
    if not game_ids:
        raise PresetError(f"No game presets in {store.root / 'games'}.")
    if not _interactive():
        raise PresetError(f"Name the game to use. Available games: {', '.join(game_ids)}.")
    options = []
    for game_id in game_ids:
        try:
            options.append((game_id, store.load_game(game_id).name))
        except PresetError:
            options.append((game_id, f"{game_id} (preset has errors: run 'doctor')"))
    return _pick("Choose game", options)


def _status_lines(outcome: Outcome, width: int, show_command: bool) -> list[str]:
    color = {
        Status.FAILED: "red",
        Status.SKIPPED: "yellow",
        Status.RUNNING: "yellow",
        Status.PLANNED: "dim",
    }.get(outcome.status, "green")
    line = f"  {outcome.label:<{width}}  {_paint(outcome.status.value, color)}"
    lines = [line]
    if outcome.detail:
        if outcome.status is Status.FAILED or len(outcome.detail) > 40:
            lines.append(f"      {outcome.detail}")
        else:
            lines[0] = f"{line} ({outcome.detail})"
    if show_command and outcome.command:
        lines.append(_paint(f"      $ {shlex.join(outcome.command)}", "dim"))
    return lines


def _launch(game: Game, machine: Machine, dry_run: bool) -> tuple[list[Outcome], list[str]]:
    """Run the launch, printing each component's outcome as it happens."""
    launcher = Launcher(game, machine, dry_run=dry_run, log_dir=paths.log_dir())
    labels = ["OBS", *game.apps, *(item.label for item in game.open)]
    width = max((len(label) for label in labels), default=0)

    report = ["Dry run, nothing is started:" if dry_run else "Starting game environment..."]
    print(report[0])
    outcomes = []
    for outcome in launcher.run():
        outcomes.append(outcome)
        lines = _status_lines(outcome, width, show_command=dry_run)
        print("\n".join(lines), flush=True)
        report += lines
    if not outcomes:
        report.append("  Nothing to start: this game lists no applications or pages.")
        print(report[-1])

    tail = []
    attention = [
        f"{outcome.label}: {text}" for outcome in outcomes for text in outcome.attention
    ]
    if attention:
        tail += ["", _paint("Needs attention:", "yellow")]
        tail += [f"  - {text}" for text in attention]
    checks = manual_checks(game, outcomes)
    if checks:
        tail += ["", "Manual checks (not verified by the launcher):"]
        tail += [f"  [ ] {text}" for text in checks]

    failed = sum(outcome.status is Status.FAILED for outcome in outcomes)
    skipped = sum(outcome.status is Status.SKIPPED for outcome in outcomes)
    if not dry_run and outcomes:
        done = len(outcomes) - failed - skipped
        summary = f"{done} of {len(outcomes)} components started"
        if failed:
            summary += f", {_paint(f'{failed} FAILED', 'red')}"
        if skipped:
            summary += f", {skipped} skipped"
        tail += [
            "",
            f"{summary}. Sound, screen sharing and recording have not been "
            f"verified: check them yourself.",
        ]
    print("\n".join(tail))
    return outcomes, report + tail


def _copy(text: str, what: str) -> None:
    try:
        clipboard.copy(text)
    except clipboard.ClipboardError as error:
        print(f"{error}\n\n{text}\n")
    else:
        print(f"Copied {what}.")


def _menu(game: Game, report: list[str]) -> None:
    """After launch: copy invitations and re-show output until the GM quits."""
    players = game.invitation.players
    while True:
        print()
        if players:
            print(f"  [1-{len(players)}] copy that player's invitation")
        elif game.invitation.has_links:
            print("  [c] copy the invitation")
        print("  [i] show invitation   [s] show status   [q] quit (applications keep running)")
        answer = _ask("> ").casefold()
        if answer in ("q", "quit"):
            return
        if answer == "i":
            print(invitation.overview(game))
        elif answer == "s":
            print("\n".join(report))
        elif players and answer.isdigit() and 1 <= int(answer) <= len(players):
            player = players[int(answer) - 1]
            _copy(
                invitation.message_for_player(game.invitation, player),
                f"the invitation for {player.name}",
            )
        elif answer == "c" and not players and game.invitation.has_links:
            _copy(invitation.message_for_everyone(game.invitation), "the invitation")
        else:
            print("Not one of the choices above.")


def _warn_missing_links(game: Game) -> None:
    if not game.invitation.has_links:
        print(
            _paint(
                f"Configuration issue: {game.source} has no player links. Add "
                f"[invitation.shared.<id>] or [invitation.players.<id>] with a url.",
                "yellow",
            )
        )


def cmd_launch(args: argparse.Namespace) -> int:
    store, machine = _open_store(args)
    picked_from_menu = not args.game
    game = store.load_game(_choose_game(store, args.game), machine)

    print(f"Game:    {_paint(game.name, 'bold')} ({game.source})")
    print(f"Machine: {machine.name} ({machine.source})")
    if picked_from_menu and not args.dry_run:
        if _ask("Launch? [Y/n] ").casefold() not in ("", "y", "yes"):
            raise _Quit
    print()

    outcomes, report = _launch(game, machine, args.dry_run)
    print()
    print(invitation.overview(game))
    _warn_missing_links(game)

    if not args.dry_run and not args.no_menu and _interactive():
        try:
            _menu(game, report)
        except _Quit:
            pass
    return 1 if any(outcome.status is Status.FAILED for outcome in outcomes) else 0


def _find_player(game: Game, wanted: str) -> Player:
    players = game.invitation.players
    if wanted.isdigit() and 1 <= int(wanted) <= len(players):
        return players[int(wanted) - 1]
    for player in players:
        if wanted.casefold() in (player.id.casefold(), player.name.casefold()):
            return player
    known = ", ".join(f"{player.id} ({player.name})" for player in players) or "none"
    raise PresetError(f"{game.source}: no player called '{wanted}'. Players: {known}.")


def cmd_invite(args: argparse.Namespace) -> int:
    store, machine = _open_store(args)
    game = store.load_game(_choose_game(store, args.game), machine)
    if not game.invitation.has_links:
        raise PresetError(
            f"{game.source}: no player links. Add [invitation.shared.<id>] or "
            f"[invitation.players.<id>] with a url."
        )

    players = game.invitation.players
    if args.player or not players:
        if args.player:
            player = _find_player(game, args.player)
            text = invitation.message_for_player(game.invitation, player)
            what = f"the invitation for {player.name}"
        else:
            text = invitation.message_for_everyone(game.invitation)
            what = "the invitation"
        print(text)
        if args.copy:
            try:
                clipboard.copy(text)
            except clipboard.ClipboardError as error:
                print(error, file=sys.stderr)
                return 1
            print(f"Copied {what}.", file=sys.stderr)
        return 0

    print(invitation.overview(game))
    if args.copy:
        if not _interactive():
            raise PresetError(
                "Each player has their own link: name one with --player "
                "(an id, a name or a number from the list)."
            )
        try:
            _menu(game, [])
        except _Quit:
            pass
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    store = PresetStore(find_presets_dir(getattr(args, "presets", None)))
    game_id = store.find_game(args.game) if args.game else None
    findings = doctor.diagnose(store, getattr(args, "machine", None), game_id)

    marks = {
        doctor.OK: _paint("ok  ", "green"),
        doctor.WARN: _paint("warn", "yellow"),
        doctor.FAIL: _paint("FAIL", "red"),
    }
    for finding in findings:
        print(f"  {marks[finding.level]}  {finding.text}")
    failures = sum(finding.level == doctor.FAIL for finding in findings)
    warnings = sum(finding.level == doctor.WARN for finding in findings)
    print(
        f"\n{failures} problem(s), {warnings} warning(s). This checks presets and "
        f"installed software only, not sound, screen sharing or recording."
    )
    return 1 if failures else 0


def cmd_list(args: argparse.Namespace) -> int:
    store = PresetStore(find_presets_dir(getattr(args, "presets", None)))
    print(f"Games in {store.root / 'games'}:")
    for game_id in store.game_ids():
        try:
            print(f"  {game_id:<16} {store.load_game(game_id).name}")
        except PresetError:
            print(f"  {game_id:<16} {_paint('preset has errors: run doctor', 'red')}")

    try:
        selected = store.resolve_machine(getattr(args, "machine", None))
    except PresetError as error:
        selected = None
        note = error.problems[0]
    print("\nMachines:")
    for machine_id in store.machine_ids():
        mark = "  <- used on this computer" if selected and selected.id == machine_id else ""
        print(f"  {machine_id}{mark}")
    if selected is None:
        print(_paint(f"  {note}", "yellow"))
    elif selected.is_builtin:
        print("  (none: built-in defaults are used)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Accepted both before and after the command name.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--presets",
        metavar="DIR",
        default=argparse.SUPPRESS,
        help=f"presets directory (default: ${paths.PRESETS_ENV}, "
        f"then {paths.default_presets_dir()})",
    )
    common.add_argument(
        "--machine",
        metavar="ID",
        default=argparse.SUPPRESS,
        help=f"machine preset to use (default: ${paths.MACHINE_ENV}, "
        f"then the one matching this hostname)",
    )

    parser = argparse.ArgumentParser(
        prog="rpg-launcher",
        parents=[common],
        description="Start a game's applications and pages, then hand out "
        "player links. Without a command: choose a game and launch it.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.set_defaults(handler=cmd_launch, game=None, dry_run=False, no_menu=False)
    commands = parser.add_subparsers(title="commands", metavar="")

    launch = commands.add_parser(
        "launch", parents=[common], help="start a game's applications and pages"
    )
    launch.add_argument("game", nargs="?", help="game id or name (asked if omitted)")
    launch.add_argument(
        "--dry-run", action="store_true", help="show what would be started, start nothing"
    )
    launch.add_argument(
        "--no-menu", action="store_true", help="exit after launching instead of showing the menu"
    )
    launch.set_defaults(handler=cmd_launch)

    invite = commands.add_parser(
        "invite", parents=[common], help="show or copy the player invitation"
    )
    invite.add_argument("game", nargs="?", help="game id or name (asked if omitted)")
    invite.add_argument(
        "--player", metavar="WHO", help="one player's message: an id, a name or a number"
    )
    invite.add_argument("--copy", action="store_true", help="copy to the clipboard")
    invite.set_defaults(handler=cmd_invite)

    check = commands.add_parser(
        "doctor", parents=[common], help="check presets and installed software"
    )
    check.add_argument("game", nargs="?", help="check one game (default: all games)")
    check.set_defaults(handler=cmd_doctor)

    listing = commands.add_parser("list", parents=[common], help="list games and machines")
    listing.set_defaults(handler=cmd_list)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except PresetError as error:
        for problem in error.problems:
            print(_paint(f"Error: {problem}", "red"), file=sys.stderr)
        return 2
    except _Quit:
        return 0
    except KeyboardInterrupt:
        print()
        return 130
