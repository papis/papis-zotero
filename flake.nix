{
  description = "Zotero compatibility layer for Papis";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    pyproject-nix.url = "github:nix-community/pyproject.nix";
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";

    papis.url = "github:papis/papis";
    papis.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    pyproject-nix,
    papis,
  }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3.override {
          packageOverrides = self: super: {
            papis = papis.packages.${system}.default;
          };
        };
        project = pyproject-nix.lib.project.loadPyproject {projectRoot = ./.;};
      in {
        packages = {
          papis-zotero = let
            attrs = project.renderers.buildPythonPackage {
              inherit python;
            };
          in
            python.pkgs.buildPythonPackage (attrs
              // {
                version =
                  if (self ? rev)
                  then self.shortRev
                  else self.dirtyShortRev;
                propagatedBuildInputs = [
                  papis.packages.${system}.default
                ];
              });
          default = self.packages.${system}.papis-zotero;
        };

        devShells = {
          default = let
            arg = project.renderers.withPackages {
              inherit python;
              extras = ["develop"];
            };
            pythonEnv = python.withPackages arg;
          in
            pkgs.mkShell {
              packages = [
                pythonEnv
                self.packages.${system}.papis-zotero
              ];
              shellHook = ''
                export PYTHONPATH="$(pwd):$PYTHONPATH"
              '';
            };
        };
      }
    );
}
