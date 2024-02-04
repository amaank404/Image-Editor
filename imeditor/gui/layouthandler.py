"""
This module handles layout management for dynamic layouts. It automatically calculates absolute positon
and dimensions for any widget provided its layout object (preferred size). A tree of layoutobjectlist
can be used to make up a layout. then the calculate method of the parent layout object can be used
and it will automatically setup rendered objects for all sublayouts.

cross axis alignment is alignment for the opposite direction axis
main axis alignment is alignment for the main direciton axis

if no flex objects are present in a layoutobjectlist. the main axis alignment is used to distribute
the given objects accordingly.
"""

import enum
from typing import List, Tuple
import textwrap

import pygame

class LayoutUnit(enum.Enum):
    ABSOLUTE = 0  # Absolute amount of space available
    PERCENTAGE = 1  # Percentage of space available
    FLEX = 2  # In case of flex, the values are the proportion of alloted space

class LayoutDirection(enum.Enum):
    HORIZONTAL = 0
    VERTICAL = 1

class LayoutCrossAxisAlignment(enum.Enum):
    CENTER = 0
    START = 1
    END = 2

class LayoutMainAxisAlignment(enum.Enum):
    CENTER = 0
    START = 1
    END = 2


class LayoutObject():
    def __init__(self, x: int = None, y: int = None, unit_x: LayoutUnit = LayoutUnit.ABSOLUTE, unit_y: LayoutUnit = LayoutUnit.ABSOLUTE) -> None:
        if x is None:
            x = 1
            unit_x = LayoutUnit.FLEX
        
        if y is None:
            y = 1
            unit_y = LayoutUnit.FLEX
        
        self.x = x
        self.y = y
        self.unit_x = unit_x
        self.unit_y = unit_y
        self.rendered: RenderedLayoutObject = RenderedLayoutObject((0, 0), (0, 0))

    def __repr__(self) -> str:
        return f"LayoutObject[{self.rendered}]"
    
    def calculate(self, spacex: int, spacey: int, offset: Tuple[int, int]) -> Tuple[int, int]:
        def decide(val, unit, axis, space):
            if unit == LayoutUnit.ABSOLUTE:
                if val > space:
                    print(f"Warning: A LayoutObject with absolute sizing {val} requires more space than alloted space {space} in axis {axis}")
                    return space
                else:
                    return val
            elif unit == LayoutUnit.FLEX:
                return space
            elif unit == LayoutUnit.PERCENTAGE:
                if val > 100:
                    print(f"Warning: A LayoutObject with percentage sizing {val} has exceeded 100")
                    return space
                else:
                    return int(space*(val/100))
        
        width = decide(self.x, self.unit_x, 'x', spacex)
        height = decide(self.y, self.unit_y, 'y', spacey)

        self.rendered.pos = offset
        self.rendered.dim = (width, height)

        return (width, height)
        
    def reoffset(self, offset: Tuple[int, int]):
        self.rendered.offset(x = offset[0], y = offset[1])


class LayoutObjectStack(LayoutObject):
    def __init__(
        self,
        x: int = None,
        y: int = None,
        unit_x: LayoutUnit = LayoutUnit.ABSOLUTE,
        unit_y: LayoutUnit = LayoutUnit.ABSOLUTE, *,
        children: List[LayoutObject]=None,
        xalign: LayoutCrossAxisAlignment = LayoutCrossAxisAlignment.START,
        yalign: LayoutCrossAxisAlignment = LayoutCrossAxisAlignment.START,
    ):
        super().__init__(x, y, unit_x, unit_y)

        if children is not None:
            self.children = children
        else:
            self.children = []
            
        self.xalign = xalign
        self.yalign = yalign

    def calculate(self, spacex: int, spacey: int, offset: Tuple[int, int]) -> Tuple[int, int]:
        width, height = super().calculate(spacex, spacey, offset)
        for child in self.children:
            (w, h) = child.calculate(spacex, spacey, offset)
            if self.xalign == LayoutCrossAxisAlignment.START:
                xoffset = 0
            elif self.xalign == LayoutCrossAxisAlignment.CENTER:
                xoffset = (spacex-w)//2
            elif self.xalign == LayoutCrossAxisAlignment.END:
                xoffset = (spacex-w)

            if self.yalign == LayoutCrossAxisAlignment.START:
                yoffset = 0
            elif self.yalign == LayoutCrossAxisAlignment.CENTER:
                yoffset = (spacey-h)//2
            elif self.yalign == LayoutCrossAxisAlignment.END:
                yoffset = (spacey-h)
            
            child.reoffset((xoffset, yoffset))
        
        return width, height

    def add(self, obj: LayoutObject):
        self.children.append(obj)
    
    def insert(self, pos: int, obj: LayoutObject):
        self.children.insert(pos, obj)
    
    def remove(self, pos: int):
        self.children.pop(pos)

    def __repr__(self) -> str:
        if len(self.children) == 0:
            return f"LayoutObjectStack[{repr(self.rendered)}]"
        item = f"LayoutObjectStack[{repr(self.rendered)}\n"
        for child in self.children:
            item += textwrap.indent(repr(child), "    ")+",\n"
        item += "]"
        return item
    
    
    def reoffset(self, offset: Tuple[int, int]):
        super().reoffset(offset)
        for child in self.children:
            child.reoffset(offset)
            
    

class LayoutObjectList(LayoutObject):
    def __init__(
            self, 
            x: int = None, 
            y: int = None,
            unit_x: LayoutUnit = LayoutUnit.ABSOLUTE, 
            unit_y: LayoutUnit = LayoutUnit.ABSOLUTE, *,
            children: List[LayoutObject]=None, 
            direction: LayoutDirection = LayoutDirection.HORIZONTAL,
            mainalign: LayoutMainAxisAlignment = LayoutMainAxisAlignment.START,
            crossalign: LayoutCrossAxisAlignment = LayoutCrossAxisAlignment.START,
        ) -> None:
        super().__init__(x, y, unit_x, unit_y)
        
        if children is not None:
            self.children = children
        else:
            self.children = []
        
        self.direction = direction
        self.mainalign = mainalign
        self.crossalign = crossalign

    def add(self, obj: LayoutObject):
        self.children.append(obj)
    
    def insert(self, pos: int, obj: LayoutObject):
        self.children.insert(pos, obj)
    
    def remove(self, pos: int):
        self.children.pop(pos)

    def __repr__(self) -> str:
        if len(self.children) == 0:
            return f"LayoutObjectList[{repr(self.rendered)}]"
        item = f"LayoutObjectList[{repr(self.rendered)}\n"
        for child in self.children:
            item += textwrap.indent(repr(child), "    ")+",\n"
        item += "]"
        return item
        
    def calculate(self, spacex: int, spacey: int, offset: Tuple[int, int] = (0, 0)) -> Tuple[int, int]:
        (width, height) = super().calculate(spacex, spacey, offset)  # First calculate the object dimensions

        curspacex = width
        curspacey = height

        if self.direction == LayoutDirection.HORIZONTAL:  # We distribute the x axis
            for child in self.children:
                if child.unit_x == LayoutUnit.ABSOLUTE:  # for the first filter, we are only gonna be looking at the absolute value children
                    (w, _) = child.calculate(curspacex, curspacey, offset)
                    curspacex -= w

            tw = 0
            for child in self.children:
                if child.unit_x == LayoutUnit.PERCENTAGE:  # for the second filter, we are gonna sort out the percentage value children
                    (w, _) = child.calculate(curspacex, curspacey, offset)
                    tw += w

            curspacex -= tw
            if curspacex < 0:
                curspacex = 0
                print("Warning: Probably, total children percentages add up to more than 100 and have overfilled the remaining space. Some visual overflow may be seen")

            totalflex = 0
            for child in self.children:
                if child.unit_x == LayoutUnit.FLEX:  # for the last filter, first we will count total flex portions.
                    totalflex += child.x

            if totalflex != 0:  # Runs only if some flex children are there
                flexdivision = curspacex/totalflex
                
                for child in self.children:
                    if child.unit_x == LayoutUnit.FLEX:  # and then divide the remaining space according to proportion.
                        flexspace = int(flexdivision * child.x)
                        (w, _) = child.calculate(flexspace, curspacey, offset)
                        curspacex -= w
                
            # Now, we first check if we are going to do mainaxisalignment.
            curwidth = 0
            offsetx = 0
            if curspacex > 0:
                if self.mainalign == LayoutMainAxisAlignment.START:
                    offsetx = 0 
                elif self.mainalign == LayoutMainAxisAlignment.CENTER:
                    offsetx = curspacex//2
                elif self.mainalign == LayoutMainAxisAlignment.END:
                    offsetx = curspacex
            
            for child in self.children:
                if self.crossalign == LayoutCrossAxisAlignment.START:
                    offsety = 0
                elif self.crossalign == LayoutCrossAxisAlignment.CENTER:
                    offsety = (curspacey - child.rendered.dim[1])//2
                elif self.crossalign == LayoutCrossAxisAlignment.END:
                    offsety = curspacey - child.rendered.dim[1]
                child.reoffset((offsetx+curwidth, offsety))
                curwidth += child.rendered.dim[0]

        elif self.direction == LayoutDirection.VERTICAL:  # We distribute the y axis
            for child in self.children:
                if child.unit_y == LayoutUnit.ABSOLUTE:  # for the first filter, we are only gonna be looking at the absolute value children
                    (_, h) = child.calculate(curspacex, curspacey, offset)
                    curspacey -= h

            th = 0
            for child in self.children:
                if child.unit_y == LayoutUnit.PERCENTAGE:  # for the second filter, we are gonna sort out the percentage value children
                    (_, h) = child.calculate(curspacex, curspacey, offset)
                    th += h

            curspacey -= th
            if curspacey < 0:
                curspacey = 0
                print("Warning: Probably, total children percentages add up to more than 100 and have overfilled the remaining space. Some visual overflow may be seen")

            totalflex = 0
            for child in self.children:
                if child.unit_y == LayoutUnit.FLEX:  # for the last filter, first we will count total flex portions.
                    totalflex += child.y

            if totalflex != 0:  # Runs only if some flex children are there
                flexdivision = curspacey/totalflex
                
                for child in self.children:
                    if child.unit_y == LayoutUnit.FLEX:  # and then divide the remaining space according to proportion.
                        flexspace = int(flexdivision * child.y)
                        (_, h) = child.calculate(curspacex, flexspace, offset)
                        curspacey -= h
                
            # Now, we first check if we are going to do mainaxisalignment.
            curheight = 0
            offsety = 0
            if curspacey > 0:
                if self.mainalign == LayoutMainAxisAlignment.START:
                    offsety = 0 
                elif self.mainalign == LayoutMainAxisAlignment.CENTER:
                    offsety = curspacey//2
                elif self.mainalign == LayoutMainAxisAlignment.END:
                    offsety = curspacey
            
            for child in self.children:
                if self.crossalign == LayoutCrossAxisAlignment.START:
                    offsetx = 0
                elif self.crossalign == LayoutCrossAxisAlignment.CENTER:
                    offsetx = (curspacex - child.rendered.dim[0])//2
                elif self.crossalign == LayoutCrossAxisAlignment.END:
                    offsetx = curspacex - child.rendered.dim[0]
                child.reoffset((offsetx, offsety+curheight))
                curheight += child.rendered.dim[1]
        
        return width, height

    def reoffset(self, offset: Tuple[int, int]):
        super().reoffset(offset)
        for child in self.children:
            child.reoffset(offset)


class RenderedLayoutObject():
    def __init__(self, pos: Tuple[int, int], dim: Tuple[int, int]) -> None:
        self.pos = pos  # position
        self.dim = dim  # dimensions

    def __repr__(self) -> str:
        return f"x{self.pos[0]}, y{self.pos[1]}, w{self.dim[0]}, h{self.dim[1]}" 
    
    def offset(self, *, x = 0, y = 0):
        self.pos = (self.pos[0] + x, self.pos[1] + y)
    
    def with_offset(self, *, x = 0, y = 0):
        return (self.pos[0] + x, self.pos[1] + y)

    @property
    def bottomright(self) -> Tuple[int, int]:
        return (self.pos[0]+self.dim[0], self.pos[1]+self.dim[1])
    
    @property
    def bottomleft(self) -> Tuple[int, int]:
        return (self.pos[0], self.pos[1]+self.dim[1])
    
    @property
    def topright(self) -> Tuple[int, int]:
        return (self.pos[0]+self.dim[0], self.pos[1])
    
    @property
    def topleft(self) -> Tuple[int, int]:
        return self.pos
    
    @property
    def pgrect(self) -> pygame.Rect:
        return pygame.Rect(self.pos, self.dim)
    
    def collides(self, val: Tuple[int, int]) -> bool:
        if (
            (val[0] >= self.pos[0] and val[0] <= self.pos[0]+self.dim[0]) and
            (val[1] >= self.pos[1] and val[1] <= self.pos[1]+self.dim[1])
        ):
            return True
        else:
            return False

    def with_poszero(self) -> "RenderedLayoutObject":
        return RenderedLayoutObject((0, 0), self.dim)