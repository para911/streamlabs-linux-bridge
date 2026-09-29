#!/usr/bin/env bash
# One-shot installer: Wine prefix, Streamlabs payload, mediamtx, OBS profile, launchers.
# It does not touch any existing OBS profile.
set -euo pipefail

VERSION="1.21.9"
SL_URL="https://slobs-cdn.streamlabs.com/Streamlabs+Desktop+Setup+${VERSION}.exe"
MTX_VERSION="v1.21.1"
MTX_URL="https://github.com/bluenviron/mediamtx/releases/download/${MTX_VERSION}/mediamtx_${MTX_VERSION}_linux_amd64.tar.gz"

PREFIX="$HOME/.local/share/streamlabs"
APP_DIR="$PREFIX/drive_c/Program Files/Streamlabs"
CACHE="$HOME/.cache/streamlabs-linux-bridge"
BIN="$HOME/.local/bin"
REPO="$(cd "$(dirname "$0")" && pwd)"

say() { printf '\n=== %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

say "checking dependencies"
for c in wine 7z curl tar; do
	command -v "$c" >/dev/null || die "$c not found. Fedora: sudo dnf install -y wine p7zip curl tar"
done
mkdir -p "$CACHE" "$BIN"

if [ ! -d "$PREFIX" ]; then
	say "creating Wine prefix ($PREFIX)"
	WINEPREFIX="$PREFIX" WINEDEBUG=-all wineboot -u
	sleep 3
fi

say "downloading Streamlabs Desktop $VERSION (~287 MB, skipped if cached)"
[ -f "$CACHE/setup.exe" ] || curl -fL --progress-bar -o "$CACHE/setup.exe" "$SL_URL"
[ -s "$CACHE/setup.exe" ] || die "download failed"

if [ ! -f "$APP_DIR/Streamlabs OBS.exe" ]; then
	say "extracting the installer payload (the NSIS installer itself fails under Wine)"
	rm -rf "$CACHE/nsis"
	mkdir -p "$CACHE/nsis"
	7z x -y -o"$CACHE/nsis" "$CACHE/setup.exe" >/dev/null
	PAYLOAD="$CACHE/nsis/\$PLUGINSDIR/app-64.7z"
	[ -f "$PAYLOAD" ] || die "payload not found in the installer (did the $VERSION layout change?)"
	mkdir -p "$APP_DIR"
	7z x -y -o"$APP_DIR" "$PAYLOAD" >/dev/null
	rm -rf "$CACHE/nsis"
fi
[ -f "$APP_DIR/Streamlabs OBS.exe" ] || die "Streamlabs OBS.exe missing after extraction"
say "Streamlabs ready: $APP_DIR/Streamlabs OBS.exe"

say "installing mediamtx $MTX_VERSION"
MTX_DIR="$HOME/.local/share/mediamtx"
if [ ! -x "$MTX_DIR/mediamtx" ]; then
	mkdir -p "$MTX_DIR"
	curl -fL --progress-bar -o "$CACHE/mediamtx.tar.gz" "$MTX_URL"
	tar -xzf "$CACHE/mediamtx.tar.gz" -C "$MTX_DIR"
fi
cp "$REPO/config/mediamtx.yml" "$MTX_DIR/local.yml"
say "mediamtx ready (RTMP 127.0.0.1:1935, HLS 127.0.0.1:8888)"

say "installing OBS profile 'localbridge'"
PROFILE_DIR="$HOME/.config/obs-studio/basic/profiles/localbridge"
if [ -d "$PROFILE_DIR" ]; then
	echo "profile already exists, leaving it alone (delete it manually to overwrite)"
else
	mkdir -p "$PROFILE_DIR"
	cp "$REPO/config/obs/localbridge.ini" "$PROFILE_DIR/basic.ini"
	cp "$REPO/config/obs/service.json" "$PROFILE_DIR/service.json"
fi

if ! rpm -q obs-studio-plugin-x264 >/dev/null 2>&1; then
	echo
	echo "WARNING: obs-studio-plugin-x264 is not installed."
	echo "Without it OBS falls back to Fedora's OpenH264, which sends an EMPTY video track"
	echo "and the Streamlabs preview stays black. Install it with:"
	echo "  sudo dnf install -y obs-studio-plugin-x264"
fi

say "installing launchers to $BIN"
for f in streamlabs streamlabs-retry desktop-bridge; do
	install -m 755 "$REPO/bin/$f" "$BIN/$f"
done
install -d "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
install -m 644 "$REPO/config/streamlabs.desktop" "$HOME/.local/share/applications/streamlabs-desktop.desktop"
[ -f "$REPO/config/streamlabs.svg" ] && install -m 644 "$REPO/config/streamlabs.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/streamlabs.svg"
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

cat <<EOF

=== done

Run:                   desktop-bridge
One-time app setup:    Sources -> + -> Media File -> uncheck "Local File"
                       -> Input: rtmp://127.0.0.1:1935/live/desk
Problems?              see docs/TROUBLESHOOTING.md
EOF
