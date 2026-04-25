import os
import sys
from io import StringIO
from unittest.mock import patch

from browser_harness import run


def test_c_flag_executes_code():
    stdout = StringIO()
    with patch.object(sys, "argv", ["browser-harness", "-c", "print('hello from -c')"]), \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"), \
         patch("sys.stdout", stdout):
        run.main()
    assert stdout.getvalue().strip() == "hello from -c"


def test_c_flag_does_not_read_stdin():
    stdin_read = []
    fake_stdin = StringIO("should not be read")
    fake_stdin.read = lambda: stdin_read.append(True) or ""

    with patch.object(sys, "argv", ["browser-harness", "-c", "x = 1"]), \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"), \
         patch("sys.stdin", fake_stdin):
        run.main()

    assert not stdin_read, "stdin should not be read when -c is passed"


def test_kameleo_profile_sets_env_before_named_daemon():
    calls = []

    def fake_ensure_daemon(name=None, env=None):
        calls.append((
            "ensure",
            name,
            env,
            os.environ.get("BU_NAME"),
            os.environ.get("BU_CDP_WS"),
            run._helpers.SOCK,
        ))

    with patch.object(sys, "argv", ["browser-harness", "--kameleo-profile", "worker", "-c", "x = 1"]), \
         patch("browser_harness.run.kameleo.attach_env", return_value={"BU_NAME": "worker-run", "BU_CDP_WS": "ws://example"}), \
         patch("browser_harness.run.daemon_alive", return_value=False), \
         patch("browser_harness.run.ensure_daemon", side_effect=fake_ensure_daemon), \
         patch("browser_harness.run.print_update_banner"):
        run.main()

    assert calls == [(
        "ensure",
        "worker-run",
        {"BU_NAME": "worker-run", "BU_CDP_WS": "ws://example"},
        "worker-run",
        "ws://example",
        "/tmp/bu-worker-run.sock",
    )]
