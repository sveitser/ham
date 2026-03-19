{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  inputs.git-hooks.url = "github:cachix/git-hooks.nix";
  inputs.git-hooks.inputs.nixpkgs.follows = "nixpkgs";

  outputs = { nixpkgs, git-hooks, ... }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      eachSystem = f: nixpkgs.lib.genAttrs systems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in f pkgs system
      );
      hookConfig = {
        hooks = {
          ruff-format = {
            enable = true;
            description = "Format Python";
            entry = "ruff format";
            types_or = [ "python" ];
            pass_filenames = true;
          };
          ruff-check = {
            enable = true;
            description = "Lint Python";
            entry = "ruff check --fix";
            types_or = [ "python" ];
            pass_filenames = true;
          };
          pytest-cov = {
            enable = true;
            description = "Tests with 98% coverage";
            entry = "pytest --cov=ham --cov-fail-under=98 -q";
            types_or = [ "python" ];
            pass_filenames = false;
          };
        };
      };
    in {
      checks = eachSystem (pkgs: system: {
        pre-commit-check = git-hooks.lib.${system}.run {
          src = ./.;
          imports = [
            ({ lib, ... }: { config.package = lib.mkForce pkgs.prek; })
            hookConfig
          ];
        };
      });

      devShells = eachSystem (pkgs: system:
        let
          pre-commit-check = git-hooks.lib.${system}.run {
            src = ./.;
            imports = [
              ({ lib, ... }: { config.package = lib.mkForce pkgs.prek; })
              hookConfig
            ];
          };
          prek-as-pre-commit = pkgs.runCommand "prek-as-pre-commit" { } ''
            mkdir -p $out/bin
            ln -s ${pkgs.prek}/bin/prek $out/bin/pre-commit
          '';
        in {
          default = pkgs.mkShell {
            packages = [
              (pkgs.python3.withPackages (ps: [
                ps.pytest
                ps.pytest-cov
              ]))
              pkgs.ruff
              pkgs.just
              pkgs.prek
              prek-as-pre-commit
            ];
            shellHook = pre-commit-check.shellHook;
          };
        }
      );
    };
}
