{
  lib,
  python3Packages,
  wl-clipboard,
  xclip,
}:

python3Packages.buildPythonApplication {
  pname = "rpg-launcher";
  version = (lib.importTOML ../pyproject.toml).project.version;
  pyproject = true;

  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [
      ../pyproject.toml
      ../src
      ../tests
      ../examples
    ];
  };

  build-system = [ python3Packages.setuptools ];

  # The tests need only the standard library.
  checkPhase = ''
    runHook preCheck
    python -m unittest discover -s tests
    runHook postCheck
  '';

  # Clipboard tools for copying invitations. Added after the system PATH, so a
  # tool the machine already has is used first.
  makeWrapperArgs = [
    "--suffix"
    "PATH"
    ":"
    (lib.makeBinPath [
      wl-clipboard
      xclip
    ])
  ];

  meta = {
    description = "Start a tabletop RPG session's apps and pages, then hand out player links";
    mainProgram = "rpg-launcher";
    platforms = lib.platforms.linux;
  };
}
