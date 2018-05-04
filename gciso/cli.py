import argparse
import enum
import sys

import gciso

def _h(n):
    return "0x{:x}".format(n)

# gciso write isofile internalfile srcfile [--offset X] [--banner]
def write(isoFile, internalFile, srcFile, offset=0, banner=False):
    if banner:
        raise NotImplementedError("Writing banners is not implemented yet!")
    with gciso.IsoFile(isoFile) as iso, open(srcFile, "rb") as src:
        iso.writeFile(internalFile, offset, srcFile.read())

# gciso read isofile internalfile dstfile [--offset X] [--length X] [--banner]
def read(isoFile, internalFile, dstFile, offset=0, length=None, banner=False):
    with gciso.IsoFile(isoFile) as iso:
        if banner:
            banner = iso.getBannerFile(internalFile)
            banner.getPILImage().save(dstFile)
        else:
            with open(dstFile, "wb") as dst:
                dst.write(iso.readFile(internalFile, offset, length))

# gciso isoinfo isofile
def isoInfo(isoFile):
    with gciso.IsoFile(isoFile) as iso:
        print("Game Code:", iso.gameCode)
        print("Maker Code:", iso.makerCode)
        print("Disk Id:", iso.diskId)
        print("Version:", iso.version)
        print("Game Name:", iso.gameName)
        print()
        print("DOL offset:", _h(iso.dolOffset))
        print("DOL size:", _h(iso.dolSize))
        print("FST offset:", _h(iso.fstOffset))
        print("FST Size:", _h(iso.fstSize))
        print("Max FST Size:", _h(iso.maxFstSize))
        print("FST Entries:", _h(iso.numFstEntries))
        print()
        print("Apploader Date:", iso.apploaderDate)
        print("Apploader Entry Point:", _h(iso.apploaderEntryPoint))
        print("Apploader Code Size:", _h(iso.apploaderCodeSize))
        print("Apploader Trailer Size:", _h(iso.apploaderTrailerSize))

def ls(isoFile, directory=b"/", columns=None, size=False):
    with gciso.IsoFile(isoFile) as iso:
        files = list(iso.listDir(directory))

        if directory[-1] != b"/":
            directory += b"/"

        maxNameLen = 0
        for file in files:
            nameLen = len(file)
            if size:
                nameLen += len(" ({})".format(iso.fileSize(directory + file)))
            maxNameLen = max(maxNameLen, nameLen)
        colWidth = maxNameLen + 5 # 3 spaces and b''

        if columns == None:
            columns = int(100 / colWidth) # assume 100 characters width

        colFmt = "{{!s:<{}}}".format(colWidth)
        for i in range(0, len(files), columns):
            printCols = min(columns, len(files) - i)
            fmt = colFmt * printCols
            params = files[i:i+printCols]
            if size:
                params = map(lambda x: "{!s} ({})".format(x, iso.fileSize(directory + x)), params)
            print(fmt.format(*params))

# gciso bannerinfo isofile/bannerfile [name]
def bannerInfo(file, fileName=b"opening.bnr"):
    if file.endswith(".iso"):
        with gciso.IsoFile(file) as iso:
            banner = iso.getBannerFile(fileName)
    elif file.endswith(".bnr"):
        with open(file, "rb") as bannerFile:
            banner = gciso.BannerFile(bannerFile.read())
    else:
        quit("File extension must be .bnr or .iso!")

    print("Magic Bytes:", banner.magicBytes)
    metas = banner.meta
    if isinstance(metas, gciso.BannerFile.MetaData):
        metas = [metas]
    for i, meta in enumerate(metas):
        print("\nMetadata {}:".format(i))
        print("Game Name:", meta.gameName)
        print("Developer Name:", meta.developerName)
        print("Full Game Title:", meta.fullGameTitle)
        print("Full Developer Name:", meta.fullDeveloperName)
        print("Game Description:", meta.gameDescription)

# gciso dolinfo isofile/dolfile [name] [--dolorder] [--memorder]
class SectionOrder(enum.Enum):
    FILE = "file"
    DOL_OFFSET = "dol"
    MEM_ADDRESS = "mem"

def dolInfo(file, fileName=b"start.dol", order=None):
    if file.endswith(".iso"):
        with gciso.IsoFile(file) as iso:
            dol = iso.getDolFile(fileName)
    elif file.endswith(".dol"):
        with open(file, "rb") as dolFile:
            dol = gciso.DolFile(dolFile.read())
    else:
        quit("File extension must be .bnr or .iso!")

    print("BSS Memory Address: 0x{:x}".format(dol.bssMemAddress))
    print("BSS Size: 0x{:x}".format(dol.bssSize))
    print("Entry Point: 0x{:x}".format(dol.entryPoint))

    if order == None: order = SectionOrder.FILE
    assert isinstance(order, SectionOrder)
    if order == SectionOrder.FILE:
        sections = dol.sections
    elif order == SectionOrder.DOL_OFFSET:
        sections = dol.sectionsDolOrder
    elif order == SectionOrder.MEM_ADDRESS:
        sections = dol.sectionsMemOrder

    print("\nSections:")
    for i, section in enumerate(sections):
        print("{} {} - DOL: {:>8} to {:>8}, Memory: 0x{:x} to 0x{:x} (size: 0x{:x})".format(
            section.type.value, section.index, _h(section.dolOffset),
            _h(section.endDolOffset), section.memAddress, section.endMemAddress, section.size))
        if i + 1 < len(sections):
            if order == SectionOrder.DOL_OFFSET:
                gap = sections[i+1].dolOffset - section.endDolOffset
                if gap > 0:
                    print("Gap (DOL): 0x{:x}".format(gap))
            if order == SectionOrder.MEM_ADDRESS:
                gap = sections[i+1].memAddress - section.endMemAddress
                if gap > 0:
                    print("Gap (memory): 0x{:x}".format(gap))


def _int(x):
    return int(x, 0)

def _bytes(s):
    return s.encode("ascii")

def main(_args=None):
    parser = argparse.ArgumentParser(prog="gciso.cli", description="")
    subparsers = parser.add_subparsers(dest="command", help="")
    subparsers.required = True

    writeParser = subparsers.add_parser("write")
    writeParser.add_argument("isofile", help="The .iso file.")
    writeParser.add_argument("internalfile", type=_bytes, help="The path to the file inside the .iso to be written to.")
    writeParser.add_argument("srcfile", help="The file with the data to be written.")
    writeParser.add_argument("--offset", type=_int, default=0, help="An offset in the internalfile to write to. Default is 0.")
    writeParser.add_argument("--banner", default=False, action="store_true", help="This will read out an image write an image file to the banner. Ignores offset.")

    readParser = subparsers.add_parser("read")
    readParser.add_argument("isofile", help="The .iso file.")
    readParser.add_argument("internalfile", type=_bytes, help="The path to the file inside the .iso to be read from.")
    readParser.add_argument("dstfile", help="The file to write the read data to.")
    readParser.add_argument("--offset", type=_int, default=0, help="An offset in the internalfile to start reading from. Default is 0.")
    readParser.add_argument("--length", type=_int, help="The number of bytes to read from the offset. Default is until end of file.")
    readParser.add_argument("--banner", default=False, action="store_true", help="This will read out an image file from a banner file. Ignores offset and length.")

    isoInfoParser = subparsers.add_parser("isoinfo")
    isoInfoParser.add_argument("isofile", help="The .iso file to output information about.")

    lsParser = subparsers.add_parser("ls")
    lsParser.add_argument("isofile", help="The .iso file to list internal files of.")
    lsParser.add_argument("dir", nargs="?", type=_bytes, default=b"/", help="The internal directory to list.")
    lsParser.add_argument("--cols", default=None, type=int, help="The number of columns to list the files in.")
    lsParser.add_argument("--size", default=False, action="store_true", help="Additionally display the file size.")

    bannerInfoParser = subparsers.add_parser("bannerinfo")
    bannerInfoParser.add_argument("file", help="The .iso file containing the banner or a banner file.")
    bannerInfoParser.add_argument("internalfile", type=_bytes, default=b"opening.bnr", nargs="?", help="The internal file name of the banner file to output info about. Only relevant if <file> is an .iso. Default is 'opening.bnr'.")

    dolInfoParser = subparsers.add_parser("dolinfo")
    dolInfoParser.add_argument("file", help="The .iso file containing the .dol or a .dol file itself.")
    dolInfoParser.add_argument("internalfile", type=_bytes, nargs="?", default=b"start.dol", help="The internal file name of the DOL file to output info about. Only relevant if <file> is an .iso. Default is 'start.dol'.")
    dolInfoParser.add_argument("--order", default="file", choices=["mem", "dol"], help="The order to output the DOL sections in. Default is the order they appear in the DOL header. 'dol' sorts them by DOL offset, 'mem' sorts them by memory address.")

    if _args == None:
        _args = sys.argv[1:]
    args = parser.parse_args(_args)

    if args.command == "write":
        write(args.isofile, args.internalfile, args.srcfile, args.offset, args.banner)
    elif args.command == "read":
        read(args.isofile, args.internalfile, args.dstfile, args.offset, args.length, args.banner)
    elif args.command == "isoinfo":
        isoInfo(args.isofile)
    elif args.command == "ls":
        ls(args.isofile, args.dir, args.cols, args.size)
    elif args.command == "bannerinfo":
        bannerInfo(args.file, args.internalfile)
    elif args.command == "dolinfo":
        dolInfo(args.file, args.internalfile, SectionOrder(args.order))

if __name__ == "__main__":
    main()
