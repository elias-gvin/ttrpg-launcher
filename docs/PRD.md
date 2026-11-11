# RPG Session Launcher — Product Requirements Document

**Status:** Design decisions agreed with the GM; MVP implemented in this repository, not yet used for a real session  
**Version:** 0.2  
**Date:** 2026-11-11 (version 0.1: 2026-11-10)  
**Product type:** Local RPG session launcher and environment manager  
**Primary user:** Game Master (GM) running online tabletop RPG sessions

> **Document intent:** Describe **what** the product should achieve and **why**, not prescribe its internal implementation. Items labeled **Confirmed** reflect the current discussion; items labeled **Proposed** need validation. Questions and unknowns are explicitly marked **Open**.
>
> **Version 0.2:** Items labeled **Decided** were agreed with the GM on 2026-11-11. They are collected in **§17, which is authoritative**: where older wording elsewhere in this document differs, §17 wins. §17 also records the GM's stated preferences, what is still open, and what has been built.
>
> **No real links or passwords belong in this document.** They live only in the GM's private presets (§17.3).

---

## 1. Executive summary

The GM currently prepares online tabletop RPG games by manually starting and configuring several independent applications and browser pages. This includes participant communication via VDO.Ninja, presentation of maps/art through Chromium-based tools, music playback from YouTube, dice rolling through Discord, and OBS recording. Audio volume and application readiness require repeated manual checks.

This setup is flexible but costly to prepare, error-prone, and difficult to reproduce on another computer.

**The product should provide a single entry point for selecting and launching a game-specific setup**, while relying as much as possible on existing software, native settings, user-provided URLs, and reusable presets. It should help ensure the required software is available through a **Nix-managed environment** and, after launching, clearly display the **links that players must follow to join the game**.

The initial release should be deliberately small. It is **not** intended to replace OBS, VDO.Ninja, EasyEffects, YouTube, or the dice-rolling service.

## 2. Problem and motivation

### 2.1 Current pain points — Confirmed

- **Repetitive preparation:** The GM spends substantial time opening browser tabs, launching OBS, and arranging the environment before each game.
- **Manual verification:** The GM must check that applications, streams, inputs, and recording are working.
- **Audio setup burden:** Music and microphone levels require manual adjustment; incorrect balancing can negatively affect players and recordings.
- **Fragile reproducibility:** A setup that works on one computer may be missing dependencies, presets, assets, or configuration on another.
- **Scattered configuration:** Different tools store their settings in different places; the GM does not want to maintain duplicate configuration models for those tools.
- **Player onboarding:** Players need one or more links to join a game, and the GM should not have to find and copy those links manually each time.
- **Session preservation:** The GM records games and wants to retain important information about what happened, including identifying the music heard in recordings. This is a broader product direction, not the main focus of the first release.

### 2.2 Why solve this

The GM's attention before and during a session should be spent preparing and running the game, not administering a stack of applications. Reducing setup steps and configuration drift should make sessions easier to start, reduce recording/audio mistakes, and allow the GM to switch machines without recreating the entire workflow.

### 2.3 Desired outcome

A typical future workflow should be:

1. Open the launcher.
2. Choose a game preset, with the relevant machine setup applied.
3. Launch the configured environment.
4. See whether the essential components are ready and which checks, if any, still require human attention.
5. Copy or share the player invitation containing the correct links.
6. Run the game using the familiar applications.

**Decided:** The interface is a command-line program with an interactive game picker and a menu after launch (§8, §17.2).

## 3. Current environment and workflow

### 3.1 Known toolchain — Confirmed unless marked

| Area | Current tool / approach | Purpose | Notes |
|---|---|---|---|
| Operating system | Arch Linux desktop | Main GM workstation | GNOME on Wayland. **Decided:** Linux only; NixOS and non-NixOS machines are both targets. |
| Browser | Chromium | Hosts multiple game-related pages | Multiple independently useful pages/windows. |
| Player communication | VDO.Ninja | Connects participants and transports media | Existing URLs can include detailed application-specific settings. |
| Visual presentation | Draw.io / Excalidraw, shown through Chromium and VDO.Ninja | Displays art, maps, and in-game material | Content is presented as a browser view; exact per-game pages vary. Draw.io today, Excalidraw planned. Roll20 is no longer used. |
| Music | Regular YouTube in Chromium, audio shared through VDO.Ninja | Background music / atmosphere | The video itself is not intended as the player-facing presentation. The GM joins the room a second time through a dedicated music link, shares the YouTube tab's audio from it, and mutes that tab locally. |
| Dice | Discord dice bot | Player/GM dice rolls | Replacement is desirable eventually, not a launch prerequisite. The GM uses the Discord desktop app; players are sent the channel link. |
| Recording | OBS Studio | Records sessions | Audio balance and recording checks currently require attention. OBS records a VDO.Ninja scene link through a browser source; each game has its own OBS scene. |
| Microphone / effects | Existing microphone and audio interface; EasyEffects considered | GM voice, future NPC voice presets | EasyEffects NPC effects are **planned**, not established as an existing production workflow. |
| Software provisioning | Nix proposed; NixOS is used on at least one other device | Reproducible dependencies and application availability | Nix is an agreed direction for this product, not a description of the present desktop setup. |

### 3.2 Current manual preparation — Confirmed at the goal level

The GM launches Chromium and opens the required VDO.Ninja links, visual-presentation content, YouTube, and other game pages; launches OBS; checks media sharing and recording; and adjusts audio. Player links are handled separately.

**Documented on 2026-11-11** for the Samosbor campaign. Only the roles are listed here; the links themselves are in the GM's presets.

| What | Who opens it | Notes |
|---|---|---|
| VDO.Ninja director link | GM, in the browser | GM only. Carries the room password. |
| VDO.Ninja scene link | OBS, as a browser source | GM only. Carries the room password. Never opened by the launcher; it is part of the OBS scene. |
| VDO.Ninja player links | Each player | One link per player, each with its own stream id. They use a hash, not the password. |
| VDO.Ninja music link | GM, in the browser | Publishes the music to the room. |
| VDO.Ninja screen-share link | GM, in the browser | Publishes the board or map window to the room. |
| YouTube | GM, in the browser | Source of the music. |
| Draw.io board | GM, in the browser | In its own window, so it can be shared. |
| Discord channel | GM in the desktop app; players by link | Dice rolls. |

The steps the GM still performs by hand each session (sharing the music tab, muting sources in OBS, and so on) are written as `checks` in the game preset and listed after every launch. Display layout and audio device routing have **not** been documented.

### 3.3 Important characteristics to preserve

- **Flexibility:** The GM can use arbitrary browser-based maps, images, and presentation tools.
- **Existing functionality:** VDO.Ninja, OBS, and other applications remain responsible for their own specialized features.
- **Original settings:** Existing VDO.Ninja URLs should be used intact; the launcher should not invent a parallel vocabulary for their video/audio options.
- **Per-game differences:** Different campaigns need different links, visual assets, presets, and possibly applications.
- **Machine differences:** A desktop and laptop may have different microphones, displays, and recording capabilities.

## 4. Product principles

1. **Composition over replacement.** Assemble and launch existing tools; do not build an alternative VTT, mixer, media player, or recording application for the MVP.
2. **Native configuration over a custom DSL.** When choosing between an application’s native settings/configuration and a launcher-specific domain-specific language (DSL) for the same settings, **prefer the native format**. Reference OBS profiles/scene collections, EasyEffects presets, and full VDO.Ninja URLs directly. Add launcher-specific fields only for launch-time composition or information the applications do not natively represent; do not duplicate their option sets.
3. **Declare intent once.** Game-specific information should be defined once and reused across compatible machines; machine-specific differences should not force a duplicate game preset.
4. **Minimal user-authored glue.** Avoid requiring the GM to write scripts or extensive configs for ordinary setup changes.
5. **Portable and reproducible.** A missing application or dependency should not be an unexpected blocker on a newly provisioned machine.
6. **Explicit readiness, not false guarantees.** Opening a program is not equivalent to verifying the microphone, shared screen, or recording. Clearly distinguish automated checks from checks that still require the GM or participants.
7. **Safe, understandable operation.** Do not silently override existing user settings, share GM-only links, start unwanted recordings, or disrupt unrelated applications.
8. **Small MVP, extensible scope.** Optimize for making the existing workflow easy to launch, not for designing a universal orchestration platform.

## 5. Users and usage scenarios

### 5.1 Primary user

A technically capable GM who runs online narrative tabletop RPGs, uses multiple desktop applications, and may alternate between computers. Technical familiarity does **not** imply willingness to maintain per-game scripts or duplicate large application configurations.

### 5.2 Core scenarios

**A. Start a familiar game on the usual desktop.**  
The GM selects “Samosbor” and launches the saved setup, without reopening the same pages and reconstructing settings manually.

**B. Start the same game on another machine.**  
The game-specific links and presets remain recognizable; machine-specific devices and capabilities are handled separately and gaps are reported clearly.

**C. Update a game.**  
The GM can change a playlist, VDO.Ninja URL, OBS scene collection, or required application without learning a custom set of options for that application's internal settings.

**D. Send player invitations.**  
After launch, the GM sees player-facing links, clearly distinguished from private GM links, and can easily copy a coherent invitation.

**E. Diagnose a broken setup.**  
The launcher makes it apparent whether a missing tool, resource, local device, permission, or manual action is preventing readiness.

**F. Maintain multiple campaigns.**  
The GM can switch between different campaigns (for example, Samosbor and Frostpunk) while using the same common workstation environment.

## 6. Scope and prioritization

### 6.1 MVP — Required

- Discover and select a saved **game preset**.
- Apply the relevant **machine-specific configuration** without unnecessary duplication of game settings.
- Make the required applications and dependencies available through a **Nix-managed environment**.
- Launch required local applications and open the game’s configured URLs/resources.
- Reuse **native application configurations** wherever applicable.
- Display the **player-facing invitation** after launch, including one or several player links.
- Provide an easy means of copying the invitation or individual links.
- Indicate basic launch outcomes, errors, and any remaining manual checks.
- Allow presets to be created and updated without significant bespoke scripting.
- Provide understandable documentation and examples for adding a second game and a second machine.

### 6.2 Near-term candidates — Proposed, not MVP commitments

- **Session-specific overrides (high-priority next increment after MVP):** Keep a reusable game preset as the default, but allow each new session to change selected resources (especially VDO.Ninja links, music playlists, maps or other URLs) without editing or duplicating the game preset. Carry forward all unchanged settings. The GM should not have to reconfigure the game from scratch to start the next session.
- Configurable launch presets/variants within a game (e.g., different presentation or communication setups).
- A compact menu or dashboard for launch/status/links.
- A more thorough preflight checklist for audio, browser sharing, and OBS.
- EasyEffects NPC-voice preset selection.
- Standardized OBS recording setup and separate audio-track capture.
- Hotkeys for common voice and music actions.
- Better handling of repeated launches, recovery, and stopping only launcher-owned processes.

### 6.3 Future possibilities — Out of initial scope

- **Automated setup verification (desired, not MVP):** After launching, confirm not only that OBS and other applications are running, but that OBS is actually recording the intended content, audio is present and balanced, and the live/recorded audio has no obvious echo or duplicated sources. Report any issues that cannot be verified automatically as explicit manual checks. This is a user-requested future capability, **not a requirement for the MVP**.

- Replacing Discord dice rolls with a dedicated shared roller and logging rolls.
- A session event journal with bookmarks and annotations.
- YouTube track-title capture and synchronization with recordings.
- Automated audio-mix presets and advanced routing.
- A GM control panel, remote/mobile controller, or integrated session timeline.
- Automatic post-session summaries or transcript analysis.

These ideas are relevant to future compatibility but **should not drive MVP complexity**.

## 7. Functional requirements

### FR-01 — Select a game preset (MVP)

**What:** The launcher must list available game presets with clear names and let the GM choose one to start. It should also support direct selection when the game is already known.

**Why:** The GM runs more than one campaign and should not have to reconstruct a launch procedure from memory.

**Acceptance criteria:**
- At least two distinct game presets can be defined and selected.
- The selected game is clearly identified before and after launch.
- An invalid or unavailable preset produces a comprehensible error.

### FR-02 — Support game-specific and machine-specific settings (MVP)

**What:** A game preset represents the reusable requirements of a campaign. Machine settings represent local differences such as device identity, installed capabilities, available displays, and output paths. Machine-specific overrides may be used where necessary.

**Why:** Switching computers should not require creating and keeping in sync full copies of every campaign configuration.

**Acceptance criteria:**
- A single game definition can be used with at least two machine configurations.
- Machine differences do not alter player invitation URLs unless explicitly overridden.
- The effective game/machine selection is visible to the GM.
- An unresolved or incompatible machine requirement is surfaced rather than silently ignored.

**Decided:** Both. The machine is chosen automatically by hostname, and the GM can choose one by hand. A computer that matches no machine preset is an error, never a guess.

### FR-03 — Rely on Nix for reproducible software availability (MVP)

**What:** The project must offer a Nix-managed way to obtain the launcher and the required applications/dependencies for supported machines. Versions and compatibility should be controlled enough to avoid unexplained drift between machines.

**Why:** The user wants to avoid arriving at game time to discover that an application, plugin, or dependency is missing.

**Acceptance criteria:**
- A documented new-machine setup brings in the supported required software without individually hunting down dependencies.
- The product can identify and report requirements that provisioning alone cannot satisfy (e.g., device-specific permissions).
- Supported systems and known limitations are documented.

**Decided:** Linux only. Nix packages the launcher on every machine. On NixOS a module also installs the applications. On other distributions (the main desktop is Arch) the applications come from the system's own packages or Flatpak, and the launcher checks that they are present. This narrows the first acceptance criterion on non-NixOS machines; see §17.6.

### FR-04 — Launch the configured environment (MVP)

**What:** The launcher starts configured applications and opens the GM’s chosen game resources, including browser links. It should support the existing roles of participant connection, game presentation, music, and recording without assuming every game uses identical tools.

**Why:** Most repetitive time is spent preparing the same constellation of apps and pages.

**Acceptance criteria:**
- A preset can request OBS and Chromium-based resources.
- Distinct URLs for participant communication, presentation, and music can be supplied.
- A game can omit an optional component without breaking unrelated launch steps.
- Launch failures are attributed to the specific affected component.
- Complete VDO.Ninja URLs are preserved, including their native parameters.

**Decided:** Window placement is not controlled; on Wayland a launcher cannot place other applications' windows. An OBS that is already running is left untouched and reported, because its profile and scene cannot be changed from outside. Browser pages open in a dedicated browser profile whether or not that browser is already running.

### FR-05 — Reuse native application configuration (MVP)

**What:** The launcher should be able to reference existing native configuration assets and named presets used by external applications, where suitable. It should not require the GM to restate application-specific settings using an invented product schema.

**Why:** Reduces maintenance, duplication, and the chance that the launcher falls behind external software.

**Examples of intended behavior:**
- **VDO.Ninja:** accept complete URLs, as authored in VDO.Ninja.
- **OBS:** select/use existing OBS profiles or scene collections where practical.
- **EasyEffects:** select/use native effect presets when voice processing is introduced.
- **YouTube:** open an ordinary playlist or video link, without recreating YouTube controls.

**Acceptance criteria:**
- The GM can change a VDO.Ninja quality/behavior setting by replacing its URL, without editing a separate launcher video-quality field.
- Native configuration references are discoverable or documented.
- The product clearly reports missing referenced presets/assets.

**Decided:** For OBS, a game names a scene and optionally a profile and scene collection, by the names OBS shows; the launcher starts OBS with them and checks, read-only, that they exist. Starting a recording is optional and off by default. EasyEffects is not part of the MVP.

### FR-06 — Provide player invitations after launch (MVP)

**What:** Once a game has been launched, the launcher displays one or more **player-facing** links and a copyable invitation message. A game may require different links for different player roles.

**Why:** Players need actionable connection instructions; the GM should not search previous chat messages or manually extract URLs every session.

**Acceptance criteria:**
- Every game can define at least one player link.
- Multiple labeled links are supported, such as “Connect to voice/video,” “Dice,” or “Spectator view.”
- Player URLs remain distinct from GM/private launch URLs.
- The GM can copy an individual link and the complete invitation without manually selecting large blocks of terminal output.
- The invitation remains accessible after its initial display during the launcher’s active use.
- A missing invitation link is reported as a configuration issue rather than replaced with a guessed URL.

**Decided:** Display and copy only. Because each player has their own link, the invitation is one message per named player: their own link followed by the links everyone shares. Each message is copied separately. A game without per-player links gets a single message.

### FR-07 — Provide meaningful status and errors (MVP)

**What:** The launcher should report whether each requested component was started, failed, or still requires attention. It should not claim that player audio or recording quality has been verified merely because the relevant process exists.

**Why:** A visually successful startup can conceal broken sound, missing screen-sharing permissions, or incorrect OBS inputs.

**Acceptance criteria:**
- The GM can identify which parts of the configured environment were attempted and which failed.
- Errors suggest a next action in ordinary language.
- Manual checks are explicitly identified as manual.
- The launcher does not claim full readiness when essential verification is unavailable.

**Decided:** The MVP checks only what it can know for certain: whether each command ran, failed or was not found; whether the presets are valid; whether the applications are installed; whether the OBS names in a preset exist; and whether a game has player links. Everything about sound, screen sharing and recording is a manual check, written in the game preset and listed after every launch.

### FR-08 — Make presets easy to maintain (MVP)

**What:** Presets must be human-readable, easy to update, and reasonably concise for routine changes. Users should be able to add or modify a game without creating a new program or extensive scripts.

**Why:** Ease of modification is a central product goal, not an optional polish feature.

**Acceptance criteria:**
- Updating a player link or YouTube playlist is a small, localized edit.
- Adding a new game does not require editing shared launcher logic.
- Adding a machine does not require copying every game's full configuration.
- The project provides a minimal example game, a second game example, and guidance for common changes.
- Configuration mistakes are reported with enough context to fix them.

**Decided:** Presets are plain TOML files edited by hand and read at launch, so an edit takes effect without rebuilding anything. There is no built-in editor.

### FR-09 — Avoid disruptive or unsafe actions (MVP)

**What:** Launching a preset must not silently overwrite unrelated personal application settings, disclose private GM links to players, or terminate applications that the launcher does not own.

**Why:** The GM may use OBS/Chromium for purposes outside RPGs, and player invitations can contain role-specific access details.

**Acceptance criteria:**
- The product distinguishes GM-only and player-facing resources.
- No recording is initiated without an explicit or clearly configured user choice.
- Existing application sessions are not unexpectedly destroyed.
- Destructive cleanup actions are explicit and predictable.

## 8. Interaction model — Initial recommendation, not a fixed implementation

The launcher needs a **simple entry point with a preset list, launch action, status, and shareable invitation**. A lightweight CLI with interactive selection is a plausible first interface; GUI or web UI remains possible if usability warrants it.

**Decided:** A command-line program. Run without arguments it lists the games, launches the chosen one, and stays open with a small menu for copying each player's invitation and re-showing the status. The invitation can also be shown or copied at any later time, and a separate check command reports problems with presets and installed software before game time.

Example **behavioral sketch** (not prescribed syntax):

```text
RPG Launcher

Choose game:
  • Samosbor 2
  • Frostpunk

Selected: Samosbor 2
Machine: Desktop

Starting game environment...
  OBS: started
  Player connection window: opened
  Presentation: opened
  Music: opened
  Audio / screen sharing: manual verification needed

PLAYER INVITATION
  Join game: <player-specific VDO.Ninja URL>
  Roll dice: <configured dice link>
  Note: Please use headphones.

Actions: Copy invitation | Show status | Exit
```

**Important:** These are illustrative labels; the PRD does not require this exact layout or command syntax.

## 9. Preset concept and information boundaries

A preset may combine:

| Information | Belongs to | Rationale |
|---|---|---|
| Campaign name | Game | Common identity across machines |
| Player connection URLs | Game, unless explicitly overridden | Invitation should not vary accidentally with hardware |
| GM-specific VDO.Ninja URLs | Game or role-specific variant | Avoid mixing GM and player access |
| Music URLs/playlists | Game | Campaign atmosphere |
| Presentation links/resources | Game | Campaign content |
| OBS profile/scene collection reference | Game or shared reusable preset | Use existing OBS configurations |
| Voice effect preset references | Game or shared reusable preset | Reuse native effects rather than redefine DSP |
| Microphone / output device mapping | Machine | Hardware differs |
| Display/window preferences | Machine or override | Monitor layout differs |
| Recording destination/capability | Machine or override | Storage and encoding differ |
| Invitation text | Game | Stable player-facing instructions |

**Deliberate non-requirement (confirmed design preference):** The product should not introduce a custom DSL that mirrors OBS, Chromium, VDO.Ninja, or EasyEffects settings when a native configuration or URL can be used instead. The launcher needs only minimal information to select, compose and launch those native resources.

### Game versus session

**Confirmed:** Presets describe **games, not individual sessions**, and must be reusable across many sessions. **Next priority after MVP:** Session-specific values should be easy to supply or update without revisiting the whole game setup. For example, session B can use new VDO.Ninja or music links while retaining session A’s game-level OBS scene collection, applications, voice presets, and machine settings. This is an explicit near-term need, **not a required MVP feature**. Whether changes are saved, carried forward, or reset between sessions is unresolved. **Confirmed on 2026-11-11:** the VDO.Ninja room and password stay the same for a whole campaign; what changes between sessions is the music and the map links. Session notes, logs, and recordings remain out of scope for the MVP preset system.

### Preset variants

**Proposed:** A game may optionally expose a small number of named variants, for example “desktop stream” or “minimal laptop.” Whether this is represented as machine overrides, distinct presets, or selectable variants is intentionally left to design, provided the GM does not have to duplicate unchanged information.

**Decided for the MVP:** Variants are not built. A machine preset can override parts of a game for that machine, which covers the "minimal laptop" case. Alternative links for the same purpose are kept as comments in the game file.

## 10. Non-functional requirements

| ID | Requirement | Why / expected quality |
|---|---|---|
| NFR-01 | Low setup effort | The normal workflow should take substantially fewer manual actions than opening and configuring each application individually. |
| NFR-02 | Reproducibility | A supported new machine should obtain required software and configurations without an undocumented manual dependency hunt. |
| NFR-03 | Low maintenance | Routine changes to links, profiles, and presets should not require changing launcher code. |
| NFR-04 | Transparency | Status must distinguish success, failure, and unverified conditions. |
| NFR-05 | Resilience | A failed optional component must not make all unrelated components unusable. |
| NFR-06 | Privacy | GM-only links, room credentials, private recordings, and local data must not appear in player invitations by accident. |
| NFR-07 | Non-intrusiveness | Ordinary desktop applications remain independently usable outside launcher-managed games. |
| NFR-08 | Extensibility | Future recording controls, audio automation, journaling and dice integration should be possible without invalidating existing game definitions. |
| NFR-09 | Documentation | A new developer should understand the product intent and a user should understand how to add/edit games and machines. |

### Suggested success measures — Proposed

- A repeat game launch requires **one selection and one launch action**, aside from genuine permissions/verification.
- Adding a new player link or changing a YouTube playlist requires **no custom code**.
- A supported second machine can run an existing game without cloning the game configuration.
- Player invitation links are available immediately after launch and can be copied in one action.
- Failed components are discoverable without inspecting multiple application logs.
- The GM reports a meaningful reduction in pre-game setup time and fewer forgotten preparation steps.

No numerical launch-time or reliability targets are set yet; measure a baseline before deciding on hard thresholds.

### Future requirement — End-to-end setup verification (post-MVP)

**What:** The launcher should be able to assess whether the game environment is functioning correctly *after startup*, not merely whether applications opened. The desired checks include OBS startup and actual recording state, presence of intended visual/audio sources, microphone and music capture, and detection of possible echo, feedback, duplicated audio, or other capture-quality problems.

**Why:** A session can appear ready while the recording is unusable or players hear echo. Detecting this before gameplay would reduce wasted sessions and the GM's manual verification burden.

**Acceptance direction (to refine when this feature is scoped):**
- Distinguish **application started**, **recording active**, **signal detected**, and **content/quality verified**; never present these as equivalent.
- Surface actionable warnings for missing audio, missing sources, suspicious duplication or potential echo when detectable.
- Show clearly what still needs a human check (especially what remote participants actually hear and see).
- Avoid false assurances: echo-free playback and recording correctness must not be claimed without adequate evidence.
- Make verification usable independently of the chosen game preset and physical machine, while acknowledging hardware-dependent checks.

**Open:** What constitutes sufficient evidence of correct recording, and how should possible echo be assessed? Some forms of echo cannot be established reliably without remote participant feedback or an explicit test recording. No particular technique is mandated by this PRD.

## 11. Dependencies and constraints

- **Nix is part of the requested product direction.** Exact packaging strategy and supported OS combinations are to be selected by developers.
- **External applications retain authority over their settings.** Their versions, permissions, and formats may change over time.
- **VDO.Ninja links may carry sensitive role/room information.** Player and GM resources must be distinguished.
- **Desktop media permissions can require human interaction.** Particularly microphone and screen sharing; the product must not promise complete unattended setup.
- **Audio device names and availability differ by computer.** Portability must account for device-specific adaptation.
- **Existing Chromium/OBS usage may conflict with RPG use.** Startup behavior must avoid unwanted disruption.
- **OBS recording and player streaming are separate concerns.** Starting both applications does not alone guarantee correct capture or sound mixing.

## 12. Explicitly out of scope for the MVP

- A complete VTT platform or tabletop scene editor.
- A replacement for the full OBS interface.
- Reimplementing VDO.Ninja video/audio configuration in launcher settings.
- A comprehensive cross-platform audio mixing engine.
- A custom dice backend or roll rules engine.
- Automated transcription, editing, or summarization of recordings.
- End-to-end automatic OBS/stream/audio verification, including echo detection or proof of recording quality (explicitly planned for consideration after MVP).
- Automatic posting to Discord or any messaging service.
- Fully hands-free interaction with browser permission prompts.

## 13. Open questions and information gaps

**Superseded in version 0.2.** Most of these questions were answered on 2026-11-11. The answers are in §17.7, in the same order, and what is still open is in §17.8. The table below is kept as it was written in version 0.1; its "current assumption" column is no longer current.

These questions should be resolved with the GM during discovery. None should silently be treated as a confirmed implementation requirement.

| Priority | Question / gap | Current assumption or impact |
|---|---|---|
| High | **Target machines/OS:** Arch Linux only, multiple Linux distributions, NixOS, or Windows too? | Linux-first is likely, but unconfirmed. Affects packaging and portability commitment. |
| High | **Exact list of applications to launch in MVP:** OBS, EasyEffects, Chromium, any others? | OBS and Chromium are definite current tools; EasyEffects is desired for voices but its MVP installation requirement needs confirmation. |
| High | **Current VDO.Ninja topology:** Which exact GM, participant, screen-share, and music-stream links exist? Which are private? | Needed to create a realistic example preset and avoid leaking GM links. Do not embed real credentials in shared PRD. |
| High | **Meaning of “works out of the box”:** Is installing/opening enough, or must OBS sources, audio routing, presets and recording paths be configured automatically? | Determines MVP boundary and what readiness can honestly guarantee. |
| High | **Preset edit UX:** Is editing a short Nix/text file acceptable, or is a built-in editor required? | MVP assumes concise file-based updates; “easy” needs user validation. |
| Medium (post-MVP, high priority) | **Session overrides:** Which links/resources typically change each session? Should changes apply only once, be remembered for the next session, or be saved as named session-specific values? | Session-specific changes must not require copying or rewriting a game preset; precise editing/persistence UX is open. |
| Medium | **Browser behavior:** Separate Chromium windows, tabs, dedicated profile, existing session, or mixed? | Impacts reliability and personal-browser isolation. |
| Medium | **Player invitation format:** Plain text, Markdown, clickable menu, QR code, or multiple role-specific invitations? | MVP assumes readable text with copy functionality. |
| Medium | **Native OBS assets:** Which profiles, scene collections, plugins, and sources are needed across machines? | Current production configuration not inventoried. |
| Medium | **Audio arrangement:** How are mic, YouTube music, and participants routed into OBS and VDO.Ninja today? | Required before promising automated verification or audio setup. |
| Low (post-MVP) | **Verification expectations:** Which sources and recordings must be checked, what would count as unacceptable echo, and is a short test recording or player confirmation acceptable? | Define when scoping future automated setup verification; no impact on MVP commitment. |
| Medium | **Already-running behavior:** Reuse apps, open a new isolated instance, or prompt? | Product must avoid duplication and disruption. |
| Medium | **Stop/relaunch expectations:** Should exiting the launcher keep streams/OBS alive? What counts as launcher-owned? | MVP should be safe but exact lifecycle semantics are open. |
| Medium | **Game resources:** Are map/art files local, cloud-hosted, or both? | Affects resource portability and missing-file reporting. |
| Low | **Interface choice:** CLI-only first, TUI, GUI, or web dashboard? | CLI/TUI is a recommendation, not an agreed requirement. |
| Low | **Sharing method:** Copy links manually or integrate messaging later? | Copy/display only for MVP. |
| Low | **Presets and versioning:** Should changes be shared via Git, NAS, or other synchronization? | Reproducibility is required; synchronization mechanism is open. |
| Low | **Multi-GM / multiple user support:** Is the tool exclusively single-GM? | Assume single GM for MVP. |

## 14. Proposed delivery milestones

These describe observable outcomes, **not mandated technical work packages**.

### Milestone A — Launch and invite

A user can select a game, start its configured applications/resources, view the outcome, and copy the correct player invitation. At least one real campaign preset is demonstrated.

**Status:** Built; see §17.9 for what has and has not been tried.

### Milestone B — Reproducibility and second machine

The same game can be launched on a second supported machine via the Nix-managed setup, with documented machine-specific differences and no duplicated campaign definition.

### Milestone C — Native presets and refinement

The launcher can refer to the required native OBS/EasyEffects configurations, with clear errors for missing assets and a documented editing workflow. The team evaluates whether improved status checks or a richer interface are warranted.

### Milestone D — Session-specific changes (next priority after MVP)

A new session can use updated links or other session-specific resources while retaining the selected game preset and machine configuration unchanged. The update experience should be lightweight; persistence behavior will be decided with the GM. This is the preferred next increment after the MVP, not part of MVP acceptance.

### Later milestones — Optional

Voice switching, audio automation, **automated setup/OBS recording verification and potential echo detection**, recording quality-of-life controls, session journal/music history, and shared dice integration.

## 15. Definition of done for the MVP

The MVP is acceptable when all of the following are demonstrable:

- [ ] The GM can choose between at least two named game configurations.
- [ ] At least one game works with two machine profiles/configurations without maintaining two full game copies.
- [ ] Required software is available on supported machines: installed by the Nix module on NixOS, and taken from the system and verified by the launcher's check command elsewhere. *(Reworded in version 0.2; see §17.6.)*
- [ ] A selected game launches its requested applications and opens the exact configured URLs.
- [ ] Complete VDO.Ninja links can be supplied unchanged; the launcher does not require custom video/audio parameters.
- [ ] Native application configuration references are supported for the MVP's agreed integrations.
- [ ] The launcher displays clearly labeled player links and allows copying a complete invitation.
- [ ] GM-only links are not included in the invitation by default.
- [ ] Missing dependencies, unavailable resources and failed launches are surfaced clearly.
- [ ] The documentation shows how to add a game, modify a link, and adapt the setup to a second machine.
- [ ] The team records which verification steps remain manual and does not present them as automated successes.

## 16. Developer handoff notes

This PRD intentionally leaves room for engineering decisions. In particular, it does **not** prescribe the launcher's programming language, internal architecture, CLI framework, exact Nix module design, process supervision strategy, or how native configuration files are deployed. The choices made for these since version 0.1 are recorded in §17.5; they are engineering choices and can change without changing the requirements.

Before coding, the team should validate the **High-priority open questions** and inspect a representative existing game setup. Where decisions are not yet possible, prefer the smallest behavior that satisfies the documented requirements and can evolve without forcing users to rewrite their game presets.

**Central product test:** Can the GM start a known campaign, on a supported computer, with very little preparation and immediately obtain the correct links for players—without maintaining a second configuration system for all the underlying applications?

## 17. Agreed decisions and GM preferences (2026-11-11)

This section records what the GM and the developer agreed after version 0.1. It is authoritative: where it differs from older wording above, this section wins. Anything not covered here is unchanged from version 0.1.

How to use the launcher and how to write presets is in [README.md](../README.md). This section says what was decided and why.

### 17.1 GM preferences

Stated by the GM during the design discussion. Treat them as constraints when making later choices.

- **Simplicity over power at this stage.** Prefer the setup with fewer moving parts, even if it leaves a manual step.
- **YouTube stays the primary music source.** Playing local tracks as well would be welcome but is not critical.
- **Open to a more convenient music setup** than sharing a browser tab, as long as it stays simple.
- **Presets are private.** They are kept out of the launcher's version control because the links carry room names and passwords.
- **Each player always gets the same personal link.** Player names are fixed in the game preset.
- **Game pages open in their own browser profile,** separate from everyday browsing.
- **The code must stay extendable.** New kinds of things to launch are added as modules, without reworking the launcher.
- **Work is committed to a local git repository.** There is no remote yet.
- **Left out on purpose:** the Google Drive folder of game files, and Roll20, which is no longer used.
- **Planned by the GM:** Excalidraw in place of Draw.io, and EasyEffects voice effects for NPCs.

### 17.2 Product decisions

| Topic | Decision |
|---|---|
| Platforms | Linux only. NixOS and non-NixOS machines are both targets. |
| What Nix provides | The launcher on every machine. On NixOS a module also installs OBS and Chromium. On other distributions the applications come from the system (packages or Flatpak) and the launcher's check command verifies them. |
| Applications in the MVP | OBS, Chromium, and any other application a game names (Discord today). EasyEffects is not included. |
| Interface | Command line: a game picker, per-component status, and a menu after launch for copying invitations. |
| Game and machine | One file per game and one per machine. A machine file lists only what differs on that computer and can override parts of one game. Game files are never copied per machine. |
| Machine selection | By hostname, or chosen by hand. No match is an error. |
| Browser | A dedicated Chromium profile. Pages open as tabs in one new window; a page can ask for its own window. On each machine the GM signs in to Google and YouTube in that profile once. |
| OBS | A game names an OBS scene and, optionally, a profile and scene collection. The VDO.Ninja scene link stays inside OBS as a browser source. Each machine keeps its own OBS settings under the same names; the launcher never writes to them or copies them between machines. |
| OBS already running | Left untouched and reported. |
| Recording | Started only when a game explicitly asks for it. Off by default. |
| Invitations | Plain text. One message per named player: their own link, then the links everyone shares. Display and copy only. |
| Keeping GM links private | By structure. Invitations are built only from the invitation part of a game preset. Pages the GM opens are kept in a different part and have no path into an invitation. |
| Manual checks | Written in the game preset next to the thing they concern, and listed after every launch. The launcher never reports sound, screen sharing or recording as verified. |
| Failures | One component failing does not stop the others. Each failure names its component and suggests what to do. |
| Stopping | The launcher never stops an application. Quitting the launcher leaves everything running. |
| Window placement | Not controlled. |
| Music | The current flow is kept: YouTube in a tab, shared from the VDO.Ninja music page. The steps are listed as manual checks. |

### 17.3 Presets

- **Format:** TOML, read at launch. No rebuild after an edit.
- **Layers:** the effective game is the game file with the machine's overrides for that game merged on top. Entries are named (for example a page called `music`), so an override can change one entry and inherit the rest. Session overrides (Milestone D) will be one more layer of the same kind.
- **URLs:** used exactly as written. The launcher never parses or rewrites them.
- **Where they live:** in a directory given by `--presets`, by `$RPG_LAUNCHER_PRESETS`, or by default `~/.config/rpg-launcher`. On the main desktop they are in `presets/` inside the launcher checkout. That directory is ignored by the launcher's git repository and is its own local git repository.
- **Examples:** `examples/presets` holds two games and two machines with placeholder links. Real links never go there.

### 17.4 The main desktop, as found on 2026-11-11

| Item | State |
|---|---|
| System | Arch Linux, GNOME on Wayland, hostname `archlinux` |
| Nix | 2.26, with flakes enabled |
| OBS | Flatpak `com.obsproject.Studio`. Settings under `~/.var/app/com.obsproject.Studio/config/obs-studio`. |
| OBS content | One profile and one scene collection, both named `Untitled`. One scene per game, plus an experimental one for Samosbor, each with a browser source for that game's VDO.Ninja scene link at 1920×1080 with "Control audio via OBS" on. |
| Chromium | System package |
| Discord | Flatpak `com.discordapp.Discord` |
| EasyEffects | System package, not used by the launcher |

### 17.5 Engineering choices

These can change without changing the requirements.

- **Language:** Python 3.11 or later, standard library only.
- **Components:** each kind of thing a game can start is one module in `src/rpg_launcher/components` behind a shared interface (`base.py`). OBS, plain applications and browser pages are the three built in. Adding one means writing a module and adding it to the list in `components/__init__.py`. Loading components from outside the repository is not supported.
- **Invitations are not a component.** They stay in the core so the privacy rule in §17.2 lives in one place.
- **Nix:** a flake with the package, a development shell and a NixOS module (`flake.nix`, `nix/`). The module takes OBS and Chromium from the system's own nixpkgs.
- **Tests:** standard-library `unittest` in `tests/`, run as part of the Nix build.
- **Processes:** applications are started detached and are not supervised afterwards.

### 17.6 Differences from version 0.1

- **Nix on non-NixOS machines (FR-03, §15).** Version 0.1 asked for required software to be available through the Nix environment. On Arch the applications come from the system instead and are verified by the launcher. Running the nixpkgs builds of OBS and Chromium on Arch would need graphics-driver wrapping and would not use the existing Flatpak OBS settings.
- **Per-player invitations (FR-06).** Version 0.1 described one invitation. The GM gives each player their own link, so there is one message per player.
- **Preset variants (§9).** Not built.

### 17.7 Answers to the questions in §13

In the order of the table in §13.

| Question | Answer |
|---|---|
| Target machines/OS | Linux only; NixOS and non-NixOS. Windows is out. |
| Applications to launch in the MVP | OBS, Chromium, and any application a game names. Not EasyEffects. |
| Current VDO.Ninja topology | Documented in §3.2. The director and scene links are private; players get one link each. |
| Meaning of "works out of the box" | Installing and opening, with existing OBS scenes selected by name. The launcher does not create OBS sources, audio routing or recording paths. |
| Preset edit UX | Hand-edited TOML files. |
| Session overrides | Partly answered: the room stays the same for a campaign; music and map links change. How changes persist is still open. |
| Browser behavior | A dedicated profile; tabs in one new window, with own windows on request. |
| Player invitation format | Plain text, one message per player. |
| Native OBS assets | The main desktop is inventoried in §17.4. Other machines and OBS plugins are not. |
| Audio arrangement | Partly answered. Music reaches players through the VDO.Ninja music page. OBS takes its sound from the browser source; its other sources, including the microphone, are muted to avoid doubled sound. Device-level routing is not documented. |
| Verification expectations | Still open; after the MVP. |
| Already-running behavior | OBS is left untouched and reported. Browser pages open in the dedicated profile either way. Other applications are simply started. |
| Stop/relaunch expectations | The launcher never stops anything. Launching again opens the pages again. |
| Game resources | Cloud-hosted today (Draw.io on Google Drive, YouTube). Local files are not managed. |
| Interface choice | Command line. |
| Sharing method | Copy only. |
| Presets and versioning | A private directory under local git. Synchronising it between machines is still open. |
| Multi-GM | Not discussed; the single-GM assumption stands. |

### 17.8 Still open

- **Session overrides:** whether a session's changes apply once, are remembered, or are saved by name.
- **Music through a virtual audio device:** would remove the share-tab and mute-tab steps and allow local tracks. Untested: sending one browser window's sound to a chosen device, and VDO.Ninja picking that device by itself.
- **OBS recording settings:** the GM's notes ask for MKV, "Indistinguishable Quality" and 30 FPS; the `Untitled` profile records hybrid MP4, "High Quality, Medium File Size" and 60 FPS. A dedicated profile that games name would settle it.
- **Synchronising presets between machines.**
- **OBS settings on a second machine:** each machine needs scenes with the same names; nothing creates them yet.
- **End-to-end verification** of sound and recording (§10), after the MVP.

### 17.9 What has been built and tried

As of 2026-11-11:

- **Built:** launching a game, showing and copying invitations, the check command, listing games and machines, the Nix package and the NixOS module.
- **Tried:** the automated tests, also inside the Nix build; the interactive flow with stand-in applications; the check command against the real desktop, which finds the applications and the OBS scene.
- **Not tried yet:** a real launch of OBS, Discord and Chromium on the desktop; any NixOS machine; a real session.
- **Presets written:** Samosbor 2 and the desktop machine. Player names in it are placeholders. Frostpunk has no preset yet; only its OBS scene is known.

### 17.10 Order of later work

1. Try a real launch on the desktop, then on a NixOS machine (Milestone B).
2. Session overrides (Milestone D).
3. Music through a virtual audio device, after a short trial.
4. EasyEffects voice presets.
