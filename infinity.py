# --- infinity.py
# reimplementation of most logic from rpcs3, handles firmware of the base

import threading
import hashlib
import logging
from collections import deque
from Crypto.Cipher import AES

infinityLog = logging.getLogger("infinity")

FIGURE_DATA_SIZE = 0x14 * 0x10
NUM_SLOTS = 9

SHA1_CONSTANT = bytes([
    0xAF, 0x62, 0xD2, 0xEC, 0x04, 0x91, 0x96, 0x8C, 0xC5, 0x2A, 0x1A, 0x71, 0x65, 0xF8, 0x65, 0xFE,
    0x28, 0x63, 0x29, 0x20, 0x44, 0x69, 0x73, 0x6e, 0x65, 0x79, 0x20, 0x32, 0x30, 0x31, 0x33,
])


def rotl(value: int, shift: int, width: int = 32) -> int:
    """Bit-rotate-left, matching C++20's std::rotl<u32>."""
    shift %= width
    mask = (1 << width) - 1
    value &= mask
    return ((value << shift) | (value >> (width - shift))) & mask


# ---------------------------------------------------------------------
# InfinityFigure
# ---------------------------------------------------------------------

class InfinityFigure:
    def __init__(self):
        self.infFile = None
        self.data = bytearray(FIGURE_DATA_SIZE)
        self.present = False
        self.orderAdded = 255

    def save(self):
        if not self.infFile:
            infinityLog.error(
                "Tried to save infinity figure to file but no infinity figure is active!"
            )
            return

        self.infFile.seek(0)
        self.infFile.write(self.data[:FIGURE_DATA_SIZE])
        self.infFile.flush()


# ---------------------------------------------------------------------
# InfinityBase
# ---------------------------------------------------------------------

class InfinityBase:

    # run on init
    def __init__(self):
        self.randomA = self.randomB = self.randomC = self.randomD = 0
        self.mask = 0x8E55AA1B3999E8AA

        self.infinityMutex = threading.RLock()
        self.figures = [InfinityFigure() for _ in range(NUM_SLOTS)]

        self.mFigureOrder = 0
        self.mFigureAddedRemovedResponses = deque()


    def generateChecksum(self, data, numOfBytes: int) -> int:
        checksum = 0
        for i in range(numOfBytes):
            checksum += data[i]
        return checksum & 0xFF


    def getBlankResponse(self, sequence: int, replyBuf: bytearray):
        replyBuf[0] = 0xAA
        replyBuf[1] = 0x01
        replyBuf[2] = sequence
        replyBuf[3] = self.generateChecksum(replyBuf, 3)


    def descrambleAndSeed(self, buf, sequence: int, replyBuf: bytearray):
        value = int.from_bytes(buf[4:12], "big")
        seed = self.descramble(value)
        self.generateSeed(seed)
        self.getBlankResponse(sequence, replyBuf)


    def getNextAndScramble(self, sequence: int, replyBuf: bytearray):
        nextRandom = self.getNext()
        scrambledNextRandom = self.scramble(nextRandom, 0)
        replyBuf[0] = 0xAA
        replyBuf[1] = 0x09
        replyBuf[2] = sequence
        replyBuf[3:11] = scrambledNextRandom.to_bytes(8, "big")
        replyBuf[11] = self.generateChecksum(replyBuf, 11)


    def descramble(self, numToDescramble: int) -> int:
        mask = self.mask
        ret = 0
        for _ in range(64):
            if mask & 0x8000000000000000:
                ret = (ret << 1) | (numToDescramble & 0x01)
            numToDescramble >>= 1
            mask <<= 1
        return ret & 0xFFFFFFFF


    def scramble(self, numToScramble: int, garbage: int) -> int:
        mask = self.mask
        ret = 0
        for _ in range(64):
            ret <<= 1
            if (mask & 1) != 0:
                ret |= (numToScramble & 1)
                numToScramble >>= 1
            else:
                ret |= (garbage & 1)
                garbage >>= 1
            mask >>= 1
        return ret & 0xFFFFFFFFFFFFFFFF


    def generateSeed(self, seed: int):
        self.randomA = 0xF1EA5EED
        self.randomB = self.randomC = self.randomD = seed
        for _ in range(23):
            self.getNext()


    def getNext(self) -> int:
        a, b, c = self.randomA, self.randomB, self.randomC
        ret = rotl(self.randomB, 27)

        temp = (a + ((ret ^ 0xFFFFFFFF) + 1)) & 0xFFFFFFFF
        b = (b ^ rotl(c, 17)) & 0xFFFFFFFF
        a = self.randomD
        c = (c + a) & 0xFFFFFFFF
        ret = (b + temp) & 0xFFFFFFFF
        a = (a + temp) & 0xFFFFFFFF

        self.randomC = a
        self.randomA = b
        self.randomB = c
        self.randomD = ret

        return ret


    def getPresentFigures(self, sequence: int, replyBuf: bytearray):
        x = 3
        for i in range(len(self.figures)):
            slot = 0x10 if i == 0 else (0x20 if i < 4 else 0x30)
            if self.figures[i].present:
                replyBuf[x] = slot + self.figures[i].orderAdded
                replyBuf[x + 1] = 0x09
                x += 2
        replyBuf[0] = 0xAA
        replyBuf[1] = x - 2
        replyBuf[2] = sequence
        replyBuf[x] = self.generateChecksum(replyBuf, x)


    def getFigureByOrder(self, orderAdded: int) -> InfinityFigure:
        for fig in self.figures:
            if fig.orderAdded == orderAdded:
                return fig
        return self.figures[0]


    def deriveFigurePosition(self, position: int) -> int:
        if position in (0, 1, 2):
            return 1
        elif position in (3, 4, 5):
            return 2
        elif position in (6, 7, 8):
            return 3
        else:
            return 0


    def queryBlock(self, figNum: int, block: int, replyBuf: bytearray, sequence: int):
        with self.infinityMutex:
            figure = self.getFigureByOrder(figNum)

            replyBuf[0] = 0xAA
            replyBuf[1] = 0x12
            replyBuf[2] = sequence
            replyBuf[3] = 0x00

            fileBlock = 1 if block == 0 else block * 4

            if figure.present and fileBlock < 20:
                start = 16 * fileBlock
                replyBuf[4:20] = figure.data[start:start + 16]

            replyBuf[20] = self.generateChecksum(replyBuf, 20)


    def writeBlock(self, figNum: int, block: int, toWriteBuf, replyBuf: bytearray, sequence: int):
        with self.infinityMutex:
            figure = self.getFigureByOrder(figNum)

            replyBuf[0] = 0xAA
            replyBuf[1] = 0x02
            replyBuf[2] = sequence
            replyBuf[3] = 0x00

            fileBlock = 1 if block == 0 else block * 4

            if figure.present and fileBlock < 20:
                start = fileBlock * 16
                figure.data[start:start + 16] = toWriteBuf[:16]
                figure.save()

            replyBuf[4] = self.generateChecksum(replyBuf, 4)


    def getFigureIdentifier(self, figNum: int, sequence: int, replyBuf: bytearray):
        with self.infinityMutex:
            figure = self.getFigureByOrder(figNum)

            replyBuf[0] = 0xAA
            replyBuf[1] = 0x09
            replyBuf[2] = sequence
            replyBuf[3] = 0x00

            if figure.present:
                replyBuf[4:11] = figure.data[:7]

            replyBuf[11] = self.generateChecksum(replyBuf, 11)


    def removeFigure(self, position: int) -> bool:
        with self.infinityMutex:
            figure = self.figures[position]

            if not figure.present:
                return False

            derivedPosition = self.deriveFigurePosition(position)
            if derivedPosition == 0:
                return False

            figure.present = False

            figureChangeResponse = bytearray(32)
            figureChangeResponse[0:6] = [0xAB, 0x04, derivedPosition, 0x09, figure.orderAdded, 0x01]
            figureChangeResponse[6] = self.generateChecksum(figureChangeResponse, 6)

            self.mFigureAddedRemovedResponses.append(figureChangeResponse)

            figure.save()
            if figure.infFile:
                figure.infFile.close()
                figure.infFile = None

            return True


    def loadFigure(self, buf, inFile, position: int) -> int:
        with self.infinityMutex:
            if len(buf) != FIGURE_DATA_SIZE:
                raise ValueError(f"expected {FIGURE_DATA_SIZE} bytes, got {len(buf)}")

            sha1Calc = bytearray(SHA1_CONSTANT[:-1]) + bytearray(buf[:7])
            digest = hashlib.sha1(bytes(sha1Calc)).digest()

            key = bytearray(16)
            for i in range(4):
                for x in range(4):
                    key[x + i * 4] = digest[(3 - x) + i * 4]

            cipher = AES.new(bytes(key), AES.MODE_ECB)
            infinityDecryptedBlock = cipher.decrypt(bytes(buf[16:32]))

            number = (
                (infinityDecryptedBlock[1] << 16)
                | (infinityDecryptedBlock[2] << 8)
                | infinityDecryptedBlock[3]
            )

            figure = self.figures[position]

            figure.infFile = inFile
            figure.data[:FIGURE_DATA_SIZE] = buf[:FIGURE_DATA_SIZE]
            figure.present = True
            if figure.orderAdded == 255:
                figure.orderAdded = self.mFigureOrder
                self.mFigureOrder += 1
            orderAdded = figure.orderAdded

            derivedPosition = self.deriveFigurePosition(position)
            if derivedPosition == 0:
                return 0

            figureChangeResponse = bytearray(32)
            figureChangeResponse[0:6] = [0xAB, 0x04, derivedPosition, 0x09, orderAdded, 0x00]
            figureChangeResponse[6] = self.generateChecksum(figureChangeResponse, 6)
            self.mFigureAddedRemovedResponses.append(figureChangeResponse)

            return number


    def popAddedRemovedResponse(self):
        with self.infinityMutex:
            if not self.mFigureAddedRemovedResponses:
                return None
            return self.mFigureAddedRemovedResponses.popleft()