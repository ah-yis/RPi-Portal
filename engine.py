# --- engine.py
# bridge b/w hidg0 and base emulator

import os
import time
import threading
import logging

from infinity import InfinityBase

infinityLog = logging.getLogger("infinity")

HIDG_PATH = "/dev/hidg0"
REPORT_SIZE = 32


def notifyEngine(base: InfinityBase, fd: int, writeLock: threading.Lock, stopEvent: threading.Event):
    while not stopEvent.is_set():
        response = base.popAddedRemovedResponse()
        if response is not None:
            try:
                with writeLock:
                    os.write(fd, response)
            except OSError as e:
                infinityLog.error(f"notifyEngine write failed: {e}")
        else:
            time.sleep(0.05)


def handleCommand(base: InfinityBase, buf: bytes, qResult: bytearray) -> bool:
    command = buf[2]
    sequence = buf[3]

    if command == 0x80:
        qResult[0:24] = [
            0xAA, 0x15, 0x00, 0x00, 0x0F, 0x01, 0x00, 0x03, 0x02, 0x09, 0x09, 0x43,
            0x20, 0x32, 0x62, 0x36, 0x36, 0x4B, 0x34, 0x99, 0x67, 0x31, 0x93, 0x8C,
        ]
    elif command == 0x81:
        base.descrambleAndSeed(buf, sequence, qResult)
    elif command == 0x83:
        base.getNextAndScramble(sequence, qResult)
    elif command in (0x90, 0x92, 0x93, 0x95, 0x96, 0xB5):
        base.getBlankResponse(sequence, qResult)
    elif command == 0xA1:
        base.getPresentFigures(sequence, qResult)
    elif command == 0xA2:
        base.queryBlock(buf[4], buf[5], qResult, sequence)
    elif command == 0xA3:
        base.writeBlock(buf[4], buf[5], buf[7:23], qResult, sequence)
    elif command == 0xB4:
        base.getFigureIdentifier(buf[4], sequence, qResult)
    else:
        infinityLog.warning(f"Unhandled query type: 0x{command:02X}")
        return False

    return True


def usbEngine(base: InfinityBase, stopEvent: threading.Event = None):
    if stopEvent is None:
        stopEvent = threading.Event()

    fd = os.open(HIDG_PATH, os.O_RDWR)
    writeLock = threading.Lock()

    notifyThread = threading.Thread(
        target=notifyEngine, args=(base, fd, writeLock, stopEvent), daemon=True
    )
    notifyThread.start()

    infinityLog.info(f"usbEngine listening on {HIDG_PATH}")

    try:
        while not stopEvent.is_set():
            try:
                buf = os.read(fd, REPORT_SIZE)
            except OSError as e:
                infinityLog.error(f"usbEngine read failed: {e}")
                time.sleep(0.1)
                continue

            if not buf or len(buf) < REPORT_SIZE:
                continue

            qResult = bytearray(REPORT_SIZE)

            try:
                shouldWrite = handleCommand(base, buf, qResult)
            except Exception as e:
                infinityLog.error(f"Error handling command 0x{buf[2]:02X}: {e}")
                continue

            if shouldWrite:
                try:
                    with writeLock:
                        os.write(fd, qResult)
                except OSError as e:
                    infinityLog.error(f"usbEngine write failed: {e}")
    finally:
        stopEvent.set()
        os.close(fd)