import sys, importlib.metadata as md
import vpype, vpype_cli
print(sys.version)
for pkg in ("vpype", "numpy", "scipy", "shapely", "pillow", "svgelements", "python-multipart"):
    try: print(pkg, md.version(pkg))
    except Exception: print(pkg, "-")
print("vpype:", [n for n in dir(vpype) if not n.startswith("_")])
lc = vpype.LineCollection()
print("LineCollection:", [n for n in dir(lc) if not n.startswith("_")])
print("vpype_cli:", [n for n in dir(vpype_cli) if not n.startswith("_")])