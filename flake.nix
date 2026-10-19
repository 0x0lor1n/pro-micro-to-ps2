{
  description = "Pro Micro as a PS/2 keyboard, driven from a Linux terminal";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    mcu-bench = {
      url = "github:0x0lor1n/mcu-bench";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    ps2dev = {
      url = "github:Harvie/ps2dev";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      mcu-bench,
      ps2dev,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAll = f: nixpkgs.lib.genAttrs systems (s: f nixpkgs.legacyPackages.${s});
      bench = pkgs: mcu-bench.lib pkgs;
      python = pkgs: (bench pkgs).python (_: [ ]);
    in
    {
      packages = forAll (
        pkgs:
        let
          b = bench pkgs;
          pm = b.boards.promicro;
        in
        rec {
          ps2term = pkgs.runCommand "ps2term" { buildInputs = [ pkgs.python3 ]; } ''
            install -Dm755 ${./src/ps2term/ps2term.py} $out/bin/ps2term
            patchShebangs $out/bin
          '';

          firmware = pm.mkFirmware {
            name = "pro-micro-to-ps2-firmware";
            ino = ./src/firmware/firmware.ino;
            libraries = { inherit ps2dev; };
          };

          flash = pm.mkFlash "flash" firmware;

          # docs/bench.fzz is tracked; `nix build .#bench-fzz` regenerates it from gen.py.
          bench-fzz = b.mkBenchFzz {
            name = "pro-micro-to-ps2-bench-fzz";
            gen = ./src/fritzing/gen.py;
            python = python pkgs;
          };

          # docs/{schematic,wiring}.{svg,png} are tracked; `render-docs` copies this output over them.
          # SVG for GitHub, PNG for chats (Telegram drops schemdraw's <use> text).
          docs =
            pkgs.runCommand "pro-micro-to-ps2-docs" { nativeBuildInputs = [ (python pkgs) ] ++ b.renderInputs; }
              ''
                mkdir -p $out
                ${b.renderSchematic "${./src/schematic}/schematic.py" "$out/schematic"}
                ${b.renderD2 "${./docs}/wiring.d2" "$out/wiring"}
              '';

          render-docs = b.mkRenderDocs { };
          fizzel = b.mkFizzel "fizzel" "docs/bench.fzz";

          default = ps2term;
        }
      );

      apps = forAll (
        pkgs:
        let
          pkg = self.packages.${pkgs.stdenv.hostPlatform.system};
        in
        {
          default = {
            type = "app";
            program = "${pkg.ps2term}/bin/ps2term";
          };
          flash = {
            type = "app";
            program = "${pkg.flash}/bin/flash";
          };
          fizzel = {
            type = "app";
            program = "${pkg.fizzel}/bin/fizzel";
          };
        }
      );

      devShells = forAll (pkgs: {
        default = (bench pkgs).mkDevShell {
          name = "pro-micro-to-ps2";
          packages =
            with self.packages.${pkgs.stdenv.hostPlatform.system};
            [
              ps2term
              flash
              fizzel
              render-docs
              pkgs.d2
              (python pkgs)
            ]
            ++ (bench pkgs).boards.promicro.devPackages;
          commands = [
            [
              "flash [port]"
              "build and flash the firmware (default /dev/ttyACM0)"
            ]
            [
              "ps2term [port]"
              "type into the PS/2 host (Ctrl-B Del spam, Ctrl-] quits)"
            ]
            [
              "picocom -b 115200 /dev/ttyACM0"
              "raw console: host commands as H xx / A xx"
            ]
            [
              "fizzel"
              "docs/bench.fzz in Fritzing"
            ]
            [
              "nix flake check"
              "firmware sim, ps2term test, Fritzing lint, docs/bench freshness"
            ]
            [
              "nix build .#bench-fzz"
              "regenerate bench.fzz from src/fritzing/gen.py"
            ]
            [
              "render-docs"
              "regenerate docs/{schematic,wiring}.{svg,png} from src/schematic and wiring.d2"
            ]
            [
              "lefthook run pre-commit"
              "what the commit hook runs (nixfmt, deadnix, statix, ruff, clang-format, cppcheck)"
            ]
            [
              "lefthook run pre-push"
              "what the push hook runs (nix flake check)"
            ]
          ];
        };
      });

      checks = forAll (
        pkgs:
        let
          b = bench pkgs;
          pkg = self.packages.${pkgs.stdenv.hostPlatform.system};
        in
        {
          # The unchanged .ino against a fake Arduino core and a fake PS2dev.
          sim = b.mkSim {
            name = "sim";
            firmware = ./src/firmware;
            test = ./test;
          };
          ps2term = pkgs.runCommand "ps2term-test" { nativeBuildInputs = [ pkgs.python3 ]; } ''
            PYTHONPATH=${./src/ps2term} python3 ${./test/test_ps2term.py} | tee $out
          '';
          # PNG is not compared, resvg output is not byte-stable across versions.
          docs-fresh = b.mkFreshCheck "docs-fresh" pkg.docs ./docs [
            "schematic.svg"
            "wiring.svg"
          ];
          bench-fresh = b.mkFreshCheck "bench-fresh" pkg.bench-fzz ./docs [ "bench.fzz" ];
          bench-lint = b.mkBenchLint {
            fzz = pkg.bench-fzz;
            sketches = [ "bench" ];
            # Whole dir: lint_cases imports the pin map from gen.py.
            cases = "${./src/fritzing}/lint_cases.py";
            python = python pkgs;
          };
        }
      );
    };
}
