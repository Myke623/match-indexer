# Description
Generate a match index for your Fighting Game videos. The match index includes:
* Timestamps for all matches
* Characters used
* Duration of each match
* Summary of character totals

Want an easy way to create chapters for your YouTube videos? Just copy/paste the output into your video's description field, and away you go!

# Prerequisites
1. Download and install Python (https://python.org/downloads)
2. Install NumPy:
   * `pip install numpy`
3. Install OpenCV (ref: https://pypi.org/project/opencv-python/)
   * `pip install opencv-python`

# Installation
Download the match-indexer.py file along with sample templates and layouts folders to get started. These come prepared to detect Virtua Fighter 5 Final Showdown matches.

# Usage
From a terminal window:

    > python.exe match-indexer.py OPTIONS LAYOUT FILENAME

* OPTIONS: See the [Options](#Options) section for a list of the options.
* LAYOUT: 
* FILENAME: the filename of the video to process. See Filename Formats for more info.

# Options

    -h, --help  show this help message and exit
    -c          Output CSV format
    -p          Preview while indexing
    -n          Show match number sequentially in output
    -z          Zoom preview window down to 50%
    -t DIR      Path to templates folder (default: "templates" in current folder)


# Configuration
## Templates
For each character that exists in your Fighting Game, you need to create two "templates" to match against, one for Player 1 side and the other for Player 2. This was deliberately designed this way, as opposed to using a single image and flipping it, since some games have non-mirrored 1P vs 2P character portraits.

To define your characters, create a `.jpg` with the following naming convention:

    {character name}-1p.jpg
    {character name}-2p.jpg

The `{character name}` label will be used in the match indexer's output.

## Layouts
All about the layouts

# Output
Print to screen, redirect to file, csv to spreadsheet

# FAQ

### Question
Answer 