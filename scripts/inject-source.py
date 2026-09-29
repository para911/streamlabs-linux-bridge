import argparse
import json
import pathlib
import sys
import uuid

DEFAULT_URL = "rtmp://127.0.0.1:1935/live/desk"
NAME = "Desktop (local bridge)"


def slobs_dir() -> pathlib.Path:
    base = pathlib.Path.home() / ".local/share/streamlabs/drive_c/users"
    users = [u for u in base.iterdir() if u.name not in ("Public", "Default", "Default User")]
    if not users:
        sys.exit("Wine prefix not found - run install.sh first.")
    return users[0] / "AppData/Roaming/slobs-client"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL, help=f"video URL (default: {DEFAULT_URL})")
    args = ap.parse_args()

    root = slobs_dir() / "SceneCollections"
    manifest = json.loads((root / "manifest.json").read_text())
    coll = root / f"{manifest['activeId']}.json"
    d = json.loads(coll.read_text())

    items = d["sources"]["items"]
    drop = {s["id"] for s in items if s.get("type") in ("monitor_capture", "ffmpeg_source", "dshow_input")}
    items[:] = [s for s in items if s["id"] not in drop]

    new = {
        "hotkeys": {"schemaVersion": 2, "nodeType": "HotkeysNode", "items": []},
        "id": "ffmpeg_source_" + str(uuid.uuid4()),
        "name": NAME,
        "type": "ffmpeg_source",
        "versioned_id": "ffmpeg_source",
        "settings": {
            "is_local_file": False, "input": args.url, "input_format": "",
            "looping": False, "restart_on_activate": True, "close_when_inactive": False,
            "clear_on_media_end": False, "buffering_mb": 1, "seekable": False, "speed_percent": 100,
        },
        "volume": 1, "muted": True, "filters": {"items": []}, "propertiesManager": "default",
    }
    items.append(new)

    for sc in d["scenes"]["items"]:
        si = sc["sceneItems"]["items"]
        si[:] = [i for i in si if i.get("sourceId") not in drop]
        si.append({
            "hotkeys": {"schemaVersion": 2, "nodeType": "HotkeysNode", "items": []},
            "id": str(uuid.uuid4()), "sourceId": new["id"], "visible": True, "locked": False,
            "transform": {"schemaVersion": 2, "position": {"x": 0, "y": 0}, "scale": {"x": 1, "y": 1},
                          "rotation": 0, "crop": {"left": 0, "top": 0, "right": 0, "bottom": 0}},
            "filters": {"schemaVersion": 1, "nodeType": "SceneFiltersNode", "items": []},
            "blendMethod": "default", "blendMode": "normal", "showTransition": False,
        })

    coll.write_text(json.dumps(d))
    print("collection:", coll.name)
    print("sources   :", [(s["name"], s["type"]) for s in items])
    print("url       :", args.url)


if __name__ == "__main__":
    main()
