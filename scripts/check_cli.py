from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
commands = [
    "/liste",
    "T01 ve T02 turlarını kahvaltı açısından karşılaştır.",
    "Bütçem 7000 TL; gece otobüs yolculuğu istemiyorum.",
    "/sifirla",
    "/cikis",
]
environment = dict(os.environ, PYTHONUTF8="1")
process = subprocess.run(
    [sys.executable, "tour_compare.py"],
    cwd=ROOT,
    input="\n".join(commands) + "\n",
    text=True,
    encoding="utf-8",
    capture_output=True,
    timeout=180,
    env=environment,
)
checks = {
    "exit_code_zero": process.returncode == 0,
    "catalogue_displayed": "T20  Safranbolu" in process.stdout,
    "selected_tours_displayed": all(
        name in process.stdout for name in ("T01 — Kapadokya", "T02 — Kapadokya")
    ),
    "followup_constraint_applied": "Koşullara uymuyor" in process.stdout,
    "reset_acknowledged": "Konuşma koşulları temizlendi." in process.stdout,
    "no_application_error": "Hata:" not in process.stdout and not process.stderr,
}
(ROOT / "evaluation/cli_smoke.txt").write_text(
    process.stdout + "\nSTDERR\n" + process.stderr, encoding="utf-8"
)
result = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "commands": commands,
    "return_code": process.returncode,
    "checks": checks,
    "passed": all(checks.values()),
}
(ROOT / "evaluation/cli_smoke.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result["passed"] else 1)
