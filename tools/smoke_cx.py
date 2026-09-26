"""Exercise a running CX app through HTTP; never sends a prompt to LM Studio."""
import argparse
import array
import io
import json
from pathlib import Path
import sys
import time
import traceback
import urllib.error
import urllib.request
import wave

SENTENCES = ["こんにちは。今日もお話しできて、うれしいです。",
             "少し休憩しませんか。温かいお茶を入れましょう。",
             "大丈夫。焦らず、一つずつ進めていきましょう。",
             "明日の午後三時に、駅の改札で待っています。",
             "おやすみなさい。また明日、あなたの声を聞かせてください。"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:7862")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 20:
        parser.error("rounds must be 1..20")
    job = args.output
    job.mkdir(parents=True, exist_ok=False)
    def write(name, value):
        (job / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "command.txt").write_text(repr(sys.argv), encoding="utf-8")
    write("status.json", {"state": "running", "started": time.time()})
    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(args.url.rstrip("/") + path, data=data,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    rows = []
    code = 1
    with (job / "run.log").open("w", encoding="utf-8", buffering=1) as log:
        try:
            status = json.loads(request("/api/status"))
            write("environment.json", status)
            assert status["diagnostics"]["runtimeMode"] == "cx", "Not a CX server"
            for index, text in enumerate(SENTENCES * args.rounds):
                start = time.perf_counter()
                result = json.loads(request("/api/speak", {"text": text, "steps": 40, "wait": True}))
                event = result.get("event", {})
                assert result.get("ok") and event.get("audios"), result
                for chunk, audio in enumerate(event["audios"]):
                    assert audio["runtimeMode"] == "cx"
                    assert audio["modelDevice"] == "cuda" and audio["codecDevice"] == "cpu"
                    assert audio["watermarkEnabled"] is False
                    data = request(audio["url"])
                    with wave.open(io.BytesIO(data)) as wav:
                        assert wav.getsampwidth() == 2 and wav.getnframes() > 0
                        samples = array.array("h", wav.readframes(wav.getnframes()))
                        assert max(abs(x) for x in samples) > 0
                        duration = wav.getnframes() / wav.getframerate()
                    name = f"{index + 1:03d}_{chunk + 1}.wav"
                    (job / name).write_bytes(data)
                    rows.append(dict(index=index, wav=name, duration=duration,
                                     httpSeconds=time.perf_counter() - start, metadata=audio))
                write("results.json", rows)
                print(f"PASS {index + 1}/{5 * args.rounds}", file=log, flush=True)
            events = json.loads(request("/api/speak-events?after=0"))
            assert events["events"], "No UI speech events"
            write("events.json", events)
            write("status.json", {"state": "completed", "exit_code": 0, "time": time.time()})
            (job / "outputs.txt").write_text("\n".join(row["wav"] for row in rows), encoding="utf-8")
            code = 0
        except BaseException as exc:
            traceback.print_exc(file=log)
            write("status.json", {"state": "failed", "exit_code": 1, "error": str(exc)})
            (job / "BLOCKED.md").write_text(str(exc), encoding="utf-8")
        finally:
            (job / "DONE.txt").write_text(str(time.time()), encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
