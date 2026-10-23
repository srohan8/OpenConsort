"""Small local API for the frontend (stdlib only, localhost only).

    POST /api/plan   {"idea": "..."}  ->  {"locked_spec", "user_flow", "scenarios", "openspec": {...}}
    GET  /api/health                  ->  {"ok": true}

Runs the orchestrator's Planning stage. Failures come back as {"error": "..."} with a
non-200 status (the orchestrator reports schema/parse failures via SystemExit).
"""
import datetime
import json
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openspec_bridge import write_change
from orchestrator import ROOT, build_stage_llms, run_planning

HOST, PORT = "127.0.0.1", 8787
MAX_BODY = 20_000


def write_and_validate_openspec(run_id: str, idea: str, locked_spec: dict, user_flow: dict, scenarios: dict) -> dict:
    """Write the plan as an OpenSpec change under projects/<run_id>/ and run `openspec validate --strict`."""
    out_dir = ROOT / "projects" / run_id
    change = write_change(out_dir, idea, locked_spec, user_flow, scenarios=scenarios)
    result = {"path": str(change), "valid": None, "output": "openspec CLI not found - skipped validation"}
    exe = shutil.which("openspec")
    if exe:
        proc = subprocess.run(
            [exe, "validate", change.name, "--strict"], cwd=out_dir, capture_output=True, text=True, timeout=60
        )
        result.update(valid=proc.returncode == 0, output=(proc.stdout + proc.stderr).strip()[:1000])
    return result


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/plan":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY:
                return self._send(413, {"error": "request too large"})
            idea = str(json.loads(self.rfile.read(length) or b"{}").get("idea", "")).strip()
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "body must be JSON"})
        if not idea:
            return self._send(400, {"error": "idea is required"})

        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_api"
        try:
            llm = build_stage_llms(False, False)["planning"]
            locked_spec, user_flow, scenarios = run_planning(run_id, llm, idea)
            openspec = write_and_validate_openspec(run_id, idea, locked_spec, user_flow, scenarios)
        except SystemExit as e:  # orchestrator's failure path
            return self._send(502, {"error": str(e.code)[:1000]})
        except Exception as e:  # network/auth errors from the LLM client
            if type(e).__name__ == "APIConnectionError":
                msg = f"Can't reach the planning model at {llm.client.base_url}. Check that it is running (and PLANNING_MODEL / CLOUD_BASE_URL in .env)."
            else:
                msg = f"{type(e).__name__}: {str(e)[:500]}"
            return self._send(502, {"error": msg})
        self._send(200, {"locked_spec": locked_spec, "user_flow": user_flow, "scenarios": scenarios, "openspec": openspec})


if __name__ == "__main__":
    print(f"OpenConsort API on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
