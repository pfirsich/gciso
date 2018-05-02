import struct

from .isofilewrapper import IsoInternalFileWrapper

class DolFile(object):
    class Section(object):
        def __init__(self, index, sectionType, offset, memAddress, size):
            self.index = index
            self.type = sectionType
            self.dolOffset = offset
            # both "end" offsets/addresses point right after the section
            self.endDolOffset = offset + size
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
    def zipSections(sectionType, offsets, memAddresses, sizes):
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
        self.textSections = DolFile.zipSections("text", textSectionFileOffsets,
            textSectionMemAddresses, textSectionSizes)
        self.dataSections = DolFile.zipSections("data", dataSectionFileOffsets,
            dataSectionMemAddresses, dataSectionSizes)
        self.sections = self.textSections + self.dataSections

        self.sectionsDolOrder = list(sorted(self.sections, key=lambda x: x.dolOffset))
        self.sectionsMemOrder = list(sorted(self.sections, key=lambda x: x.memAddress))

    def getSectionByMemAddress(self, memAddress):
        for section in self.sections:
            rel = memAddress - section.memAddress
            if rel >= 0 and rel < section.size:
                return section
        return None

    def getSectionByDolOffset(self, offset):
        for section in self.sections:
            rel = offset - section.dolOffset
            if rel >= 0 and rel < section.size:
                return section
        return None

    def memAddressToDolOffset(self, memAddress):
        section = self.getSectionByMemAddress(memAddress)
        if not section:
            return None
        return section.dolOffset + (memAddress - section.memAddress)

    def dolOffsetToMemAddress(self, dolOffset):
        section = self.getSectionByDolOffset(dolOffset)
        if not section:
            return None
        return section.memAddress + (dolOffset - section.dolOffset)

    def isMappedContiguousMem(self, memAddressStart, memAddressEnd):
        return self.isMappedContiguous(self.memAddressToDolOffset(memAddressStart),
            self.memAddressToDolOffset(memAddressEnd))

    # dolOffsetEnd is not included!
    # if isContiguous(0, 4) is true, then the byte at offset 4 might not be
    # contiguous with the rest
    def isMappedContiguous(self, dolOffsetStart, dolOffsetEnd):
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
