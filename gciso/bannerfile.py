import struct

from .isofilewrapper import IsoInternalFileWrapper

def _zeroTermination(b, offset=0, maxLen=None):
    i = offset
    while b[i] != 0 and (maxLen == None or i - offset < maxLen):
        i += 1
    return b[offset:i]

class BannerFile(object):
    """
    Represents a .bnr file. Mostly there is just one `opening.bnr` in an .iso. In PAL .isos there are multiple.
    You probably don't want to instance this class yourself, but rather call :meth:`IsoFile.getBannerFile`.

    Parameters
    ----------
    data : bytes or :class:`IsoInternalFileWrapper`
        The file to interpret as a banner file. See the description of this class.

    Attributes
    ----------
    magicBytes : bytes
    pixelData: bytes
        The pixel data of the image in RGB5A1 format.
    meta : :class:`MetaData` or list of :class:`MetaData`
        For PAL isos meta may be a list with multiple :class:`MetaData` objects

    """

    _META_DATA_SIZE = 0x140

    class MetaData(object):
        """
        Contains metadata of a banner.
        See here for more information about the fields: http://hitmen.c02.at/files/yagcd/yagcd/chap14.html#sec14.1

        Attributes
        ----------
        gameName : bytes
        developerName : bytes
        fullGameTitle : bytes
        fullDeveloperName : bytes
        gameDescription : bytes
        """
        def __init__(self, data, offset=0):
            self.gameName = _zeroTermination(data, offset+0x0, 0x20)
            self.developerName = _zeroTermination(data, offset+0x20, 0x20)
            self.fullGameTitle = _zeroTermination(data, offset+0x40, 0x40)
            self.fullDeveloperName = _zeroTermination(data, offset+0x80, 0x40)
            self.gameDescription = _zeroTermination(data, offset+0xc0, 0x80)

        def __str__(self):
            return "<BannerFile.MetaData gameName: {}, developerName: {}, fullGameTitle: {}, fullDeveloperName: {}, gameDescription: {}>".format(
                self.gameName, self.developerName, self.fullGameTitle, self.fullDeveloperName, self.gameDescription)

    def __init__(self, data): # data = bytes or InternalFile
        if isinstance(data, IsoInternalFileWrapper):
            data.seek(0)
            data = data.read()
        self.data = data

        self.magicBytes = data[0:4]
        self.pixelData = data[0x20:0x1820]

        metaDataOffset = 0x1820
        metaDataCount = (len(data) - metaDataOffset) // BannerFile._META_DATA_SIZE
        if metaDataCount == 1:
            self.meta = BannerFile.MetaData(data, metaDataOffset)
        else:
            self.meta = []
            for i in range(metaDataCount):
                offset = metaDataOffset + BannerFile._META_DATA_SIZE * i
                self.meta.append(BannerFile.MetaData(data, offset))

    def getPILImage(self):
        """
        `PIL` will be imported lazily by this function. So PIL or Pillow is only a requirement if
        you use this function.

        Returns
        -------
        :class:`PIL.Image`
        """
        from PIL import Image

        # 96x32 px, 4x4 tiles => 24*8 tiles
        BANNER_W = 96
        BANNER_H = 32
        TILE_SIZE = 4
        C_MAX = (1 << 5) - 1
        BANNER_W_TILES = BANNER_W // TILE_SIZE
        TILE_PIXELS = TILE_SIZE * TILE_SIZE

        # I am very sure this can be done more efficiently.
        buf = bytearray(BANNER_W*BANNER_H*3)
        for i in range(0, len(self.pixelData), 2):
            v = struct.unpack_from(">H", self.pixelData, i)[0]
            a = ((v & 0b1000000000000000) >> 15)
            r = ((v & 0b0111110000000000) >> 10) * 255 // C_MAX
            g = ((v & 0b0000001111100000) >> 5) * 255 // C_MAX
            b = ((v & 0b0000000000011111)) * 255 // C_MAX

            pixel = (i // 2) # 2 = bytes per pixel
            tile = pixel // TILE_PIXELS
            tilePixel = pixel - tile * TILE_PIXELS

            tileY = tile // BANNER_W_TILES
            tileX = tile - tileY * BANNER_W_TILES

            tilePixelY = tilePixel // TILE_SIZE
            tilePixelX = tilePixel - tilePixelY * TILE_SIZE

            imgY = tileY * TILE_SIZE + tilePixelY
            imgX = tileX * TILE_SIZE + tilePixelX

            pixelOffset = imgX*3 + imgY*BANNER_W*3
            # I did not read this anywhere, but I have to multiply with a
            # to get images that look like in Dolphin/GC Rebuilder
            buf[pixelOffset + 0] = r * a
            buf[pixelOffset + 1] = g * a
            buf[pixelOffset + 2] = b * a

        return Image.frombytes("RGB", (BANNER_W, BANNER_H), bytes(buf))
