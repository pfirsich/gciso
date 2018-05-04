import enum
import struct

from .isofilewrapper import IsoInternalFileWrapper

class DolFile(object):
    """
    Represents a DOL executable file.
    You probably don't want to instance this class yourself, but rather call :meth:`IsoFile.getDolFile`.
    See here for some more information about the attributes of this class: http://hitmen.c02.at/files/yagcd/yagcd/chap14.html#sec14.2
    The DOL file is loaded into memory by the Apploader, section by section. This may or may not include permutation
    or fragmentation (the sections stay contiguous, but there may be gaps between the sections after being loaded.)

    Parameters
    ----------
    data : bytes or :class:`IsoInternalFileWrapper`
        The file to be interpreted as a DOL file. See description of this class.

    Attributes
    ----------
    data : bytes
        The DOL file as bytes
    bssMemAddress : int
    bssSize : int
    entryPoint : int
    bodyOffset : int
        Offset to the the data after the header of the DOL
    textSections : list of :class:`Section`
        The text sections of the DOL
    dataSections : list of :class:`Section`
        The data sections of the DOL
    sections : list of :class:`Section`
        Just a joined list of :attr:`DolFile.textSections` and :attr:`DolFile.dataSections`
    sectionsDolOrder : list of :class:`Section`
        :attr:`DolFile.sections` but sorted by DOL offset
    sectionsMemOrder : list of :class:`Section`
        :attr:`DolFile.sections` but sorted by memory address
    """

    class SectionType(enum.Enum):
        """
        The type of section in the DOL file.
        """
        TEXT = "text"
        DATA = "data"

    class Section(object):
        """
        A section in a DOL file. You probably never want to instantiate this class yourself.

        Parameters
        ----------
        index : int
            The index of the section
        sectionType : :class:`DolFile.SectionType`
            The type of the section
        dolOffset : int
        memAddress : int
        size : int

        Attributes
        ----------
        index : int
        type : :class:`DolFile.SectionType`
        dolOffset : int
        endDolOffset : int
        memAddress : int
        endMemAddress : int
        size : int
        """
        def __init__(self, index, sectionType, dolOffset, memAddress, size):
            self.index = index
            self.type = sectionType
            self.dolOffset = dolOffset
            # both "end" offsets/addresses point right after the section
            self.endDolOffset = dolOffset + size
            self.memAddress = memAddress
            self.endMemAddress = memAddress + size
            self.size = size

        def isBefore(self, other):
            return self.memAddress + self.size == other.memAddress \
                and self.dolOffset + self.size == other.dolOffset

        def __repr__(self):
            return "<DolFile.Section {} {} - dolOffset: 0x{:x}, memAddress: 0x{:x}, size: 0x{:x}".format(
                self.type, self.index, self.dolOffset, self.memAddress, self.size)

    @staticmethod
    def _zipSections(sectionType, offsets, memAddresses, sizes):
        assert len(offsets) == len(memAddresses) == len(sizes)
        ret = []
        for i in range(len(offsets)):
            offset, memAddress, size = offsets[i], memAddresses[i], sizes[i]
            if offset == 0 or memAddress == 0 or size == 0:
                break
            ret.append(DolFile.Section(i, sectionType, offset, memAddress, size))
        return ret

    def __init__(self, data):
        if isinstance(data, IsoInternalFileWrapper):
            data.seek(0)
            data = data.read()
        self.data = data

        # header
        textSectionFileOffsets = struct.unpack_from(">6I", data, 0)
        dataSectionFileOffsets = struct.unpack_from(">10I", data, 0x1C)
        textSectionMemAddresses = struct.unpack_from(">6I", data, 0x48)
        dataSectionMemAddresses = struct.unpack_from(">10I", data, 0x64)
        textSectionSizes = struct.unpack_from(">6I", data, 0x90)
        dataSectionSizes = struct.unpack_from(">10I", data, 0xAC)
        self.bssMemAddress = struct.unpack_from(">I", data, 0xD8)[0]
        self.bssSize = struct.unpack_from(">I", data, 0xDC)[0]
        self.entryPoint = struct.unpack_from(">I", data, 0xE0)[0]
        self.bodyOffset = 0x100
        self.textSections = DolFile._zipSections(DolFile.SectionType.TEXT,
            textSectionFileOffsets, textSectionMemAddresses, textSectionSizes)
        self.dataSections = DolFile._zipSections(DolFile.SectionType.DATA,
            dataSectionFileOffsets, dataSectionMemAddresses, dataSectionSizes)
        self.sections = self.textSections + self.dataSections

        self.sectionsDolOrder = list(sorted(self.sections, key=lambda x: x.dolOffset))
        self.sectionsMemOrder = list(sorted(self.sections, key=lambda x: x.memAddress))

    def getSectionByMemAddress(self, memAddress):
        """
        Parameters
        ----------
        memAddress : int
            Memory address

        Returns
        -------
        :class:`Section` or None
            The section the memory address points to or `None` if that address does not point to a DOL section.
        """
        for section in self.sections:
            rel = memAddress - section.memAddress
            if rel >= 0 and rel < section.size:
                return section
        return None

    def getSectionByDolOffset(self, dolOffset):
        """
        Parameters
        ----------
        dolOffset : int
            A offset inside the DOL file

        Returns
        -------
        :class:`Section` or None
            The section `dolOffset` points to or `None` if that offset does not point to a DOL section.
        """
        for section in self.sections:
            rel = dolOffset - section.dolOffset
            if rel >= 0 and rel < section.size:
                return section
        return None

    def memAddressToDolOffset(self, memAddress):
        """
        Parameters
        ----------
        memAddress : int
            Memory address

        Returns
        -------
        int or None
            The offset inside the DOL of the data that is loaded to `memAddress` if it belongs to a DOL section. `None` otherwise.
        """
        section = self.getSectionByMemAddress(memAddress)
        if not section:
            return None
        return section.dolOffset + (memAddress - section.memAddress)

    def dolOffsetToMemAddress(self, dolOffset):
        """
        Parameters
        ----------
        dolOffset : int
            An offset inside the DOL file.

        Returns
        -------
        int or None
            The memory address the data pointed to by dolOffset is loaded to if it belongs to a DOL section. `None` otherwise.
        """
        section = self.getSectionByDolOffset(dolOffset)
        if not section:
            return None
        return section.memAddress + (dolOffset - section.dolOffset)

    def isMappedContiguousMem(self, memAddressStart, memAddressEnd):
        """
        See :meth:`isMappedContiguous`, but starting with memory.
        This essentially just maps the memory addresses to DOL offsets and then calls
        :meth:`isMappedContiguous`.
        """
        return self.isMappedContiguous(self.memAddressToDolOffset(memAddressStart),
            self.memAddressToDolOffset(memAddressEnd))

    # dolOffsetEnd is not included!
    # if isContiguous(0, 4) is true, then the byte at offset 4 might not be
    # contiguous with the rest
    def isMappedContiguous(self, dolOffsetStart, dolOffsetEnd):
        """
        This function determines whether a range of (contiguous) memory in the DOL file is loaded
        contiguously to memory.

        Parameters
        ----------
        dolOffsetStart : int
            The start of the data range inside the DOL
        dolOffsetEnd : int
            The end of the data range (non-inclusive).

        Returns
        -------
        bool

        Notes
        -----
        `dolOffsetEnd` not being inclusive means that if isContiguous(0, 4) is True, then
        the byte at offset 4 not be 4 bytes after the byte at offset 0 in memory. (Only byte 0, 1, 2 and 3 are).
        """
        section = self.getSectionByDolOffset(dolOffsetStart)
        if dolOffsetEnd <= section.endDolOffset:
            return True
        else:
            dolIndex = self.sectionsDolOrder.index(section)
            memIndex = self.sectionsMemOrder.index(section)
            dolNext = self.sectionsDolOrder[dolIndex+1]
            memNext = self.sectionsDolOrder[memIndex+1]

            if dolNext == memNext and section.isBefore(dolNext):
                return self.isMappedContiguous(dolNext.dolOffset, dolOffsetEnd)
            else:
                return False
