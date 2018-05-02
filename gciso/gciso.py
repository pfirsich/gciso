import struct
from collections import OrderedDict as odict

from .isofilewrapper import IsoInternalFileWrapper
from .bannerfile import BannerFile
from .dolfile import DolFile

class IsoFile(object):
    FST_ENTRY_LENGTH = 0xC

    def __init__(self, isoPath):
        self.file = open(isoPath, "r+b")
        self.files = odict()
        self.readDiskHeader()
        self.readFst()

    # http://hitmen.c02.at/files/yagcd/yagcd/chap13.html#sec13
    def readDiskHeader(self):
        self.file.seek(0)
        values = struct.unpack(">4s2sBB", self.file.read(8))
        self.gameCode = values[0]
        self.makerCode = values[1]
        self.diskId = values[2]
        self.version = values[3]
        self.gameName = self.readString(0x20)

        self.file.seek(0x420)
        values = struct.unpack(">IIII", self.file.read(16))
        self.dolOffset = values[0]
        self.fstOffset = values[1]
        self.fstSize = values[2]
        self.maxFstSize = values[3] # relevant for multiple disks
        self.dolSize = self.fstOffset - self.dolOffset

        self.files[b"boot.bin"] = (0x0, 0x440)
        self.files[b"bi2.bin"] = (0x440, 0x2000)
        self.files[b"fst.bin"] = (self.fstOffset, self.fstSize)
        self.files[b"start.dol"] = (self.dolOffset, self.dolSize)

        self.appLoaderOffset = 0x2440
        # I am unsure about this whole part
        self.file.seek(self.appLoaderOffset)
        values = struct.unpack(">10s6xIII", self.file.read(28))
        self.apploaderDate = values[0]
        self.apploaderEntryPoint = values[1]
        self.apploaderCodeSize = values[2]
        self.apploaderTrailerSize = values[3]
        self.appLoaderCodeOffset = self.appLoaderOffset + 0x20

        self.files[b"appldr.bin"] = (self.appLoaderCodeOffset, self.apploaderCodeSize)


    def readFst(self):
        self.file.seek(self.fstOffset + 0x8)
        # length of root entry
        self.numFstEntries = struct.unpack(">I", self.file.read(4))[0]
        self.stringTableOffset = self.fstOffset + (self.numFstEntries * IsoFile.FST_ENTRY_LENGTH);

        self.readDirectory(b"", 0)

    # https://github.com/CraftedCart/GCISOManager cleared a lot of things up
    def readDirectory(self, path, index):
        self.file.seek(self.fstOffset + IsoFile.FST_ENTRY_LENGTH * index)
        isDir = self.file.read(1)[0]
        fileNameOffset = struct.unpack(">I", b"\0" + self.file.read(3))[0]
        offset = struct.unpack(">I", self.file.read(4))[0]
        length = struct.unpack(">I", self.file.read(4))[0]
        name = b"" if index == 0 else self.readString(self.stringTableOffset + fileNameOffset)

        if isDir:
            i = index + 1
            while i < length:
                i += self.readDirectory(path + name + b"/", i)
            return length
        else:
            filePath = path + name
            if filePath[0] == b"/"[0]: filePath = filePath[1:]
            self.files[filePath] = (offset, length)
            return 1

    def readString(self, offset):
        self.file.seek(offset)
        s = b""
        while True:
            byte = self.file.read(1)
            if byte == b"\0":
                break
            else:
                s += byte
        return s

    def close(self):
        self.file.close()

    @staticmethod
    def _checkPath(path):
        if not isinstance(path, bytes):
            raise TypeError("Path must be bytes!")

    def _writeFile(self, fileOffset, fileSize, offset, data):
        if offset < 0:
            raise IndexError("Offset must be > 0!")
        if offset >= fileSize:
            raise IndexError("Offset is out of file bounds!")
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes!")
        if offset + len(data) > fileSize:
            raise ValueError("Cannot change file size!")
        self.file.seek(fileOffset + offset)
        return self.file.write(data)

    def writeFile(self, path, offset, data):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        return self._writeFile(fileOffset, fileSize, offset, data)

    def _readFile(self, fileOffset, fileSize, offset=0, count=-1):
        if offset < 0:
            raise IndexError("Offset must be > 0!")
        if offset >= fileSize:
            raise IndexError("Offset is out of file bounds!")
        if count == None or count < 0:
            count = fileSize - offset
        if offset + count > fileSize:
            raise ValueError("Cannot read beyond end of file!")
        self.file.seek(fileOffset + offset)
        return self.file.read(count)

    def readFile(self, path, offset, count=-1):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        return self._readFile(fileOffset, fileSize, offset, count)

    @staticmethod
    def fileInDir(filePath, dirPath):
        IsoFile._checkPath(filePath)
        IsoFile._checkPath(dirPath)
        if dirPath[-1] != b"/"[0]: dirPath += b"/"
        if dirPath == "/": return True
        return filePath.startswith(dirPath)

    def listDir(self, path):
        IsoFile._checkPath(path)
        if path[-1] != b"/"[0]: path += b"/"
        for file in self.files:
            if IsoFile.fileInDir(file, path):
                yield file[len(path):]

    def isFile(self, path):
        IsoFile._checkPath(path)
        return path in self.files

    def isDir(self, path):
        IsoFile._checkPath(path)
        return any(IsoFile.fileInDir(file, path) for file in self.files.keys())

    def open(self, path):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        return IsoInternalFileWrapper(self, fileOffset, fileSize)

    def fileOffset(self, path):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        return fileOffset

    def fileSize(self, path):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        return fileSize

    def getBannerFile(self, path):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        self.file.seek(fileOffset)
        return BannerFile(self.file.read(fileSize))

    def getDolFile(self, path=b"start.dol"):
        IsoFile._checkPath(path)
        fileOffset, fileSize = self.files[path]
        self.file.seek(fileOffset)
        return DolFile(self.file.read(fileSize))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.file.close()
