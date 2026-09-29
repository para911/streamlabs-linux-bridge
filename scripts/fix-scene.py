#!/usr/bin/env python3
"""Clean up an OBS scene so the feed shows one full-frame capture instead of a collage.

The scene often ends up with several duplicated Screen Capture sources, each scaled down
and positioned at random. Streamlabs then shows a grid of small desktops on a black
background.

Important: OBS recomputes position and scale from the pos_rel/scale_rel/scale_ref fields
when they exist, and ignores absolute pos/scale written by hand. This script deletes those
fields, which is why it works where editing the JSON manually does not.

    python3 scripts/fix-scene.py                       # landscape, desktop fills the frame
    python3 scripts/fix-scene.py --portrait 1080x1920  # vertical: text top, desktop middle, webcam bottom

Run it while OBS is closed; OBS rewrites its scene file on exit.
"""
import argparse
import json
import pathlib
import shutil
import time

TEXT_Y_RATIO = 0.156   # top band
CAM_Y_RATIO = 0.844    # bottom band


def parse_res(s: str) -> tuple[int, int]:
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise SystemExit(f"invalid resolution: {s!r} (expected e.g. 1080x1920)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--portrait", metavar="WxH",
                    help="vertical canvas, e.g. 1080x1920 (default: read from the scene or the OBS profile)")
    ap.add_argument("--scene", default=None, help="scene file (default: most recently modified)")
    args = ap.parse_args()

    base = pathlib.Path.home() / ".config/obs-studio/basic/scenes"
    p = pathlib.Path(args.scene) if args.scene else max(base.glob("*.json"), key=lambda f: f.stat().st_mtime)
    d = json.loads(p.read_text())

    if args.portrait:
        W, H = parse_res(args.portrait)
    else:
        # The scene only stores custom_size if the user changed it; otherwise the real
        # size lives in the OBS profile. Last resort: 1920x1080.
        scene = next(s for s in d["sources"] if s["id"] == "scene")
        cs = scene["settings"].get("custom_size")
        if isinstance(cs, dict) and cs.get("x") and cs.get("y"):
            W, H = int(cs["x"]), int(cs["y"])
        else:
            ini = pathlib.Path.home() / ".config/obs-studio/basic/profiles/localbridge/basic.ini"
            W = H = None
            if ini.exists():
                for line in ini.read_text().splitlines():
                    if line.startswith("BaseCX="):
                        W = int(line.split("=", 1)[1])
                    elif line.startswith("BaseCY="):
                        H = int(line.split("=", 1)[1])
            W, H = W or 1920, H or 1080

    scene = next(s for s in d["sources"] if s["id"] == "scene")
    items = scene["settings"]["items"]

    caps = [i for i in items if i["name"].startswith("Screen Capture")]
    if not caps:
        raise SystemExit("no Screen Capture source found in this scene")
    keep = max(caps, key=lambda i: i["scale"]["x"])
    for i in caps:
        i["visible"] = i is keep

    def place(item, cx, cy, scale=None):
        item["align"] = 5                      # anchor at the item's center
        item["pos"] = {"x": float(cx), "y": float(cy)}
        if scale is not None:
            item["scale"] = {"x": scale, "y": scale}
        item["bounds"] = {"x": 0.0, "y": 0.0}
        item["bounds_type"] = 0
        for stale in ("pos_rel", "scale_rel", "scale_ref", "bounds_rel"):
            item.pop(stale, None)

    # A 16:9 desktop fitted to the width leaves a band above and below on a vertical canvas.
    desktop_w = 1920
    scale = W / desktop_w
    place(keep, W / 2, H / 2, scale=scale)

    text = next((i for i in items if i["name"].startswith("Text")), None)
    if text:
        place(text, W / 2, H * TEXT_Y_RATIO)
    cam = next((i for i in items if i["name"].startswith("Video Capture")), None)
    if cam:
        place(cam, W / 2, H * CAM_Y_RATIO)

    shutil.copy(p, p.with_suffix(f".json.bak-{time.strftime('%H%M%S')}"))
    p.write_text(json.dumps(d))

    assert sum(i["visible"] for i in caps) == 1, "exactly one screen capture must be visible"
    assert keep["scale"]["x"] == scale, "desktop must be fitted to the width"
    assert "scale_ref" not in keep and "pos_rel" not in keep, "relative fields must be removed"

    print("scene   :", p.name)
    print("canvas  :", f"{W}x{H}")
    print("desktop :", keep["name"], f"-> {W}x{int(1080 * scale)} centered")
    print("text    :", text["name"] if text else "-")
    print("webcam  :", cam["name"] if cam else "-")
    print("hidden  :", [i["name"] for i in caps if not i["visible"]])


if __name__ == "__main__":
    main()
