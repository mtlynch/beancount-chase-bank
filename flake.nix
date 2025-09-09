{
  description = "Create Nix development environment";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";

    # Python 3.13.3 release
    python-nixpkgs.url = "github:NixOS/nixpkgs/12a55407652e04dcf2309436eb06fef0d3713ef3";

    pyproject-nix.url = "github:nix-community/pyproject.nix";
  };

  outputs = {
    self,
    python-nixpkgs,
    flake-utils,
    pyproject-nix,
  } @ inputs:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = python-nixpkgs.legacyPackages.${system};
      python = pkgs.python313;

      # Load production requirements
      project = pyproject-nix.lib.project.loadRequirementsTxt {
        projectRoot = ./.;
      };

      # Parse dev requirements manually (excluding --requirement line)
      devRequirementsContent = builtins.readFile ./dev_requirements.txt;
      devRequirementsLines = pkgs.lib.splitString "\n" devRequirementsContent;
      devRequirements =
        builtins.filter (
          line:
            line
            != ""
            && !pkgs.lib.hasPrefix "#" line
            && !pkgs.lib.hasPrefix "--requirement" line
        )
        devRequirementsLines;

      # Parse dev requirements into package names
      devPackages =
        map (
          req: let
            # Split on == to get package name
            parts = pkgs.lib.splitString "==" req;
            packageName = builtins.head parts;
            # Handle special cases like isort[requirements_deprecated_finder]
            cleanName = pkgs.lib.replaceStrings ["[" "]"] ["" ""] (
              builtins.head (pkgs.lib.splitString "[" packageName)
            );
          in
            cleanName
        )
        devRequirements;

      # Create development environment with both prod and dev dependencies
      pythonEnv = python.withPackages (
        ps:
          (project.renderers.withPackages {inherit python;} ps)
          ++ (builtins.filter (pkg: pkg != null) (map (
              name:
                if builtins.hasAttr name ps
                then ps.${name}
                else null
            )
            devPackages))
      );
    in {
      formatter = pkgs.alejandra;

      devShells.default = pkgs.mkShell {
        packages = [
          pythonEnv
        ];

        shellHook = ''
          python --version
        '';
      };
    });
}
