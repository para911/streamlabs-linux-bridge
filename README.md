# streamlabs-linux-bridge

Run Streamlabs Desktop (Windows) on Linux through Wine, with working screen capture,
including vertical 9:16 output for TikTok.

## The problem

Streamlabs Desktop's screen capture does not work under Wine. It uses Windows Graphics
Capture, which Wine does not implement, so the preview is black and selecting the capture
source can crash the app.

This project works around that by routing video through a local RTMP server:

```
OBS (Linux, native)  --RTMP-->  mediamtx  --RTMP-->  Streamlabs (Wine)
 captures the screen          127.0.0.1:1935          reads it as a Media Source
```

OBS Studio for Linux does the capturing. It publishes to a local RTMP server, and
Streamlabs reads that stream as a regular media source. No kernel modules, no patched
binaries, and your existing OBS profiles are left alone.

## Requirements

- Wine 9 or newer
- OBS Studio (native Linux build)
- `7z`, `curl`, `tar`, Python 3
- Fedora or another RPM-based distribution

On Fedora:

```bash
sudo dnf install -y wine p7zip obs-studio ffmpeg obs-studio-plugin-x264
```

`obs-studio-plugin-x264` is not optional. The OpenH264 encoder shipped with Fedora emits
a video track with no SPS, which Streamlabs cannot decode: the preview stays black even
though data is flowing.

## Install

```bash
git clone https://github.com/<user>/streamlabs-linux-bridge
cd streamlabs-linux-bridge
./install.sh
```

The installer downloads the official Streamlabs 1.21.9 installer from its CDN and extracts
the payload directly into a Wine prefix. The NSIS installer itself is skipped because it
fails under Wine; only its payload is used.

## Run

```bash
desktop-bridge
```

This starts mediamtx, launches OBS with the `localbridge` profile already streaming, and
opens Streamlabs. Wait about a minute for the window to appear.

## One-time setup inside Streamlabs

1. **Sources -> + -> Media File**. ("Media File" is Streamlabs' name for OBS's Media Source.)
2. Uncheck **Local File**. The Input field only appears when it is off.
3. Set **Input** to `rtmp://127.0.0.1:1935/live/desk` and leave Input Format empty.
4. Click OK.

Do not use Browser Source for this; it plays web pages, not video streams. Do not add a
Display Capture source inside Wine; the preview will be black and the app may crash.

## Vertical 9:16 output

Both sides have to be changed, or the output stays landscape.

**OBS:** `~/.config/obs-studio/basic/profiles/localbridge/basic.ini`:

```ini
BaseCX=1080
BaseCY=1920
OutputCX=1080
OutputCY=1920
```

**Streamlabs:** Settings -> Video -> set base and output resolution to 1080x1920.

Then arrange the scene (text band on top, screen capture centered, webcam below):

```bash
python3 scripts/fix-scene.py --portrait 1080x1920
```

Run this while OBS is closed. OBS rewrites its scene file on exit, so edits made while it
is running are lost.

## Notes

- Audio from OBS is already carried by the RTMP stream, so the Media Source is muted in
  Streamlabs to avoid doubling.
- HLS is not used. mediamtx closes idle HLS sessions, which makes Streamlabs report
  `Failed to open media` after a few minutes of inactivity.
- `v4l2loopback` is a valid alternative to RTMP, but it requires signing a kernel module
  for Secure Boot and rebooting. This project avoids kernel changes entirely.

## Open source & contributions

This project is open source. Feel free to fork it, modify it, fix bugs, improve existing
features, or add support for other Linux distributions.

Contributions and pull requests are welcome, especially for improving compatibility with
Linux distributions that are not currently supported.

The project currently focuses primarily on Fedora and RPM-based distributions, but support
for additional Linux distributions is planned for future updates.

If you manage to get it working on another distribution, feel free to contribute your
changes back to the project so other users can benefit from them as well.

## License

MIT. Not affiliated with Streamlabs or TikTok. Streamlabs Desktop is downloaded from its
official CDN during installation; no copyrighted binaries are redistributed here.

