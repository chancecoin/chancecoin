import sys
from cx_Freeze import setup, Executable

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

from lib import config

setup(  name = "Chancecoin",
        version = config.CLIENT_VERSION,
        description = "Chancecoin",
        options = {"build_exe": {"packages": ["os"], "includes": ["chancecoind"], "excludes": [], "include_files":["chancecoin.conf", "templates/casino.html","templates/index.html","templates/participate.html","templates/template.html","templates/wallet.html", "templates/error.html", "templates/technical.html","static/css/style.css","static/images/aperture_alt_32x32.png","static/images/calendar_alt_stroke_32x32.png","static/images/cog_32x32.png","static/images/dice_32x32.png","static/images/favicon.ico","static/images/fullscreen_exit_32x32.png","static/images/logo.png"]}},
        executables = [Executable("gui.py", base=base)])
