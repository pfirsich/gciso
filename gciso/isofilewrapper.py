class IsoInternalFileWrapper(object):
    """
    Wraps a file inside the .iso.
    You probably don't want to call this yourself. See :meth:`IsoFile.open`.

    Parameters
    ----------
    isoFile : :class:`IsoFile`
    offset : int
        Offset of the file inside the .iso file.
    size : int
        Size of the file

    Notes
    -----
    This class may also be used as a context manager, similar to `open` from the standard library.::

        with isoFile.open(b'PlSs.dat') as f:
            f.seek(0x1000)
            data = f.read(0x30)
    """
    def __init__(self, isoFile, offset, size):
        self.cursor = 0
        self.file = isoFile
        self.offset = offset
        self.size = size

    # 0 = start, 1 = current, 2 = end
    def seek(self, offset, whence=0):
        """
        Moves the current position inside the file according to the given offset.

        Parameters
        ----------
        offset : int
            The offset
        whence : int
            One of either 0, 1 or 2. See notes.

        Returns
        -------
        int
            The current position after seeking.

        Raises
        ------
        ValueError
            If whence is not in `{0, 1, 2}`

        Notes
        -----

        If `whence` is 0, the offset will be interpreted relative to **the start of the file**.

        If `whence` is 1, the offset will be interpreted relative to **the current position**.

        If `whence` is 2, the offset will be interpreted relative to **the end of the file**. Usually in this case `offset` is negative.

        You may also seek before or after the end of the file, though write and read operations will most likely fail.
        """
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
        """
        Returns
        -------
        int
            The current position inside the file
        """
        return self.cursor

    def read(self, size=-1):
        """
        Reads data starting from the current position.

        Parameters
        ----------
        size : int
            How many bytes to read. If `None`, negative or ommited, read until end of file

        Returns
        -------
        bytes
            The data read from the file

        Notes
        -----
        See :meth:`IsoFile.readFile` for exceptions this function might raise.
        """
        data = self.file._readFile(self.offset, self.size, self.cursor, size)
        self.cursor += len(data)
        return data

    def write(data):
        """
        Writes data to the current position.

        Parameters
        ----------
        data : bytes

        Returns
        -------
        int
            The number of bytes written

        Notes
        -----
        See :meth:`IsoFile.writeFile` for exceptions this function might raise.
        """
        # store ret first, so that the cursor is not move, if _writeFile raises an exception
        ret = self.file._writeFile(self.offset, self.size, self.cursor, data)
        self.cursor += len(data)
        return ret

    def close(self):
        """
        Internally this is a NOP, but it exists to provide more compatibility with Python's own file objects.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass
