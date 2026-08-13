# --- main.py
# ugh does the working you know how it is

import os
import subprocess
import logging
import threading
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from infinity import InfinityBase, FIGURE_DATA_SIZE
from engine import usbEngine, HIDG_PATH
from catalog import scanCatalog

WEB_ROOT = Path(__file__).parent / "web"
RESOURCES_ROOT = WEB_ROOT / "resources"

logging.basicConfig(level=logging.INFO)
infinityLog = logging.getLogger("infinity")

base = InfinityBase()
stopEvent = threading.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    if os.path.exists(HIDG_PATH):
        thread = threading.Thread(target=usbEngine, args=(base, stopEvent), daemon=True)
        thread.start()
        infinityLog.info("USB engine thread started.")
    else:
        infinityLog.warning(
            f"{HIDG_PATH} not found - USB gadget engine not started. "
            "REST API is still available for testing."
        )

    yield

    # shutdown (not that one the other one)
    stopEvent.set()


app = FastAPI(title="RPi-Portal", lifespan=lifespan)


# ---------------------------------------------------------------------
# --------------------------## MODELS ##-------------------------------
# ---------------------------------------------------------------------

class PlaceFigureRequest(BaseModel):
    position: int
    filePath: str


class RemoveFigureRequest(BaseModel):
    position: int


# delays a command. uh thats baically it. we will use it to make sure
# ...that our reboot/shutdown works correctly
def _delayedCommand(cmd: list[str], delay: float = 1.0):
    time.sleep(delay)
    subprocess.run(cmd, check=False)


# ---------------------------------------------------------------------
# -------------------------## ROUTES ##--------------------------------
# ---------------------------------------------------------------------


# return status of all slots
@app.get("/figures")
def getFigures():
    result = {}
    for i, fig in enumerate(base.figures):
        result[i] = {
            "present": fig.present,
            "orderAdded": fig.orderAdded if fig.present else None,
        }
    return result


# place stuff in the slots
@app.post("/figures/place")
def placeFigure(req: PlaceFigureRequest):
    if not (0 <= req.position < len(base.figures)):
        raise HTTPException(status_code=400, detail=f"position must be 0-{len(base.figures) - 1}")

    if not os.path.isfile(req.filePath):
        raise HTTPException(status_code=404, detail=f"file not found: {req.filePath}")

    with open(req.filePath, "rb") as f:
        buf = f.read()

    if len(buf) != FIGURE_DATA_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"expected {FIGURE_DATA_SIZE} bytes, got {len(buf)}",
        )

    inFile = open(req.filePath, "r+b")

    try:
        number = base.loadFigure(buf, inFile, req.position)
    except Exception as e:
        inFile.close()
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "number": number, "position": req.position}


# removes stuff from slots
@app.post("/figures/remove")
def removeFigure(req: RemoveFigureRequest):
    if not (0 <= req.position < len(base.figures)):
        raise HTTPException(status_code=400, detail=f"position must be 0-{len(base.figures) - 1}")

    ok = base.removeFigure(req.position)
    if not ok:
        raise HTTPException(status_code=400, detail="no figure present at that position, or invalid slot")

    return {"status": "ok", "position": req.position}


# removes stuff from ALL slots
@app.post("/figures/remove_all")
def removeAllFigures():
    removed = []
    for i in range(len(base.figures)):
        if base.removeFigure(i):
            removed.append(i)
    return {"status": "ok", "removed": removed}


# getting the files using catalog.py
@app.get("/catalog")
def getCatalog(franchise: str = "infinity"):
    entries = scanCatalog(RESOURCES_ROOT, franchise)
    for entry in entries:
        entry["image"] = f"resources/{entry['image']}"
    return entries


# ---------------------------------------------------------------------
# ---------------------------## SYS ##---------------------------------
# ---------------------------------------------------------------------

# reboot sys
@app.post("/system/reboot")
def systemReboot():
    try:
        threading.Thread(target=_delayedCommand, args=(["systemctl","reboot","-i"],), daemon=True).start()
        return {"status": "ok", "message": "Rebooting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# shutdown sys
@app.post("/system/shutdown")
def systemShutdown():
    try:
        threading.Thread(target=_delayedCommand, args=(["systemctl","poweroff", "-i"],), daemon=True).start()
        return {"status": "ok", "message": "Shutting down..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------
# --------------## THING THAT MOUNTS THE SITE ##-----------------------
# ---------------------------------------------------------------------

if WEB_ROOT.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_ROOT), html=True), name="web")
else:
    infinityLog.warning(f"{WEB_ROOT} not found. fix yo directories yo")