{
  description = "Pro Micro as a PS/2 keyboard, driven from a Linux terminal";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    ps2dev = {
      url = "github:Harvie/ps2dev";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      ps2dev,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAll = f: nixpkgs.lib.genAttrs systems (s: f nixpkgs.legacyPackages.${s});
    in
    {
      packages = forAll (
        pkgs:
        let
          core = "${pkgs.arduino-core-unwrapped}/share/arduino";
        in
        rec {
          ps2term = pkgs.runCommand "ps2term" { buildInputs = [ pkgs.python3 ]; } ''
            install -Dm755 ${./src/ps2term/ps2term.py} $out/bin/ps2term
            patchShebangs $out/bin
          '';

          # Pro Micro 5 V/16 MHz runs the Leonardo build unchanged (same MCU, Caterina loader).
          firmware = pkgs.runCommand "pro-micro-to-ps2-firmware" { } ''
            mkdir -p libs build sketch/firmware $out
            ln -s ${ps2dev} libs/ps2dev
            cp ${./src/firmware/firmware.ino} sketch/firmware/firmware.ino
            ${core}/arduino-builder \
              -hardware ${core}/hardware \
              -tools ${core}/tools-builder \
              -tools ${core}/hardware/tools/avr \
              -built-in-libraries ${core}/libraries \
              -libraries libs \
              -fqbn arduino:avr:leonardo \
              -build-path "$PWD/build" \
              -warnings default \
              sketch/firmware/firmware.ino
            cp build/firmware.ino.hex $out/firmware.hex
          '';

          flash = pkgs.writeShellApplication {
            name = "flash";
            runtimeInputs = [
              pkgs.avrdude
              pkgs.coreutils
            ];
            # 1200 bps touch resets Caterina into its loader (8 s window); the loader
            # re-enumerates under the same ttyACM name, so match by USB id instead.
            text = ''
              port=''${1:-/dev/ttyACM0}
              # Leonardo loader, Pro Micro 5V, Pro Micro 3V3
              is_loader() {
                d=/sys/class/tty/''${1##*/}/device/..
                [ -r "$d/idVendor" ] || return 1
                case "$(cat "$d/idVendor"):$(cat "$d/idProduct")" in
                  2341:0036|2a03:0036|1b4f:9205|1b4f:9203) return 0 ;;
                esac
                return 1
              }
              find_loader() {
                for _ in $(seq "$1"); do
                  for p in /dev/ttyACM*; do
                    [ -e "$p" ] && is_loader "$p" && { echo "$p"; return 0; }
                  done
                  sleep 0.1
                done
                return 1
              }
              loader=$(find_loader 1 || true)
              if [ -z "$loader" ] && [ -e "$port" ]; then
                echo "1200 bps touch on $port"
                stty -F "$port" 1200 || true
                loader=$(find_loader 50 || true)
              fi
              if [ -z "$loader" ]; then
                echo "no bootloader: short RST to GND twice now"
                loader=$(find_loader 150 || true)
              fi
              [ -n "$loader" ] || { echo "no bootloader appeared"; exit 1; }
              echo "bootloader on $loader"
              sleep 0.3
              avrdude -p atmega32u4 -c avr109 -P "$loader" -b 57600 -D \
                -U flash:w:${firmware}/firmware.hex:i
            '';
          };

          # docs/wiring.{svg,png} are tracked; `render-docs` in the devshell copies
          # this output over them. d2 embeds its font as @font-face, which resvg
          # ignores, so the PNG pass substitutes a real font-family first.
          docs =
            pkgs.runCommand "pro-micro-to-ps2-docs"
              {
                nativeBuildInputs = [
                  pkgs.d2
                  pkgs.resvg
                ];
              }
              ''
                mkdir -p $out
                d2 ${./docs}/wiring.d2 $out/wiring.svg
                sed -E 's/font-family: "?d2-[0-9]+-font-(bold|italic|regular)"?/font-family: "Source Sans 3"/' \
                  $out/wiring.svg > wiring.svg
                resvg --skip-system-fonts --use-fonts-dir ${pkgs.source-sans}/share/fonts \
                  --font-family "Source Sans 3" wiring.svg $out/wiring.png
              '';

          render-docs = pkgs.writeShellApplication {
            name = "render-docs";
            text = ''
              cp -r --no-preserve=mode "$(nix build --no-link --print-out-paths .#docs)"/. docs/
              git -C docs status --short .
            '';
          };

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
        }
      );

      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = with self.packages.${pkgs.stdenv.hostPlatform.system}; [
            ps2term
            flash
            render-docs
            pkgs.avrdude
            pkgs.picocom
            pkgs.d2
            pkgs.python3
            # git hooks; lefthook.yml takes the tools from PATH
            pkgs.lefthook
            pkgs.gitleaks
            pkgs.nixfmt
            pkgs.deadnix
            pkgs.statix
            pkgs.ruff
            pkgs.clang-tools
            pkgs.cppcheck
          ];
          shellHook = ''
            lefthook install >/dev/null || echo "lefthook install failed; git hooks not installed" >&2
            cat <<'HELP'
            pro-micro-to-ps2 devshell
              flash [port]              build and flash the firmware (default /dev/ttyACM0)
              ps2term [port]            type into the PS/2 host (Ctrl-B Del spam, Ctrl-] quits)
              picocom -b 115200 /dev/ttyACM0   raw console: host commands as H xx / A xx
              nix flake check           firmware sim, ps2term test, docs-fresh
              render-docs               regenerate docs/wiring.{svg,png} from docs/wiring.d2
              lefthook run pre-commit   what the commit hook runs (nixfmt, deadnix, statix, ruff, clang-format, cppcheck)
              lefthook run pre-push     what the push hook runs (nix flake check)
            HELP
          '';
        };
      });

      checks = forAll (pkgs: {
        # The unchanged .ino against a fake Arduino core and a fake PS2dev.
        sim = pkgs.runCommandCC "sim" { } ''
          mkdir -p test src/firmware
          cp ${./src/firmware/firmware.ino} src/firmware/firmware.ino
          cp ${./test/sim.cpp} test/sim.cpp
          cp ${./test/ps2dev.h} test/ps2dev.h
          $CXX -std=c++17 -Wall -Werror -Wno-unused-function -I test test/sim.cpp -o sim
          ./sim | tee $out
        '';
        ps2term = pkgs.runCommand "ps2term-test" { nativeBuildInputs = [ pkgs.python3 ]; } ''
          PYTHONPATH=${./src/ps2term} python3 ${./test/test_ps2term.py} | tee $out
        '';
        # The tracked SVG must be what wiring.d2 renders to; the PNG is not
        # compared, resvg output is not byte-stable across versions.
        docs-fresh = pkgs.runCommand "docs-fresh" { } ''
          cmp -s ${self.packages.${pkgs.stdenv.hostPlatform.system}.docs}/wiring.svg ${./docs}/wiring.svg \
            || { echo "docs/wiring.svg is stale, run render-docs" >&2; exit 1; }
          touch $out
        '';
      });
    };
}
