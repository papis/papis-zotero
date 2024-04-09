{
  description = "Zotero compatibility layer for Papis";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    papis = {
      url = "github:papis/papis";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    pyproject-nix,
    papis,
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pypkgs = pkgs.python3Packages;
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3.override {
          packageOverrides = self: super: {
            papis = papis.packages.${system}.default;
            flake8-quotes = flake8-quotes;
            flake8-pyproject = flake8-pyproject;
            python-coveralls = python-coveralls;
          };
        };
        project = pyproject-nix.lib.project.loadPyproject {projectRoot = ./.;};

        flake8-quotes = python.pkgs.buildPythonPackage rec {
          pname = "flake8-quotes";
          version = "3.4.0";

          src = python.pkgs.fetchPypi {
            inherit pname version;
            sha256 = "sha256-qthJL7cQotPqvmjF+GoUKN5lDISEEn4UxD0FBLowJ2w=";
          };

          doCheck = false;
          checkInputs = [];

          meta = with pkgs.lib; {
            homepage = "http://github.com/zheller/flake8-quotes";
            description = "Flake8 lint for quotes.";
            license = licenses.mit;
          };
        };

        flake8-pyproject = python.pkgs.buildPythonPackage {
          pname = "flake8-pyproject";
          version = "1.2.3";
          pyproject = true;

          src = pkgs.fetchFromGitHub {
            owner = "john-hen";
            repo = "Flake8-pyproject";
            rev = "30b8444781d16edd54c11df08210a7c8fb79258d";
            hash = "sha256-bPRIj7tYmm6I9eo1ZjiibmpVmGcHctZSuTvnKX+raPg=";
          };

          doCheck = false;
          checkInputs = [];
          propagatedBuildInputs = [pypkgs.flit-core pypkgs.flake8];

          meta = with pkgs.lib; {
            homepage = "https://github.com/john-hen/Flake8-pyproject";
            description = "Flake8 plug-in loading the configuration from pyproject.toml";
            license = licenses.mit;
          };
        };

        python-coveralls = python.pkgs.buildPythonPackage rec {
          pname = "python-coveralls";
          version = "2.9.3";

          src = python.pkgs.fetchPypi {
            inherit pname version;
            sha256 = "sha256-v694EefcVijoO2sWKWKk4khdv/GEsw5J84A3TtG87lU=";
          };

          doCheck = false;
          checkInputs = [];

          meta = with pkgs.lib; {
            homepage = "http://github.com/z4r/python-coveralls";
            description = "Python interface to coveralls.io API ";
            license = licenses.asl20;
          };
        };
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
