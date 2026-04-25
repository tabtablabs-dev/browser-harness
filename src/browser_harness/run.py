import os, sys

from . import helpers as _helpers
from . import kameleo

# Windows default stdout encoding is cp1252, which can't encode the 🟢 marker
# helpers prepend to tab titles (or anything else outside Latin-1). Force UTF-8
# so `print(page_info())` doesn't UnicodeEncodeError on Windows. Issue #124(4).
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

from .admin import (
    _version,
    daemon_alive,
    ensure_daemon,
    list_cloud_profiles,
    list_local_profiles,
    print_update_banner,
    restart_daemon,
    run_doctor,
    run_setup,
    run_update,
    start_remote_daemon,
    stop_remote_daemon,
    sync_local_profile,
)
from .helpers import *

HELP = """Browser Harness

Read SKILL.md for the default workflow and examples.

Typical usage:
  browser-harness -c '
  ensure_real_tab()
  print(page_info())
  '

Helpers are pre-imported. The daemon auto-starts and connects to the running browser.

Commands:
  browser-harness --version        print the installed version
  browser-harness --doctor         diagnose install, daemon, and browser state
  browser-harness --setup          interactively attach to your running browser
  browser-harness --update [-y]    pull the latest version (agents: pass -y)
  browser-harness --reload         stop the daemon so next call picks up code changes
  browser-harness --kameleo-profile NAME [--bu-name NAME] [-c CODE]
"""


def main():
    args = sys.argv[1:]
    if args and args[0] in {"-h", "--help"}:
        print(HELP)
        return
    if args and args[0] == "--version":
        print(_version() or "unknown")
        return
    if args and args[0] == "--doctor":
        sys.exit(run_doctor())
    if args and args[0] == "--setup":
        sys.exit(run_setup())
    if args and args[0] == "--update":
        yes = any(a in {"-y", "--yes"} for a in args[1:])
        sys.exit(run_update(yes=yes))
    if args and args[0] == "--reload":
        restart_daemon()
        print("daemon stopped — will restart fresh on next call")
        return
    if args and args[0] == "--debug-clicks":
        os.environ["BH_DEBUG_CLICKS"] = "1"
        args = args[1:]
    kameleo_profile = None
    kameleo_api = None
    bu_name = None
    while args:
        if args[0] == "--kameleo-profile" and len(args) >= 2:
            kameleo_profile = args[1]
            args = args[2:]
            continue
        if args[0] == "--kameleo-api" and len(args) >= 2:
            kameleo_api = args[1]
            args = args[2:]
            continue
        if args[0] == "--bu-name" and len(args) >= 2:
            bu_name = args[1]
            args = args[2:]
            continue
        break
    if not args or args[0] != "-c":
        sys.exit("Usage: browser-harness -c \"print(page_info())\"")
    if len(args) < 2:
        sys.exit("Usage: browser-harness -c \"print(page_info())\"")
    print_update_banner()
    if kameleo_profile:
        env = kameleo.attach_env(kameleo_profile, api=kameleo_api, name=bu_name)
        os.environ.update(env)
        _helpers.NAME = env["BU_NAME"]
        _helpers.SOCK = _helpers.ipc.sock_addr(env["BU_NAME"])
        if daemon_alive(env["BU_NAME"]):
            restart_daemon(env["BU_NAME"])
        ensure_daemon(name=env["BU_NAME"], env=env)
    else:
        ensure_daemon()
    exec(args[1], globals())


if __name__ == "__main__":
    main()
