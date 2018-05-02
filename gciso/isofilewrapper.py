class IsoInternalFileWrapper(object):
    def __init__(self, isoFile, offset, size):
        self.cursor = 0
        self.file = isoFile
        self.offset = offset
        self.size = size

    # 0 = start, 1 = current, 2 = end
    def seek(self, offset, whence=0):
        if whence == 0:
            self.cursor = offset
        elif whence == 1:
            self.cursor += offset
        elif whence == 2:
            self.cursor = self.size + offset
        else:
            raise ValueError("Whence must be in {0, 1, 2}")
        return self.cursor

    def tell(self):
        return self.cursor

    def read(self, size=-1):
        data = self.file._readFile(self.offset, self.size, self.cursor, size)
        self.cursor += len(data)
        return data

    def write(data):
        # store ret first, so that the cursor is not move, if _writeFile raises an exception
        ret = self.file._writeFile(self.offset, self.size, self.cursor, data)
        self.cursor += len(data)
        return ret

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass
