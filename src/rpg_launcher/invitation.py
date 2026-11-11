"""Build the text players receive.

Only the [invitation] part of a game preset is used here. Pages listed under
[open] are the GM's own and cannot end up in an invitation.
"""

from __future__ import annotations

from rpg_launcher.presets import Game, Invitation, Player


def _message(invitation: Invitation, link_lines: list[str]) -> str:
    blocks = [invitation.intro, "\n".join(link_lines), invitation.note]
    return "\n\n".join(block for block in blocks if block)


def _shared_lines(invitation: Invitation) -> list[str]:
    return [f"{link.label}: {link.url}" for link in invitation.shared]


def message_for_player(invitation: Invitation, player: Player) -> str:
    """The message for one player: their own link, then the shared links."""
    own = f"{invitation.player_link_label}: {player.url}"
    return _message(invitation, [own, *_shared_lines(invitation)])


def message_for_everyone(invitation: Invitation) -> str:
    """The message when a game has no per-player links."""
    return _message(invitation, _shared_lines(invitation))


def overview(game: Game) -> str:
    """Everything players can be sent, for the GM to read."""
    invitation = game.invitation
    lines = [f"PLAYER INVITATION: {game.name}"]
    if not invitation.has_links:
        lines.append("  (no player links are configured for this game)")
        return "\n".join(lines)
    if invitation.intro:
        lines.append(f"  {invitation.intro}")
    if invitation.players:
        lines.append(f"  {invitation.player_link_label}, one link per player:")
        for number, player in enumerate(invitation.players, start=1):
            lines.append(f"    [{number}] {player.name}: {player.url}")
    for link in invitation.shared:
        lines.append(f"  {link.label}: {link.url}")
    if invitation.note:
        lines.append(f"  {invitation.note}")
    return "\n".join(lines)
