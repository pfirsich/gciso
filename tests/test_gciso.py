import unittest

import filecmp
import os

from PIL import Image

import gciso

# A Super Smash Bros. Melee NTSC 1.02 ISO!
# md5: 0e63d4223b01d9aba596259dc155a174
ISO_PATH = os.environ["GCISO_TEST_ISO_PATH"]
print("Using ISO '{}' for testing.".format(ISO_PATH))

class IsoFileTestCase(unittest.TestCase):
    def setUp(self):
        self.isoFile = gciso.IsoFile(ISO_PATH)

    def tearDown(self):
        self.isoFile.close()

    def test_header(self):
        self.assertEqual(self.isoFile.gameCode, b"GALE")
        self.assertEqual(self.isoFile.makerCode, b"01")
        self.assertEqual(self.isoFile.diskId, 0)
        self.assertEqual(self.isoFile.version, 2)
        self.assertEqual(self.isoFile.gameName, b"Super Smash Bros Melee")
        self.assertEqual(self.isoFile.dolOffset, 0x1e800)
        self.assertEqual(self.isoFile.fstOffset, 0x456e00)
        self.assertEqual(self.isoFile.fstSize, 0x7529)
        self.assertEqual(self.isoFile.maxFstSize, 0x7529)

        self.assertEqual(self.isoFile.apploaderDate, b"2001/11/14")
        self.assertEqual(self.isoFile.apploaderEntryPoint, 0x81200268)
        self.assertEqual(self.isoFile.apploaderCodeSize, 0x14f4)
        self.assertEqual(self.isoFile.apploaderTrailerSize, 0x1ade0)

    def test_files(self):
        self.assertEqual(self.isoFile.numFstEntries, 1212)
        firstFiles = [b'audio/1padv.ssm', b'audio/1pend.ssm', b'audio/1p_qk.hps', b'audio/akaneia.hps', b'audio/baloon.hps']
        lastFiles = [b'Vi0801.dat', b'Vi1101.dat', b'Vi1201v1.dat', b'Vi1201v2.dat', b'Vi1202.dat']
        self.assertEqual(list(self.isoFile.files.keys())[5:10], firstFiles)
        self.assertEqual(list(self.isoFile.files.keys())[-5:], lastFiles)

        audioUsFiles = [b'1padv.ssm', b'1pend.ssm', b'bigblue.ssm', b'captain.ssm', b'castle.ssm', b'clink.ssm']
        self.assertEqual(list(self.isoFile.listDir(b"audio/us"))[0:6], audioUsFiles)

        files = [b'audio/mrider.hps', b'PlGnGr.dat', b'TyMnView.usd']
        for file in files:
            self.assertTrue(self.isoFile.isFile(file))

        self.assertTrue(self.isoFile.isDir(b"audio"))
        self.assertTrue(self.isoFile.isDir(b"audio/us"))

        self.assertEqual(self.isoFile.fileOffset(b'TyPokeD.dat'), 0x3acf0000)
        self.assertEqual(self.isoFile.fileSize(b'TyPokeD.dat'), 0x327e2)

        # I don't test write here.
        # Theoretically I could test the exceptions for example, but in case
        # the test fails and the exceptions are not thrown, the iso is messed up

        filePart = b'erMove_figatree\x00PlySamus5K_Share_ACTION_ItemParasolOpen_figatree\x00\x00'
        self.assertEqual(self.isoFile.readFile(b'PlSs.dat', 0x1000, 0x42), filePart)
        with self.assertRaises(TypeError):
            self.isoFile.readFile('PlSs.dat', 0, 0)
        with self.assertRaises(IndexError):
            self.isoFile.readFile(b'PlSs.dat', 0x300000, 0)
        with self.assertRaises(IndexError):
            self.isoFile.readFile(b'PlSs.dat', -100, 0)
        with self.assertRaises(ValueError):
            self.isoFile.readFile(b'PlSs.dat', 0, 0x300000)

        with self.isoFile.open(b'PlSs.dat') as f:
            fileSize = 0x4def3
            self.assertEqual(f.seek(0x1000), 0x1000)
            self.assertEqual(f.read(0x30), filePart[:0x30])
            self.assertEqual(f.tell(), 0x1030)
            self.assertEqual(f.seek(0x10, 1), 0x1040)
            self.assertEqual(f.read(0x2), filePart[-2:])
            self.assertEqual(f.seek(-0x20, 2), fileSize - 0x20)
            self.assertEqual(f.read(), b'opN_shapeanim_joint\x00ftDataSamus\x00')

            with self.assertRaises(ValueError):
                f.seek(0x20, 4)

            self.assertEqual(f.seek(0x20, 1), fileSize + 0x20)
            with self.assertRaises(IndexError): # read out of bounds of file
                f.read(0x20)
            # check the erroring read did not change the cursor
            self.assertEqual(f.tell(), fileSize + 0x20)


    def test_banner(self):
        banner = self.isoFile.getBannerFile(b"opening.bnr")
        self.assertEqual(banner.magicBytes, b"BNR1")
        self.assertEqual(banner.meta.gameName, b"SUPER SMASH BROS.")
        self.assertEqual(banner.meta.developerName, b"Melee")
        self.assertEqual(banner.meta.fullGameTitle, b"SUPER SMASH BROS. Melee")
        self.assertEqual(banner.meta.fullDeveloperName, b"Nintendo/HAL Laboratory,Inc.")
        self.assertEqual(banner.meta.gameDescription, b"Nintendo's all-stars are ready to do \nbattle! Let the melee begin!")
        # TODO: Test multiple MetaData for PAL isos

        banner.getPILImage().save("banner_test.png")
        self.assertTrue(filecmp.cmp("banner_test.png", "banner_ref.png", shallow=False))

    def test_dolFile(self):
        dolFile = self.isoFile.getDolFile()

        self.assertEqual(dolFile.bssMemAddress, 0x804316c0)
        self.assertEqual(dolFile.bssSize, 0xa6309)
        self.assertEqual(dolFile.entryPoint, 0x8000522c)

        text = gciso.DolFile.SectionType.TEXT
        data = gciso.DolFile.SectionType.DATA
        sectionsCheck = [
            (text, 0, 0x100, 0x80003100, 0x2420),
            (text, 1, 0x2520, 0x80005940, 0x3b1900),
            (data, 0, 0x3b3e20, 0x80005520, 0x1a0),
            (data, 1, 0x3b3fc0, 0x800056c0, 0x280),
            (data, 2, 0x3b4240, 0x803b7240, 0x20),
            (data, 3, 0x3b4260, 0x803b7260, 0x20),
            (data, 4, 0x3b4280, 0x803b7280, 0x25c0),
            (data, 5, 0x3b6840, 0x803b9840, 0x77e80),
            (data, 6, 0x42e6c0, 0x804d36a0, 0x2d00),
            (data, 7, 0x4313c0, 0x804d79e0, 0x7220),
        ]
        for i, section in enumerate(dolFile.sections):
            self.assertEqual(section.type, sectionsCheck[i][0])
            self.assertEqual(section.index, sectionsCheck[i][1])
            self.assertEqual(section.dolOffset, sectionsCheck[i][2])
            self.assertEqual(section.memAddress, sectionsCheck[i][3])
            self.assertEqual(section.size, sectionsCheck[i][4])

        sectionsDolOrder = [(text, 0), (text, 1), (data, 0), (data, 1),
            (data, 2), (data, 3), (data, 4), (data, 5), (data, 6), (data, 7)]
        for i, section in enumerate(dolFile.sectionsDolOrder):
            self.assertEqual(section.type, sectionsDolOrder[i][0])
            self.assertEqual(section.index, sectionsDolOrder[i][1])

        sectionsMemOrder = [(text, 0), (data, 0), (data, 1), (text, 1),
            (data, 2), (data, 3), (data, 4), (data, 5), (data, 6), (data, 7)]
        for i, section in enumerate(dolFile.sectionsMemOrder):
            self.assertEqual(section.type, sectionsMemOrder[i][0])
            self.assertEqual(section.index, sectionsMemOrder[i][1])

        # -> An own test?
        self.assertEqual(dolFile.getSectionByMemAddress(0x800056c0 + 0x69), dolFile.sections[3])
        self.assertEqual(dolFile.getSectionByMemAddress(0x800056c0 + 0x280), dolFile.sections[1])
        self.assertEqual(dolFile.getSectionByMemAddress(0x804d79e0), dolFile.sections[-1])
        self.assertEqual(dolFile.getSectionByMemAddress(0x804d79e0 + 0x42), dolFile.sections[-1])

        self.assertIsNone(dolFile.getSectionByMemAddress(0x80000000)) # before dol
        self.assertIsNone(dolFile.getSectionByMemAddress(0x804316c5)) # between data 5 and 6

        self.assertEqual(dolFile.getSectionByDolOffset(0x3b4280), dolFile.sections[6])
        self.assertEqual(dolFile.getSectionByDolOffset(0x3b4280 + 0x1000), dolFile.sections[6])
        self.assertEqual(dolFile.getSectionByDolOffset(0x3b4280 + 0x25c0), dolFile.sections[7])

        self.assertIsNone(dolFile.getSectionByDolOffset(0x4385E5))
        self.assertIsNone(dolFile.getSectionByDolOffset(0x0))

        self.assertEqual(dolFile.memAddressToDolOffset(0x80003100), 0x100)
        self.assertEqual(dolFile.memAddressToDolOffset(0x80005940 + 0x20), 0x2520 + 0x20)
        self.assertIsNone(dolFile.memAddressToDolOffset(0x804316c5))

        self.assertEqual(dolFile.dolOffsetToMemAddress(0x100), 0x80003100)
        self.assertEqual(dolFile.dolOffsetToMemAddress(0x2520 + 0x20), 0x80005940 + 0x20)
        self.assertIsNone(dolFile.dolOffsetToMemAddress(0x0))

        self.assertTrue(dolFile.isMappedContiguous(0x3b4240 + 0x10, 0x3b6840 + 0x1337))
        self.assertFalse(dolFile.isMappedContiguous(0x3b4240 + 0x10, 0x3b6840 + 0x430000))
        self.assertTrue(dolFile.isMappedContiguous(0x150, 0x2000))
        self.assertTrue(dolFile.isMappedContiguous(0x150, 0x2520))
        self.assertFalse(dolFile.isMappedContiguous(0x150, 0x2600))

        # same as above, but with mem addresses
        self.assertTrue(dolFile.isMappedContiguousMem(0x803b7240 + 0x10, 0x803b9840 + 0x1337))
        self.assertTrue(dolFile.isMappedContiguousMem(0x80003150, 0x80005000))
        self.assertFalse(dolFile.isMappedContiguousMem(0x80003150, 0x80005600))

if __name__ == "__main__":
    unittest.main()
