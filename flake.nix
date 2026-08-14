{
  # Keep this line accurate and one line long: `nix flake metadata` prints it,
  # and it is the first thing a cold agent learns about the repo.
  description = "streamer_shield_bot -- StreamerShield's Twitch moderation chat bot (Python, quart + twitchAPI + asyncpg). Run `nix flake show` for the command map.";

  # nixpkgs is the only input, on purpose.
  #
  # flake-utils would buy exactly one thing here -- eachDefaultSystem -- which is
  # the three-line genAttrs below. In exchange it costs a second lock node, a
  # second upstream that can break, and a hardcoded system list this repo cannot
  # edit. That list is currently broken: it still contains x86_64-darwin, which
  # now throws (see `systems` below).
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    # `...` rather than a closed { self, nixpkgs }: adding a second input later
    # would otherwise fail with "called with unexpected argument 'self'".
    { nixpkgs, ... }:
    let
      lib = nixpkgs.lib;

      # x86_64-darwin is deliberately absent: nixpkgs 26.11 replaced that whole
      # attribute set with a `throw`. genAttrs is lazy, so plain `nix develop` on
      # Linux would not notice -- it detonates on `nix flake check --all-systems`.
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];

      # Stand-in for flake-utils.lib.eachDefaultSystem. Passes `pkgs` rather than
      # a system string, because that is what every call site below wants.
      forAllSystems = f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # ======================================================================
      # PER-REPO BLOCK 1 -- the toolchain
      # ======================================================================
      # python312, not python3 or python313: the Dockerfile builds on
      # python:3.12-slim and the README asks for 3.12, and requirements.txt pins
      # tensorflow, whose wheel availability is the thing that decides this
      # repo's Python version. Pinning by major keeps .venv valid across a
      # nixpkgs bump -- a rolling alias would invalidate it on some random
      # afternoon.
      #
      # postgresql is here for `psql` only: init_database.sh and
      # init_database.ps1 pipe database_setup.sql into it, so a cold agent that
      # cannot run psql cannot bring this repo up. It is not a server for you to
      # start -- point DB_HOST/DB_PORT at a real Postgres.
      #
      # shellcheck is for init_database.sh, which CI treats as a first-class
      # source file (build_and_push.yml triggers on '**/*.sh').
      toolchain = pkgs: [
        # ---- this repo's ecosystem ----
        pkgs.python312
        pkgs.uv
        pkgs.ruff
        pkgs.postgresql_17
        pkgs.shellcheck

        # ---- present in every repo in the fleet ----
        pkgs.git
        pkgs.jq
        pkgs.gnumake
      ];

      # ======================================================================
      # PER-REPO BLOCK 2 -- libraries that get dlopened, not linked
      # ======================================================================
      # numpy and tensorflow ship manylinux wheels whose .so files are dlopened
      # at runtime, so neither patchelf nor the nix linker ever sees them and
      # NixOS has no /usr/lib to find them in. stdenv.cc.cc.lib supplies
      # libstdc++, which is the one that breaks `import numpy`. Keep this list
      # minimal -- LD_LIBRARY_PATH is a blunt instrument.
      nativeLibs = pkgs: [
        pkgs.stdenv.cc.cc.lib
        pkgs.zlib
      ];

      # ======================================================================
      # PER-REPO BLOCK 3 -- constant environment variables
      # ======================================================================
      # Only constants belong here. Anything that must READ an existing value
      # (LD_LIBRARY_PATH), UNSET something (SOURCE_DATE_EPOCH) or touch the work
      # tree goes in the shellHook further down.
      #
      # Applied to BOTH surfaces -- the dev shell and every `nix run` wrapper --
      # so a command cannot behave differently depending on how it was reached.
      #
      # Deliberately absent: TWITCH_APP_ID, TWITCH_APP_SECRET, DB_* and the
      # SHIELD_URL/EVENTSUB_URL family. twitch_config.py raises on a missing app
      # id by design; baking placeholder credentials in here would turn that
      # loud failure into a confusing Twitch 401 much later.
      envVars = pkgs: {
        # Keep uv on the nix interpreter. Left alone it downloads its own
        # portable CPython, which then resolves a different set of wheels than
        # this shell pins: two Pythons, one venv, no way to tell which is live.
        UV_PYTHON = "${pkgs.python312}/bin/python";
        UV_PYTHON_DOWNLOADS = "never";
        # /nix/store and the work tree are usually different filesystems, so
        # uv's default hardlink strategy warns on every single install.
        UV_LINK_MODE = "copy";
        PIP_DISABLE_PIP_VERSION_CHECK = "1";
        # Matches ENV PYTHONUNBUFFERED=1 in the Dockerfile. Without it the bot's
        # logs sit in a pipe buffer, which reads as a hung process to an agent
        # capturing stdout.
        PYTHONUNBUFFERED = "1";
      };

      # ======================================================================
      # PER-REPO BLOCK 4 -- the command map
      # ======================================================================
      # THE single source of truth. It generates `apps` (so `nix run .#lint`
      # works), the `dev-*` wrappers on PATH inside the shell, and `dev-help`.
      # Nothing is written twice, so `nix flake show` can never disagree with
      # what `dev-lint` actually runs.
      #
      # `build` and `test` are OMITTED on purpose, and their absence is
      # information: this repo produces no local artifact (CI builds the
      # container from the Dockerfile) and ships no test suite -- there is no
      # tests/ directory, no pytest/unittest file and no test job in
      # .github/workflows/build_and_push.yml. A stub that echoed "not
      # applicable" would turn `nix flake show` into a liar. Add `test` here in
      # the same breath as the first real test.
      commands = pkgs: {
        setup = {
          # requirements.txt is unpinned and pulls tensorflow (~600 MB wheel),
          # so this is slow once and cached after. Note that tensorflow,
          # discord and ipaddress are listed but imported by nothing in this
          # repo; they are installed anyway rather than second-guessing the
          # manifest in a flake.
          description = "(network) create .venv from requirements.txt (large: pulls tensorflow)";
          text = ''
            uv venv "$REPO_ROOT/.venv"
            uv pip install --python "$REPO_ROOT/.venv/bin/python" -r "$REPO_ROOT/requirements.txt"
          '';
        };
        lint = {
          # There is no ruff.toml or pyproject.toml in the repo, so this is
          # ruff's own default rule set, and it reports dozens of pre-existing
          # findings (unused imports, `except:`, %-formatting, unsorted imports)
          # on an untouched checkout. A red `dev-lint` here is the truth about
          # the code, NOT a broken flake -- do not "fix" it by narrowing the
          # rules in this file. If the repo wants a narrower set, that decision
          # belongs in a committed ruff config, where the editor and CI can see
          # it too.
          description = "ruff check (default rules; the repo has pre-existing findings)";
          text = ''ruff check "$@"'';
        };
        fmt = {
          description = "ruff format (rewrites files)";
          text = ''ruff format "$@"'';
        };
        run = {
          # The venv interpreter and the script both by absolute path, not a
          # bare `python`: the wrappers prepend the nix toolchain to PATH, so a
          # bare name resolves to the store copy and misses everything `setup`
          # installed into .venv.
          #
          # Needs TWITCH_APP_ID and TWITCH_APP_SECRET exported or
          # twitch_config.py raises immediately, plus a reachable Postgres
          # (DB_HOST/DB_PORT/...). It binds 0.0.0.0:38080 for the Quart auth and
          # EventSub endpoints.
          description = "start the bot (needs `setup`, TWITCH_APP_ID/SECRET and a Postgres)";
          text = ''"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/streamer_shield_chatbot.py" "$@"'';
        };
      };

      # ======================================================================
      # GENERIC MACHINERY -- byte-identical across the fleet, do not edit
      # ======================================================================

      # Prepend, never assign: a host LD_LIBRARY_PATH may be carrying something
      # the user needs, and clobbering it breaks binaries they launch from here.
      # Linux only -- on darwin the loader variable is DYLD_*, and exporting a
      # Linux-shaped value there is at best useless.
      ldPreamble =
        pkgs:
        lib.optionalString (pkgs.stdenv.hostPlatform.isLinux && nativeLibs pkgs != [ ]) ''
          export LD_LIBRARY_PATH="${lib.makeLibraryPath (nativeLibs pkgs)}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        '';

      # Every command gets $REPO_ROOT. `nix run` and `nix develop` both start in
      # whatever directory they were invoked from, so a bare `.venv` silently
      # forks a second environment as soon as an agent works from a subdirectory.
      # Note we do NOT cd there: commands act on the caller's cwd on purpose.
      rootPreamble = ''
        REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
        export REPO_ROOT
      '';

      # One derivation per command, reused by both `apps` and the dev shell, so
      # the two can never diverge. `dev-` prefixed because a bare `test` binary
      # earlier on PATH would shadow the POSIX shell builtin and quietly break
      # every script in the repo that uses it.
      wrappers =
        pkgs:
        lib.mapAttrs (
          name: cmd:
          pkgs.writeShellApplication {
            name = "dev-${name}";
            runtimeInputs = toolchain pkgs;
            runtimeEnv = envVars pkgs;
            meta.description = cmd.description;
            text = ''
              ${rootPreamble}
              ${ldPreamble pkgs}
              ${cmd.text}
            '';
          }
        ) (commands pkgs);

      helpFor =
        pkgs:
        let
          cmds = commands pkgs;
          names = lib.attrNames cmds;
          width = lib.foldl' (a: n: lib.max a (builtins.stringLength n)) 0 names;
          pad = n: n + lib.concatStrings (lib.genList (_: " ") (width - builtins.stringLength n));
          line = n: c: "  dev-${pad n}  ${c.description}";
        in
        pkgs.writeShellApplication {
          name = "dev-help";
          meta.description = "print this repo's command map (works offline)";
          text = ''
            cat <<'EOF'
            ${lib.concatStringsSep "\n" (lib.mapAttrsToList line cmds)}
            EOF
          '';
        };
    in
    {
      # `nix flake show` -- the discovery entrypoint, and deliberately the whole
      # machine-facing contract: every app carries a meta.description, which
      # `nix flake show` prints inline and `nix flake show --json` exposes at
      # .apps.<system>.<name>.description. Pure evaluation, so an agent gets the
      # entire command map in one cheap call without reading a README.
      #
      # Do NOT invent a top-level output for this (`agentManifest` ...). Nix
      # answers with `warning: unknown flake output '<name>'` on every single
      # `nix flake check`, forever.
      apps = forAllSystems (
        pkgs:
        lib.mapAttrs (name: cmd: {
          type = "app";
          program = "${(wrappers pkgs).${name}}/bin/dev-${name}";
          meta.description = cmd.description;
        }) (commands pkgs)
      );

      # `nix develop` -- the toolchain, plus a dev-<verb> for every app.
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = toolchain pkgs ++ lib.attrValues (wrappers pkgs) ++ [ (helpFor pkgs) ];

          env = envVars pkgs;

          # Some C extensions compile at -O0, where glibc's _FORTIFY_SOURCE
          # becomes a hard error instead of a warning.
          hardeningDisable = [ "fortify" ];

          shellHook = ''
            # mkShell inherits SOURCE_DATE_EPOCH=315532800 (1980-01-01) from
            # stdenv, and any wheel or zip built in here then dies with "ZIP does
            # not support timestamps before 1980".
            unset SOURCE_DATE_EPOCH

            ${rootPreamble}
            ${ldPreamble pkgs}

            # Nothing networked, nothing stateful and nothing interactive above
            # this line, and nothing below it either. No venv creation, no `pip
            # install`. Bootstrapping in the hook makes a cold
            # `nix develop -c python ...` start downloading before it runs
            # anything, on EVERY invocation -- the exact failure an unattended
            # agent cannot diagnose. That is what `dev-setup` is for.

            # The banner is interactive-only, and this guard is load-bearing:
            # shellHook output lands on the STDOUT of `nix develop -c <cmd>`, so
            # an unguarded echo corrupts anything parsing it
            # (`nix develop -c cat x.json | jq` fails to parse). $- is the only
            # reliable discriminator here -- it lacks `i` for `nix develop -c`
            # and has it at an interactive prompt. Do not test $PS1 (unset in
            # both) or $IN_NIX_SHELL (set in both). >&2 is the second layer, for
            # the case where a caller runs us on a pty.
            case $- in
              *i*) echo "streamer_shield_bot dev shell -- 'dev-help' for the command map" >&2 ;;
            esac
          '';
        };
      });

      # `nix flake check` -- honest by construction. It realises the toolchain
      # closure (so a typo'd or currently-broken attr fails here) and builds
      # every wrapper, which runs shellcheck over every command text. Add real
      # test derivations beside it once the repo grows tests. NEVER add a check
      # that always passes: an agent reads "all checks passed!" as a signal.
      checks = forAllSystems (pkgs: {
        toolchain =
          pkgs.runCommand "toolchain-check"
            {
              nativeBuildInputs = toolchain pkgs ++ lib.attrValues (wrappers pkgs);
            }
            ''
              for verb in ${lib.escapeShellArgs (lib.attrNames (commands pkgs))}; do
                command -v "dev-$verb" > /dev/null || {
                  echo "dev-$verb is not on PATH" >&2
                  exit 1
                }
              done
              touch "$out"
            '';
      });

      # `nix fmt` -- formats the *Nix* in this repo; project code is `dev-fmt`.
      # nixfmt-tree (the treefmt wrapper) rather than bare nixfmt, because bare
      # nixfmt tries to parse every path handed to it and fails on non-Nix files.
      formatter = forAllSystems (pkgs: pkgs.nixfmt-tree);
    };
}
