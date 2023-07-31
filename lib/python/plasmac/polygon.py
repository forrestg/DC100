'''
polygon.py

Copyright (C) 2020, 2021, 2022  Phillip A Carter
Copyright (C) 2020, 2021, 2022  Gregory D Carl

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import os
import sys
import math
import gettext

for f in sys.path:
    if '/lib/python' in f:
        if '/usr' in f:
            localeDir = 'usr/share/locale'
        else:
            localeDir = os.path.join('{}'.format(f.split('/lib')[0]),'share','locale')
        break
gettext.install("linuxcnc", localedir=localeDir)

# Conv is the upstream calling module
def preview(Conv, fTmp, fNgc, fNgcBkp, \
            matNumber, matName, \
            preAmble, postAmble, \
            leadinLength, leadoutLength, \
            isCenter, xOffset, yOffset, \
            kerfWidth, isExternal, \
            sides, diameter, sAngle, \
            inStyle, diaOrLen):
    error = ''
    msg1 = _('entry is invalid')
    valid, xOffset = Conv.conv_is_float(xOffset)
    if not valid and xOffset:
        msg0 = _('X ORIGIN')
        error += '{} {}\n\n'.format(msg0, msg1)
    valid, yOffset = Conv.conv_is_float(yOffset)
    if not valid and yOffset:
        msg0 = _('Y ORIGIN')
        error += '{} {}\n\n'.format(msg0, msg1)
    valid, leadinLength = Conv.conv_is_float(leadinLength)
    if not valid and leadinLength :
        msg0 = _('LEAD IN')
        error += '{} {}\n\n'.format(msg0, msg1)
    valid, leadoutLength = Conv.conv_is_float(leadoutLength)
    if not valid and leadoutLength:
        msg0 = _('LEAD OUT')
        error += '{} {}\n\n'.format(msg0, msg1)
    valid, sides = Conv.conv_is_int(sides)
    if not valid and sides:
        msg0 = _('SIDES')
        error += '{} {}\n\n'.format(msg0, msg1)
    valid, diameter = Conv.conv_is_float(diameter)
    if not valid and diameter:
        error += '{} {}\n\n'.format(diaOrLen, msg1)
    valid, sAngle = Conv.conv_is_float(sAngle)
    if not valid and sAngle:
        msg0 = _('ANGLE')
        error += '{} {}\n\n'.format(msg0, msg1)
    valid, kerfWidth = Conv.conv_is_float(kerfWidth)
    if not valid:
        msg = _('Invalid Kerf Width entry in material')
        error += '{}\n\n'.format(msg)
    if error:
        return error
    if sides < 3:
        msg = _('More than two SIDES required')
        error += '{}\n\n'.format(msg)
    if diameter == 0:
        msg = _('DIAMETER cannot be zero')
        error += '{}\n\n'.format(msg)
    if error:
        return error
    if inStyle == 0: # circumscribed
        radius = diameter / 2
    elif inStyle == 1: # inscribed
        radius = (diameter / 2) / math.cos(math.radians(180 / sides))
    else: # side length
        radius = diameter / (2 * math.sin(math.radians(180 / sides)))
    sAngle = math.radians(sAngle)
    ijOffset = radius * math.sin(math.radians(45))
    # get start point
    if isCenter:
        xS = float(xOffset)
        yS = float(yOffset)
    else:
        xS = float(xOffset) + radius# * math.cos(math.radians(0))
        yS = float(yOffset) + radius# * math.sin(math.radians(90))
    leadInOffset = float(leadinLength) / (2 * math.pi * (90.0 / 360))
    leadOutOffset = math.sin(math.radians(45)) * float(leadoutLength)
    # get all points
    pList = get_points(sides, sAngle, xS, yS, radius)
    # get offset required
    offset = get_offset([pList[2][0],pList[2][1]], [pList[1][0],pList[1][1]], [pList[0][0],pList[0][1]], kerfWidth)
    # get new points
    move = 0 if isCenter else offset
    if isExternal:
        pList = get_points(sides, sAngle, xS + move, yS + move, radius + offset)
    else:
        pList = get_points(sides, sAngle, xS - move, yS - move, radius - offset)
    # get center
    xCentre = (float(pList[0][0]) + float(pList[sides - 1][0])) / 2
    yCentre = (float(pList[0][1]) + float(pList[sides - 1][1])) / 2
    angle = math.atan2(float(pList[0][1]) - yCentre, float(pList[0][0]) - xCentre)
    right = math.radians(0)
    up = math.radians(90)
    left = math.radians(180)
    down = math.radians(270)
    if isExternal:
        dir = [down, right]
    else:
        dir = [up, left]
    outTmp = open(fTmp, 'w')
    outNgc = open(fNgc, 'w')
    inWiz = open(fNgcBkp, 'r')
    for line in inWiz:
        if '(new conversational file)' in line:
            if('\\n') in preAmble:
                outNgc.write('(preamble)\n')
                for l in preAmble.split('\\n'):
                    outNgc.write('{}\n'.format(l))
            else:
                outNgc.write('\n{} (preamble)\n'.format(preAmble))
            break
        elif '(postamble)' in line:
            break
        elif 'm2' in line.lower() or 'm30' in line.lower():
            continue
        outNgc.write(line)
    outTmp.write('\n(conversational polygon {})\n'.format(sides))
    outTmp.write(';using material #{}: {}\n'.format(matNumber, matName))
    outTmp.write('M190 P{}\n'.format(matNumber))
    outTmp.write('M66 P3 L3 Q1\n')
    outTmp.write('f#<_hal[plasmac.cut-feed-rate]>\n')
    if leadInOffset > 0:
        xlCentre = xCentre + (leadInOffset * math.cos(angle + dir[0]))
        ylCentre = yCentre + (leadInOffset * math.sin(angle + dir[0]))
        xlStart = xlCentre + (leadInOffset * math.cos(angle + dir[1]))
        ylStart = ylCentre + (leadInOffset * math.sin(angle + dir[1]))
        outTmp.write('g0 x{:.6f} y{:.6f}\n'.format(xlStart, ylStart))
        outTmp.write('m3 $0 s1\n')
        outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xCentre, yCentre, xlCentre - xlStart, ylCentre - ylStart))
    else:
        outTmp.write('g0 x{:.6f} y{:.6f}\n'.format(xCentre, yCentre))
        outTmp.write('m3 $0 s1\n')
    if isExternal:
        for i in range(sides, 0, -1):
            outTmp.write('g1 x{} y{}\n'.format(pList[i - 1][0], pList[i - 1][1]))
    else:
        for i in range(sides):
            outTmp.write('g1 x{} y{}\n'.format(pList[i][0], pList[i][1]))
    outTmp.write('g1 x{} y{}\n'.format(xCentre, yCentre))
    if leadOutOffset > 0:
        if isExternal:
            dir = [down, left]
        else:
            dir = [up, right]
        xlCentre = xCentre + (leadOutOffset * math.cos(angle + dir[0]))
        ylCentre = yCentre + (leadOutOffset * math.sin(angle + dir[0]))
        xlEnd = xlCentre + (leadOutOffset * math.cos(angle + dir[1]))
        ylEnd = ylCentre + (leadOutOffset * math.sin(angle + dir[1]))
        outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xlEnd, ylEnd , xlCentre - xCentre, ylCentre - yCentre))
    outTmp.write('m5 $0\n')
    outTmp.close()
    outTmp = open(fTmp, 'r')
    for line in outTmp:
        outNgc.write(line)
    outTmp.close()
    if('\\n') in postAmble:
        outNgc.write('(postamble)\n')
        for l in postAmble.split('\\n'):
            outNgc.write('{}\n'.format(l))
    else:
        outNgc.write('\n{} (postamble)\n'.format(postAmble))
    outNgc.write('m2\n')
    outNgc.close()
    return False

    pList = []
    for i in range(sides):
        angle = sAngle + 2 * math.pi * i / sides
        x = xS + radius * math.cos(angle)
        y = yS + radius * math.sin(angle)
        pList.append(['{:.6f}'.format(x), '{:.6f}'.format(y)])

def get_points(sides, sAngle, xS, yS, radius):
    pList = []
    for i in range(sides):
        angle = sAngle + 2 * math.pi * i / sides
        x = xS + radius * math.cos(angle)
        y = yS + radius * math.sin(angle)
        pList.append([round(x, 3), round(y, 3)])
    return pList

def get_offset(A, B, C, kerfWidth):
    Ax, Ay = A[0] - B[0], A[1] - B[1]
    Cx, Cy = C[0] - B[0], C[1] - B[1]
    a = math.atan2(Ay, Ax)
    c = math.atan2(Cy, Cx)
    if a < 0: a += math.pi * 2
    if c < 0: c += math.pi * 2
    ang = (math.pi * 2 + c - a) if a > c else (c - a)
    ang = math.radians(90) - (ang / 2)
    adj = (kerfWidth / 2) / math.sin(ang)
    ofs = math.tan(ang) * adj
    return ofs
