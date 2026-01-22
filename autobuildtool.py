# tool/autobuildtool.py
import sys
import subprocess
from pathlib import Path
import shutil
import os

# --- 安全なストリーム再設定（PyInstaller バンドル環境や Windows Runner 対策） ---
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# =====================
# Zig / C
# =====================

def find_zig():
    # 環境変数での指定を最優先
    env = os.environ.get("AUTOBUILD_ZIG")
    if env:
        p = Path(env)
        if p.exists():
            return p

    # PyInstallerでバンドルされたパス (sys._MEIPASS) をチェック
    if hasattr(sys, "_MEIPASS"):
        bundled_zig = Path(sys._MEIPASS) / "zig" / "zig.exe"
        if bundled_zig.exists():
            return bundled_zig

    # カレントディレクトリや相対パスのチェック
    for p in [
        Path("zig/zig.exe"),
        Path("tool/zig/zig.exe"),
    ]:
        if p.exists():
            return p

    # 最後にシステムのPATHをチェック
    p = shutil.which("zig")
    if p:
        return Path(p)

    return None



def build_with_zig(zig_path: Path, src: Path, out_name: str):
    cmd = [
        str(zig_path),
        "cc",
        str(src),
        "-O2",
        "-std=c11",
        "-target", "x86_64-windows-gnu",
        "-o",
        out_name,
    ]
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd).returncode


# =====================
# Python / PyInstaller
# =====================

def find_pyinstaller():
    p = shutil.which("pyinstaller")
    if p:
        return Path(p)
    return None


def build_python(pyinstaller: Path, src: Path, out_name: str):
    cmd = [
        str(pyinstaller),
        "--onefile",
        "--clean",
        "--name",
        Path(out_name).stem,
        str(src),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd).returncode


# =====================
# 共通ユーティリティ
# =====================

def normalize_out_name(name: str | None) -> str:
    if not name:
        return "a.exe"
    if not name.lower().endswith(".exe"):
        return name + ".exe"
    return name


def die(msg: str, code: int):
    print("ERROR:", msg)
    sys.exit(code)


# =====================
# メイン
# =====================

def main():
    print("AutoBuildTool (Windows) - start")

    src: Path | None = None
    out_name: str | None = None

    # --- argv 指定ルート ---
    if len(sys.argv) >= 2:
        src = Path(sys.argv[1])
        if not src.exists():
            die(f"source not found: {src}", 2)

        if len(sys.argv) >= 3:
            out_name = sys.argv[2]

    # --- 自動検出ルート ---
    else:
        cwd = Path.cwd()
        main_c = cwd / "main.c"
        main_py = cwd / "main.py"

        has_c = main_c.exists()
        has_py = main_py.exists()

        if has_c and has_py:
            die("both main.c and main.py exist (ambiguous)", 10)
        if not has_c and not has_py:
            die("main.c or main.py not found", 1)

        src = main_c if has_c else main_py

    out_name = normalize_out_name(out_name)

    # =====================
    # 分岐実行
    # =====================

    if src.suffix == ".c":
        zig = find_zig()
        if not zig:
            die("zig not found", 3)

        print("Using zig:", zig)
        print(f"Building C: {src} -> {out_name}")
        rc = build_with_zig(zig, src, out_name)
        if rc != 0:
            die("C build failed", rc)

    elif src.suffix == ".py":
        pyinstaller = find_pyinstaller()
        if not pyinstaller:
            die("pyinstaller not found (pip install pyinstaller)", 4)

        print("Using pyinstaller:", pyinstaller)
        print(f"Building Python: {src} -> {out_name}")
        rc = build_python(pyinstaller, src, out_name)
        if rc != 0:
            die("Python build failed", rc)

    else:
        die(f"unsupported source type: {src.suffix}", 5)

    print("Build succeeded. Created:", out_name)
    sys.exit(0)


if __name__ == "__main__":
    main()
