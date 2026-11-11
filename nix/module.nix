{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.rpg-launcher;
in
{
  options.programs.rpg-launcher = {
    enable = lib.mkEnableOption "the RPG session launcher and the applications it starts";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ./package.nix { };
      defaultText = lib.literalExpression "pkgs.callPackage ./package.nix { }";
      description = "The rpg-launcher package to install.";
    };

    apps = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [
        pkgs.obs-studio
        pkgs.chromium
      ];
      defaultText = lib.literalExpression "[ pkgs.obs-studio pkgs.chromium ]";
      example = lib.literalExpression "[ pkgs.obs-studio pkgs.chromium pkgs.discord ]";
      description = ''
        Applications that game presets start on this machine. They come from
        the system's own nixpkgs, so the system decides their versions.
        Discord is not in the default list because it is unfree.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ] ++ cfg.apps;
  };
}
