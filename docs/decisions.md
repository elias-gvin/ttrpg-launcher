# Design decisions

Answers to the open questions in [PRD.md](PRD.md), agreed with the GM on
2026-11-11. Section numbers refer to the PRD.

## Decided

| Question (PRD) | Decision |
|---|---|
| Target machines (FR-03, §13) | Linux only. Both NixOS and other distributions (the main desktop is Arch). |
| What Nix provides (FR-03) | The launcher everywhere. On NixOS a module also installs the applications. On other distributions the applications come from the system (packages or Flatpak) and `doctor` checks them. |
| Applications in the MVP (§13) | OBS, Chromium, and any other application named in a game (Discord today). EasyEffects is left out. |
| Preset format and editing (FR-08) | TOML files read at launch. No rebuild after an edit. No built-in editor. |
| Where presets live (§13) | A private directory or repository of the GM's, separate from the launcher. This repository holds only examples with placeholder links. |
| Game and machine settings (FR-02) | One file per game, one per machine. The effective game is the game file with the machine's `[overrides.<game>]` merged on top. |
| Machine selection (FR-02) | Automatic by hostname, with `--machine` or `$RPG_LAUNCHER_MACHINE` to choose by hand. No match is an error, not a guess. |
| Interface (§8) | Command line with an interactive picker and a menu after launch. |
| Browser behaviour (§13) | A dedicated Chromium profile for game pages. Pages open as tabs in one new window; a page can ask for its own window. |
| OBS configuration (FR-05) | A game names an OBS scene and, optionally, a profile and scene collection. The VDO.Ninja scene link stays inside OBS as a browser source. Each machine keeps its own OBS settings under the same names; the launcher does not copy them between machines. |
| OBS already running (§13) | Left untouched and reported, because profile and scene cannot be applied to a running OBS from the command line. |
| Recording (FR-09) | Started only when the game says `record = true`. |
| Invitation format (FR-06) | Plain text. A game can give each named player their own link plus shared links; each player's message is copied separately. Display and copy only. |
| Keeping GM links private (NFR-06) | By structure: invitations are built only from `[invitation]`. Pages under `[open]` have no path into them. |
| Manual checks (FR-07) | Written in the game preset next to the component they concern and listed after every launch. The launcher adds a recording reminder for OBS. |
| Stop and relaunch (§13) | The launcher never stops applications. Quitting it leaves everything running. Launching again opens the pages again. |
| Window placement (FR-04) | Not controlled. On Wayland a launcher cannot place other applications' windows. |
| Music (§3.1) | The current flow stays: YouTube in a tab, shared from the VDO.Ninja music page, with the steps listed as manual checks. |

## Differences from the PRD

- **Nix on non-NixOS machines.** The PRD's definition of done says required
  software is available through the Nix environment. On Arch the applications
  come from the system instead, and `doctor` verifies them. Running the nixpkgs
  builds of OBS and Chromium on Arch needs graphics-driver wrapping and would
  not use the existing Flatpak OBS settings.
- **Preset variants (§9).** Not built. Alternative links are kept as comments
  in the game file.

## Later, in this order

1. **Session overrides (Milestone D).** A third layer on top of game and
   machine, using the same merge. The VDO.Ninja room stays the same for a whole
   campaign, so this covers music and map links; the OBS scene link does not
   need to follow.
2. **Music through a virtual audio device.** Play YouTube or local tracks into
   a dedicated audio device and have the VDO.Ninja music page pick it up by
   itself. Removes the share-tab and mute-tab steps. Needs a trial first:
   sending one Chromium window to a chosen device, and VDO.Ninja's
   `&audiodevice` parameter, are both untested here.
3. **EasyEffects voice presets.**

## Not yet tried on real hardware

- Launching on a NixOS machine. The module evaluates and the package builds,
  but OBS's process name there (assumed `.obs-wrapped`) is unconfirmed.
