# --- main.py
# using fastapi to create a webui, communicating with infinity.py via engine.py
# use startup.sh to run JK THAT SCRIPT DOESNT WORK!!11`1`111111111 (maybe it does now)
# realizing that it might be difficult in the long run to add other games...
# ill give it a shot maybe probably but not right now

import os
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette import FileResponse

# importing classes and functions from infinity.py and engine.py
from infinity import InfinityBase, FIGURE_DATA_SIZE
from engine import usbEngine, HIDG_PATH

# those who log
logging.basicConfig(level=logging.INFO)
infinityLog = logging.getLogger("infinity")

base = InfinityBase()
stopEvent = threading.Event()

# starts the usb engine, after which you can see the base is picked up by the game
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.path.exists(HIDG_PATH):
        thread = threading.Thread(target=usbEngine, args=(base, stopEvent), daemon=True)
        thread.start()
        infinityLog.info("USB engine thread started.")
    else:
        infinityLog.warning(
            f"{HIDG_PATH} not found."
            "REST API is still available."
        )

    yield

    stopEvent.set()


app = FastAPI(title="RPi-Portal", lifespan=lifespan)


# requests for placing/removing figures through post
class PlaceFigureRequest(BaseModel):
    position: int
    filePath: str

class RemoveFigureRequest(BaseModel):
    position: int

# ----------------------------------------------------
# -------------------## WEB UI ##---------------------
# ----------------------------------------------------

# add functionality to power, reboot, hostname, game-switcher....... someday
# add functionality to settings too while youre at it
# and also display the website???



# ----------------------------------------------------
# ------------------## INFINITY ##--------------------
# ----------------------------------------------------

@app.get("/")
async def displayPage():
    return FileResponse('web/index.html')

# shows the status of the base, ie. what figures are/arent placed
@app.get("/figures")
def getFigures():
    result = {}
    for i, fig in enumerate(base.figures):
        result[i] = {
            "present": fig.present,
            "orderAdded": fig.orderAdded if fig.present else None,
        }
    return result

# places the figures on the base based on given position and filepath
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

# removes figure based on position
@app.post("/figures/remove")
def removeFigure(req: RemoveFigureRequest):
    if not (0 <= req.position < len(base.figures)):
        raise HTTPException(status_code=400, detail=f"position must be 0-{len(base.figures) - 1}")

    ok = base.removeFigure(req.position)
    if not ok:
        raise HTTPException(status_code=400, detail="no figure present at that position, or invalid slot")

    return {"status": "ok", "position": req.position}

# removes all figures altogether
@app.post("/figures/remove_all")
def removeAllFigures():
    removed = []
    for i in range(len(base.figures)):
        if base.removeFigure(i):
            removed.append(i)
    return {"status": "ok", "removed": removed}