{
  description = "RPG session launcher: start a game's apps and pages, then hand out player links";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forEachSystem (pkgs: rec {
        rpg-launcher = pkgs.callPackage ./nix/package.nix { };
        default = rpg-launcher;
      });

      # The package build runs the tests, so `nix flake check` does too.
      checks = forEachSystem (pkgs: {
        rpg-launcher = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      });

      devShells = forEachSystem (pkgs: {
        default = pkgs.mkShell {
          packages = [ pkgs.python3 ];
          shellHook = ''
            export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
          '';
        };
      });

      # NixOS: installs the launcher together with the applications it starts.
      nixosModules.default = import ./nix/module.nix;
    };
}
