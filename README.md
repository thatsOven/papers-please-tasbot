# "Papers, Please" TASbot
A "Papers, Please" TASbot that offers a programmable interface with the game.

Huge thanks to HowToCantaloupe for helping throughout the development process, giving ideas, as well as offering information about the how the game is actually built, and, in general, providing a lot of knowledge about the game!

# Usage
Requires Python 3.11+ and the dependencies listed in `requirements.txt`. Run `main.py` to start the bot.

Run `build.py` to build an optimized version of the text recognition system, written in Cython. 

To build releases, pass the `--release` argument to `build.py`.

Note that using `build.py` requires the dependencies listed in `build_requirements.txt`

NOTE: For the bot to properly work:
- The game language must be English;
- The date format must be 1982-1-23;
- The game must be fullscreen at 1920x1080 resolution;
- You must be running on a Windows operating system (non-Windows OSes compatibility is not yet implemented for this branch)
