# gciso
**gciso** is a library for reading and writing *.iso* files for the Nintendo GameCube.

## Installation
Clone/Download the repository and call `pip install <dir>` on the directory containing `setup.py`.

## Documentation
If you use Python and want to modify GameCube ISOs, you probably already know enough to just look at the code and you will hopefully quickly find what you are looking for.

## Tests
To run the tests, you need a Super Smash Bros. Melee Iso (NTSC, v1.02) (md5: `0e63d4223b01d9aba596259dc155a174`).
Set the path to the iso to an environment variable named `GCISO_TEST_ISO_PATH` and you also need to download a reference export of the `opening.bnr` banner image, which you can find [here](http://download.theshoemaker.de/gciso_test/banner_ref.png) (put it into the `tests` directory).
