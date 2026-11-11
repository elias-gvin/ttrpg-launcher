# RPG Session Launcher — Product Requirements Document

**Status:** Draft for developer review  
**Version:** 0.1  
**Date:** 2026-11-10  
**Product type:** Local RPG session launcher and environment manager  
**Primary user:** Game Master (GM) running online tabletop RPG sessions

> **Document intent:** Describe **what** the product should achieve and **why**, not prescribe its internal implementation. Items labeled **Confirmed** reflect the current discussion; items labeled **Proposed** need validation. Questions and unknowns are explicitly marked **Open**.

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

The exact interaction (CLI, GUI, web interface) is **not yet decided**.

## 3. Current environment and workflow

### 3.1 Known toolchain — Confirmed unless marked

| Area | Current tool / approach | Purpose | Notes |
|---|---|---|---|
| Operating system | Arch Linux desktop | Main GM workstation | Other machines are also available; target coverage is open. |
| Browser | Chromium | Hosts multiple game-related pages | Multiple independently useful pages/windows. |
| Player communication | VDO.Ninja | Connects participants and transports media | Existing URLs can include detailed application-specific settings. |
| Visual presentation | Draw.io / Excalidraw, shown through Chromium and VDO.Ninja | Displays art, maps, and in-game material | Content is presented as a browser view; exact per-game pages vary. |
| Music | Regular YouTube in Chromium, audio shared through VDO.Ninja | Background music / atmosphere | The video itself is not intended as the player-facing presentation. |
| Dice | Discord dice bot | Player/GM dice rolls | Replacement is desirable eventually, not a launch prerequisite. |
| Recording | OBS Studio | Records sessions | Audio balance and recording checks currently require attention. |
| Microphone / effects | Existing microphone and audio interface; EasyEffects considered | GM voice, future NPC voice presets | EasyEffects NPC effects are **planned**, not established as an existing production workflow. |
| Software provisioning | Nix proposed; NixOS is used on at least one other device | Reproducible dependencies and application availability | Nix is an agreed direction for this product, not a description of the present desktop setup. |

### 3.2 Current manual preparation — Confirmed at the goal level

The GM launches Chromium and opens the required VDO.Ninja links, visual-presentation content, YouTube, and other game pages; launches OBS; checks media sharing and recording; and adjusts audio. Player links are handled separately. The exact number of tabs, display layout, selected OBS sources, and audio-routing topology have **not** been fully documented.

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

**Open:** Whether machine selection is automatic, manual, or both.

### FR-03 — Rely on Nix for reproducible software availability (MVP)

**What:** The project must offer a Nix-managed way to obtain the launcher and the required applications/dependencies for supported machines. Versions and compatibility should be controlled enough to avoid unexplained drift between machines.

**Why:** The user wants to avoid arriving at game time to discover that an application, plugin, or dependency is missing.

**Acceptance criteria:**
- A documented new-machine setup brings in the supported required software without individually hunting down dependencies.
- The product can identify and report requirements that provisioning alone cannot satisfy (e.g., device-specific permissions).
- Supported systems and known limitations are documented.

**Open:** Target OS distribution(s) and whether support is Linux-only initially. Nix is an explicit product requirement; no specific module, flake structure, or provisioning mechanism is mandated by this PRD.

### FR-04 — Launch the configured environment (MVP)

**What:** The launcher starts configured applications and opens the GM’s chosen game resources, including browser links. It should support the existing roles of participant connection, game presentation, music, and recording without assuming every game uses identical tools.

**Why:** Most repetitive time is spent preparing the same constellation of apps and pages.

**Acceptance criteria:**
- A preset can request OBS and Chromium-based resources.
- Distinct URLs for participant communication, presentation, and music can be supplied.
- A game can omit an optional component without breaking unrelated launch steps.
- Launch failures are attributed to the specific affected component.
- Complete VDO.Ninja URLs are preserved, including their native parameters.

**Open:** Exact expected window placement and behavior when a required application is already running.

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

**Open:** Which native OBS/EasyEffects configuration operations are essential for the first release versus later integrations.

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

**Open:** Should the product merely display/copy invitations, or should it support sending them to Discord/other messengers later? **Assumption for MVP: display and copy only.**

### FR-07 — Provide meaningful status and errors (MVP)

**What:** The launcher should report whether each requested component was started, failed, or still requires attention. It should not claim that player audio or recording quality has been verified merely because the relevant process exists.

**Why:** A visually successful startup can conceal broken sound, missing screen-sharing permissions, or incorrect OBS inputs.

**Acceptance criteria:**
- The GM can identify which parts of the configured environment were attempted and which failed.
- Errors suggest a next action in ordinary language.
- Manual checks are explicitly identified as manual.
- The launcher does not claim full readiness when essential verification is unavailable.

**Open:** Which automated health checks can be delivered reliably in the MVP.

### FR-08 — Make presets easy to maintain (MVP)

**What:** Presets must be human-readable, easy to update, and reasonably concise for routine changes. Users should be able to add or modify a game without creating a new program or extensive scripts.

**Why:** Ease of modification is a central product goal, not an optional polish feature.

**Acceptance criteria:**
- Updating a player link or YouTube playlist is a small, localized edit.
- Adding a new game does not require editing shared launcher logic.
- Adding a machine does not require copying every game's full configuration.
- The project provides a minimal example game, a second game example, and guidance for common changes.
- Configuration mistakes are reported with enough context to fix them.

**Open:** Whether editing the underlying files is sufficient or an interactive preset editor is desired. **Assumption for MVP: file-based editing is acceptable, provided it is simple and well documented.**

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

**Confirmed:** Presets describe **games, not individual sessions**, and must be reusable across many sessions. **Next priority after MVP:** Session-specific values should be easy to supply or update without revisiting the whole game setup. For example, session B can use new VDO.Ninja or music links while retaining session A’s game-level OBS scene collection, applications, voice presets, and machine settings. This is an explicit near-term need, **not a required MVP feature**. Whether changes are saved, carried forward, or reset between sessions is unresolved. Session notes, logs, and recordings remain out of scope for the MVP preset system.

### Preset variants

**Proposed:** A game may optionally expose a small number of named variants, for example “desktop stream” or “minimal laptop.” Whether this is represented as machine overrides, distinct presets, or selectable variants is intentionally left to design, provided the GM does not have to duplicate unchanged information.

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
- [ ] Required software is reproducibly available through the documented Nix environment on supported machines.
- [ ] A selected game launches its requested applications and opens the exact configured URLs.
- [ ] Complete VDO.Ninja links can be supplied unchanged; the launcher does not require custom video/audio parameters.
- [ ] Native application configuration references are supported for the MVP's agreed integrations.
- [ ] The launcher displays clearly labeled player links and allows copying a complete invitation.
- [ ] GM-only links are not included in the invitation by default.
- [ ] Missing dependencies, unavailable resources and failed launches are surfaced clearly.
- [ ] The documentation shows how to add a game, modify a link, and adapt the setup to a second machine.
- [ ] The team records which verification steps remain manual and does not present them as automated successes.

## 16. Developer handoff notes

This PRD intentionally leaves room for engineering decisions. In particular, it does **not** prescribe the launcher's programming language, internal architecture, CLI framework, exact Nix module design, process supervision strategy, or how native configuration files are deployed.

Before coding, the team should validate the **High-priority open questions** and inspect a representative existing game setup. Where decisions are not yet possible, prefer the smallest behavior that satisfies the documented requirements and can evolve without forcing users to rewrite their game presets.

**Central product test:** Can the GM start a known campaign, on a supported computer, with very little preparation and immediately obtain the correct links for players—without maintaining a second configuration system for all the underlying applications?
