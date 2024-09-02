# -*- coding: utf-8 -*-
import datetime
import glob
import os
import math
import time
import argparse
import importlib
import numpy as np
import cv2


# Start the clock... now!
timeStart = datetime.datetime.now().replace(microsecond=0)


#
# Setup Argument Parser
#
def is_valid_file(p, arg):
    if not os.path.isfile(arg):
        p.error('The file {} does not exist!'.format(arg))
    else:
        # File exists so return the filename
        return arg


def is_valid_directory(p, arg):
    dirName = arg.strip("\"")  # Remove trailing double-quote
    if not os.path.isdir(dirName):
        p.error('The directory {} does not exist!'.format(dirName))
    else:
        # File exists so return the directory
        return dirName


parser = argparse.ArgumentParser(description='Generate a fighting game match index with timestamps and characters used.')

parser.add_argument(
    'layout',
    help='Name of the layout to use',
    metavar='LAYOUT')

parser.add_argument(
    'filename',
    help='The video file to index',
    metavar='FILENAME', type=lambda x: is_valid_file(parser, x))

parser.add_argument('-c', help='Output CSV format', action='store_true')

parser.add_argument('-i', help='Include clock detection', action='store_true')

parser.add_argument('-n', help='Show match number sequentially in output', action='store_true')

parser.add_argument('-p', help='Preview while indexing (press \'Q\' to quit the preview)', action='store_true')

parser.add_argument(
    '-t',
    help='Path to templates folder (default: \"templates\" in current folder)',
    metavar='DIR', type=lambda x: is_valid_directory(parser, x))

parser.add_argument('-z', help='Zoom preview window down to 50%% (used with the -p option)', action='store_true')

args = parser.parse_args()

#
# Process arguments
#
# Check filename
videoFile = args.filename

# Check templates
if args.t:
    templatePath = os.path.join(args.t,'')
    print('Custom templates path: {0}'.format(templatePath))
else:
    templatePath = os.path.join('templates','')
    print('Default templates path: {0}'.format(templatePath))

# Check layouts
if not os.path.isfile(os.path.join('layouts', args.layout + '.py')):
    print("Layout {0}.py file does not exist in layouts/".format(args.layout))
    exit()
else:
    layoutFile = importlib.import_module("layouts." + args.layout)
    print('Layout: {0}'.format(args.layout))

# Check clock detection inclusion
if args.i:
    includeClock = True
    print("Clock detection: included")
else:
    includeClock = False
    print("Clock detection: excluded")

# Check preview
if args.p:
    previewVideo = True
    print("Preview: on")
else:
    previewVideo = False
    print("Preview: off")


# Initialise ROI variables from layout file
templateScale = layoutFile.layout['scale']
roiP1 = layoutFile.layout['originPlayer1']
roiP2 = layoutFile.layout['originPlayer2']
roiPw = layoutFile.layout['widthPortrait']
roiPh = layoutFile.layout['heightPortrait']
if includeClock:
    roiClk = layoutFile.layout['originClock']
    roiCw = layoutFile.layout['widthClock']
    roiCh = layoutFile.layout['heightClock']

if "threshold" in layoutFile.layout: 
    threshold = layoutFile.layout['threshold']
else:
    threshold = 0.9 # Default
print("Detection Threshold: {0}".format(threshold))


# TO-DO: Make the debug flag more useful
debug = False

#
# Match Information
#
def printMatchInfo(mID, mStart, p1, p2, mDuration):

    # Output in csv
    if args.c:
        delim = ","

        if args.n:
            mIDString = str(mID) + delim  # Show the match IDs (sequential no)
        else:
            mIDString = ''  # Don't show the match IDs

        outString = mIDString + mStart + delim + p1 + delim + p2 + delim + mDuration

    # Output in plain text
    else:
        if args.n:
            mIDString = str(mID) + '. ' # Show the match IDs (sequential no)
        else:
            mIDString = ''  # Don't show the match IDs

        outString = mIDString + mStart + " - " + p1 + " vs " + p2 + " (" + mDuration + ")"

    print(outString)

#
# Usage Information
#
def printUsageInfo(usageList):

    print('Character Appearance in Video')
    print('-----------------------------')

    usageSummary = []
    for useIndex, useTotal in enumerate(usageList):
        usageSummary.append([name_list[useIndex], useTotal])

    # Filter Usage Summary list (remove characters not used)
    usageFiltered = [i for i in usageSummary if i[1] > 0]

    # Sort Usage Summary list (most to least used)
    usageSorted = sorted(usageFiltered, key=lambda t: t[1], reverse=True)

    # Output character name and play count
    for u in usageSorted:
        print(u[0] + ':', u[1])


# No. of frames to skip: speeds up analysis
frameSkip = 30

# No. of seconds before we consider detection lost
detectThresholdSec = 6
if includeClock: clockThresholdSec = 1

# Video input
cap = cv2.VideoCapture(videoFile)

# Determine frames per second of video
fps = cap.get(cv2.CAP_PROP_FPS)

# (OBS Hack) Incorrectly reports 62.5 fps
if fps == 62.5:
    fps = 60

# Get other video properties
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
totalFrames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

print('Video: {0}' . format(videoFile))
print('Frame width: {0:.0f}' . format(width))
print('Frame height: {0:.0f}' . format(height))
print('Frame rate: {0:.2f} fps' . format(fps))
print('Length: {0}' . format(
    time.strftime("%H:%M:%S", time.gmtime(totalFrames / fps))))
print('--')

# No. of Frames before we lose detection
detectThreshold = detectThresholdSec * fps
if includeClock: clockThreshold = clockThresholdSec * fps

# Empty list to store template images
template_list1 = []
template_list2 = []
name_list = []
usage_list = []
nameIndex1 = 0
nameIndex2 = 0

# Make a list of all Player 1 and 2 template images from a directory
files1 = glob.glob(templatePath + '*-1p.jpg')
files2 = glob.glob(templatePath + '*-2p.jpg')

# Prepare the Player 1 and 2 templates
for myfile in files1:
    image = cv2.imread(myfile, 0)
    # Resize
    resImage = cv2.resize(image, None, fx=templateScale, fy=templateScale, interpolation=cv2.INTER_LINEAR)
    template_list1.append(resImage)
    charaName = os.path.basename(myfile).replace('-1p.jpg', '').title()
    name_list.append(charaName)  # Build the character name list
    usage_list.append(0)  # Initialise usage values to 0

for myfile in files2:
    image = cv2.imread(myfile, 0)
    # Resize
    resImage = cv2.resize(image, None, fx=templateScale, fy=templateScale, interpolation=cv2.INTER_LINEAR)
    template_list2.append(resImage)

# Prepare the Clock template
if includeClock:
    clockImage = cv2.imread(templatePath + 'clock.jpg', 0)
    clockTemplate = cv2.resize(clockImage, None, fx=templateScale, fy=templateScale, interpolation=cv2.INTER_LINEAR)

# Init variables
frameCount = 0
matchDetected1 = False
matchDetected2 = False
thresholdCount1 = 0
thresholdCount2 = 0
previouslyDetected = False
matchCount = 0
firstPass = True
if includeClock:
    clockDetected = False
    clockCount = 0
    firstPassClock = True
    clockPreviouslyOn = False
else:
    clockDetected = True


# Text label properties
fontFace = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 0.7
fontColor = (255, 255, 255)
fontThickness = 2
borderThickness = 1
textPadding = 2
colorBlue = (255, 0, 0)
colorRed = (0, 0, 255)
colorCyan = (255, 255, 0)
colorFill = -1


#
# Draw Label function
#
def drawLabel(text, img, origin, bgcolor):

    textSize, textBaseline = cv2.getTextSize(text, fontFace, fontScale, fontThickness)
    labelOrigin = (origin[0] - int(borderThickness / 2), origin[1] - textSize[1] - borderThickness - textPadding * 2)
    labelSize = (textSize[0] + textPadding * 2, textSize[1] + borderThickness + textPadding * 2)
    cv2.rectangle(img, labelOrigin, tuple(np.add(labelOrigin, labelSize)), bgcolor, colorFill)
    textOrigin = (origin[0] + textPadding, origin[1] - textPadding - borderThickness)
    cv2.putText(img, text, textOrigin, fontFace, fontScale, fontColor, fontThickness)

# Setup preview window
if previewVideo:
    if args.z:
        previewWidth = int(width/2)
        previewHeight = int(height/2)
    else:
        previewWidth = int(width)
        previewHeight = int(height)

    cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('frame', previewWidth, previewHeight)

#
# Start capture
#
while cap.isOpened():
    ret, frame = cap.read()

    if ret:
        frameCount += 1

        # Let's only check every few frames as defined by frameCount
        if frameSkip > 0 and frameCount % frameSkip != 0:
            continue

        #
        # Setup Clock ROI: frame[ row_range (y-coord), col_range (x-coord) ]
        #
        if includeClock:
            imgClk_roi = frame[roiClk[1]:roiClk[1] + roiCh, roiClk[0]:roiClk[0] + roiCw]
            imgClk_gray = cv2.cvtColor(imgClk_roi, cv2.COLOR_BGR2GRAY)
            # Draw Clock ROI
            if previewVideo:
                cv2.rectangle(frame, roiClk, (roiClk[0] + roiCw, roiClk[1]+roiCh), colorCyan, borderThickness)

            w3, h3 = clockTemplate.shape[::-1]
            res3 = cv2.matchTemplate(imgClk_gray, clockTemplate, cv2.TM_CCOEFF_NORMED)
            loc3 = np.where(res3 >= threshold)

            if len(loc3[0]):
                # Detected
                if (clockCount > clockThreshold) and not clockDetected:
                    clockDetected = True
                    clockCount = 0
                else:
                    clockCount += 1 + frameSkip
            else:
                # Not detected
                if (clockCount > clockThreshold) and clockDetected:
                    clockDetected = False
                    clockCount = 0
                else:
                    clockCount += 1 + frameSkip

            if clockDetected and firstPassClock:
                firstPassClock = False
                clockPreviouslyOn = True

            if not clockDetected and clockPreviouslyOn:
                firstPassClock = True
                clockPreviouslyOn = False

            if previewVideo and clockDetected:
                for pt3 in zip(*loc3[::-1]):
                    # Draw the detected rectangle
                    cv2.rectangle(frame,
                                (roiClk[0] + pt3[0], roiClk[1] + pt3[1]),
                                (roiClk[0] + pt3[0] + w3, roiClk[1] + pt3[1] + h3),
                                colorBlue,
                                borderThickness)

        #
        # Player 1 ROI: frame[ row_range (y-coord), col_range (x-coord) ]
        #
        img1_roi = frame[roiP1[1]:roiP1[1] + roiPh, roiP1[0]:roiP1[0] + roiPw]
        img1_gray = cv2.cvtColor(img1_roi, cv2.COLOR_BGR2GRAY)

        # Draw P1 ROI
        if previewVideo:
            cv2.rectangle(frame, roiP1, (roiP1[0] + roiPw, roiP1[1] + roiPh), colorCyan, borderThickness)

        #
        # Player 1 Check
        #
        if matchDetected1:

            # Keep monitoring the previously matched template
            w1, h1 = template_list1[nameIndex1].shape[::-1]
            res1 = cv2.matchTemplate(img1_gray, template_list1[nameIndex1], cv2.TM_CCOEFF_NORMED)
            loc1 = np.where(res1 >= threshold)

            if len(loc1[0]):
                # Still detected
                thresholdCount1 = 0
                textName1 = name_list[nameIndex1]
                if previewVideo:
                    for pt1 in zip(*loc1[::-1]):
                        # Draw the detected rectangle
                        detOrigin = (roiP1[0] + pt1[0], roiP1[1] + pt1[1])
                        detSize = (w1, h1)
                        cv2.rectangle(frame, detOrigin, tuple(np.add(detOrigin, detSize)), colorRed, borderThickness)

                        # Draw the detection label above the rectangle
                        drawLabel(textName1, frame, detOrigin, colorRed)
            else:
                # No match
                if thresholdCount1 > detectThreshold:
                    # Detection loss timeout
                    matchDetected1 = False
                    firstPass = True
                else:
                    # Start timer on detection loss
                    thresholdCount1 += 1 + frameSkip
        else:

            # Loop until we find a matching template
            for templateIndex1, template1 in enumerate(template_list1):

                w1, h1 = template1.shape[::-1]
                res1 = cv2.matchTemplate(img1_gray, template1, cv2.TM_CCOEFF_NORMED)
                loc1 = np.where(res1 >= threshold)

                if len(loc1[0]):
                    # Detected successfully
                    thresholdCount1 = 0
                    matchDetected1 = True
                    nameIndex1 = templateIndex1
                    if debug:
                        print('### P1', name_list[nameIndex1], '(template no: ' + str(nameIndex1) + ')', 'matched on:', time.strftime('%H:%M:%S', time.gmtime(frameCount / fps)))
                    break

        #
        # Player 2 ROI: frame[ row_range (y-coord), col_range (x-coord) ]
        #
        img2_roi = frame[roiP2[1]:roiP2[1] + roiPh, roiP2[0]:roiP2[0] + roiPw]
        img2_gray = cv2.cvtColor(img2_roi, cv2.COLOR_BGR2GRAY)
        # Draw P2 ROI
        if previewVideo:
            cv2.rectangle(frame,
                          roiP2,
                          (roiP2[0] + roiPw, roiP2[1] + roiPh),
                          colorCyan,
                          borderThickness)

        #
        # Player 2 Check
        #
        if matchDetected2:

            # Keep monitoring the previously matched template
            w2, h2 = template_list2[nameIndex2].shape[::-1]
            res2 = cv2.matchTemplate(img2_gray, template_list2[nameIndex2], cv2.TM_CCOEFF_NORMED)
            loc2 = np.where(res2 >= threshold)

            if len(loc2[0]):
                # Still detected
                thresholdCount2 = 0
                textName2 = name_list[nameIndex2]
                if previewVideo:
                    for pt2 in zip(*loc2[::-1]):
                        # Draw the detected rectangle
                        detOrigin = (roiP2[0] + pt2[0], roiP2[1] + pt2[1])
                        detSize = (w2, h2)
                        cv2.rectangle(frame, detOrigin, tuple(np.add(detOrigin, detSize)), colorBlue, borderThickness)

                        # Draw the detection label above the rectangle
                        drawLabel(textName2, frame, detOrigin, colorBlue)
            else:
                # No match
                if thresholdCount2 > detectThreshold:
                    matchDetected2 = False
                else:
                    thresholdCount2 += 1 + frameSkip
        else:

            # Loop until we find a matching template
            for templateIndex2, template2 in enumerate(template_list2):

                w2, h2 = template2.shape[::-1]
                res2 = cv2.matchTemplate(img2_gray, template2, cv2.TM_CCOEFF_NORMED)
                loc2 = np.where(res2 >= threshold)

                if len(loc2[0]):
                    # Detected
                    thresholdCount2 = 0
                    matchDetected2 = True
                    nameIndex2 = templateIndex2
                    if debug:
                        print('### P2', name_list[nameIndex2], '(template no: ' + str(nameIndex2) + ')', 'matched on:', time.strftime('%H:%M:%S', time.gmtime(frameCount / fps)))
                    break

        #
        # Are we detecting a match for the first time?
        #
        if clockDetected and matchDetected1 and matchDetected2 and firstPass:
            firstPass = False
            previouslyDetected = True
            matchStart = frameCount / fps
            matchStartText = format(datetime.timedelta(seconds=math.trunc(matchStart)))
            # Print match start info
            # print(str(matchCount)+".", name_list[nameIndex1], "vs", name_list[nameIndex2], "started on", matchStartText)

        #
        # If we previously detected a match but now we don't, then record the end of match
        #
        if not matchDetected1 and not matchDetected2 and previouslyDetected:
            firstPass = True
            previouslyDetected = False
            matchCount += 1
            matchEnd = frameCount / fps - detectThresholdSec
            matchEndText = format(datetime.timedelta(seconds=matchEnd))
            matchDuration = time.strftime("%H:%M:%S", time.gmtime(matchEnd - matchStart))
            # Print match end info
            # print(str(matchCount)+".", name_list[nameIndex1], "vs", name_list[nameIndex2], "ended on", time.strftime('%H:%M:%S', time.gmtime(matchEnd)))
            # Print match info
            #print(str(matchCount) + ".", matchStartText, "-", name_list[nameIndex1], "vs", name_list[nameIndex2], "(" + matchDuration + ")")
            printMatchInfo(matchCount, matchStartText, name_list[nameIndex1], name_list[nameIndex2], matchDuration)
            usage_list[nameIndex1] += 1  # Increment character usage (P1)
            usage_list[nameIndex2] += 1  # Increment character usage (P2)

        # Preview video during processsing, if enabled
        if previewVideo:
            # cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
            # cv2.resizeWindow('frame', int(width/2), int(height/2))
            cv2.imshow('frame', frame)
            if cv2.waitKey(11) & 0xFF == ord('q'):
                break

    else:
        # End of video reached, but check that a match wasn't in progress
        if matchDetected1 and matchDetected2 and previouslyDetected:
            matchCount += 1
            matchEnd = frameCount / fps
            matchEndText = format(datetime.timedelta(seconds=matchEnd))
            matchDuration = time.strftime("%H:%M:%S", time.gmtime(matchEnd - matchStart))
            # print(str(matchCount) + ".", matchStartText, "-", name_list[nameIndex1], "vs", name_list[nameIndex2], "(" + matchDuration + ")")
            printMatchInfo(matchCount, matchStartText, name_list[nameIndex1], name_list[nameIndex2], matchDuration)
            usage_list[nameIndex1] += 1  # Increment character usage (P1)
            usage_list[nameIndex2] += 1  # Increment character usage (P2)
        break

cap.release()
cv2.destroyAllWindows()
timeEnd = datetime.datetime.now().replace(microsecond=0)
print('--')
print('Total matches:', matchCount)
print('Processing Time started:', timeStart)
print('Processing Time ended:', timeEnd)
print('Processing Time taken:', (timeEnd - timeStart))
print('')
printUsageInfo(usage_list)
