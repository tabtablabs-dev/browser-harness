"""Kameleo Local API adapter for browser-harness.

Kameleo owns the browser profile lifecycle. browser-harness only needs a CDP
websocket and a socket namespace, so this module returns BU_* env vars.
"""
import json, os, re, subprocess, time, urllib.request


KAMELEO_API = "http://127.0.0.1:5050"


def _json(url, method="GET", body=None, timeout=15):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read() or b"{}")


def _profile(api, name):
    profiles = _json(f"{api}/profiles")
    matches = [p for p in profiles if p.get("name") == name]
    if not matches:
        raise RuntimeError(f"Kameleo profile {name!r} not found")
    if len(matches) > 1:
        ids = ", ".join(p.get("id", "?") for p in matches)
        raise RuntimeError(f"multiple Kameleo profiles named {name!r}: {ids}")
    return matches[0]


def _status(api, profile_id):
    return _json(f"{api}/profiles/{profile_id}/status").get("lifetimeState")


def _start(api, profile_id, wait=45):
    state = _status(api, profile_id)
    if state == "running":
        return state
    _json(f"{api}/profiles/{profile_id}/start", method="POST", body={}, timeout=30)
    deadline = time.time() + wait
    while time.time() < deadline:
        state = _status(api, profile_id)
        if state == "running":
            return state
        time.sleep(1)
    raise RuntimeError(f"Kameleo profile {profile_id} did not start; last state={state!r}")


def _debugging_port(profile_id):
    ps = subprocess.check_output(["ps", "-ax", "-o", "pid,command"], text=True)
    line = next((
        l for l in ps.splitlines()
        if profile_id in l
        and "--remote-debugging-port=" in l
        and "Chroma Helper" not in l
        and ("MacOS/Chroma " in l or "/Chroma " in l)
    ), None)
    if not line:
        raise RuntimeError(f"no Kameleo Chroma main process matched profile id {profile_id}")
    m = re.search(r"--remote-debugging-port=(\d+)", line)
    if not m:
        raise RuntimeError(f"matched Kameleo Chroma process but no remote debugging port: {line}")
    return m.group(1)


def attach_env(profile_name, api=None, name=None, wait=45):
    """Resolve/start a Kameleo profile and return BU_NAME/BU_CDP_WS env."""
    api = (api or os.environ.get("KAMELEO_API") or KAMELEO_API).rstrip("/")
    profile_id = _profile(api, profile_name)["id"]
    _start(api, profile_id, wait=wait)
    port = _debugging_port(profile_id)
    ws = _json(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"]
    bu_name = name or f"{profile_name}-{int(time.time())}-{os.getpid()}"
    return {"BU_NAME": bu_name, "BU_CDP_WS": ws}
