import pygame
import pygame.gfxdraw
from PIL import Image
import os
from functools import lru_cache
from typing import TypeAlias, Tuple, Union, List, Callable, Dict
import math
import enum

from . import layouthandler as lh
from .colors import *

# Defining the position type
Position: TypeAlias = Union[Tuple[int, int], pygame.Rect]

def _sizeargs(size: str) -> dict:
    args = {}
    sx, sy = size.split(",")
    if sx.endswith("f"):
        args["x"] = int(sx[:-1])
        args["unit_x"] = lh.LayoutUnit.FLEX
    elif sx.endswith("%"):
        args["x"] = int(sx[:-1])
        args["unit_x"] = lh.LayoutUnit.PERCENTAGE
    elif sx.isnumeric():
        args["x"] = int(sx)
        args["unit_x"] = lh.LayoutUnit.ABSOLUTE
    
    if sy.endswith("f"):
        args["y"] = int(sy[:-1])
        args["unit_y"] = lh.LayoutUnit.FLEX
    elif sy.endswith("%"):
        args["y"] = int(sy[:-1])
        args["unit_y"] = lh.LayoutUnit.PERCENTAGE
    elif sy.isnumeric():
        args["y"] = int(sy)
        args["unit_y"] = lh.LayoutUnit.ABSOLUTE

    return args

@lru_cache(1024*1024)
def _scale(val: int):
    return int(BuildContext().scale*val)


def _PILImagetopgsurf(pilImage):
    return pygame.image.fromstring(
        pilImage.tobytes(), pilImage.size, pilImage.mode).convert()


class BuildContext(object):
    def init(self) -> None:
        self.fonts: Dict[Tuple[int, str], pygame.font.FontType] = {}  # (Font size int, variant): Font Object pygame
        self.scale: float = 1.0
        self.root_widget: AppRoot = None
        self.state = {}
        self.setdefault = self.state.setdefault

    def __getitem__(self, key):
        if key in self.state:
            return self.state[key]
        else:
            return None
    
    def __setitem__(self, key, val):
        self.state[key] = val

    def __contains__(self, key):
        return key in self.state
    
    def __delitem__(self, key):
        del self.state[key]


    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(BuildContext, cls).__new__(cls)
            cls.instance.init()
        return cls.instance
    
    def get_font(self, fontsize: int, variant: str = "medium", fontname: str = "dmsans"):  # Other variants are bold and thin
        if (fontsize, variant) not in self.fonts:
            self.fonts[(fontsize, variant)] = pygame.font.Font(f"{os.path.dirname(__file__)}/fonts/{fontname}-{variant}.ttf", fontsize)
        return self.fonts[(fontsize, variant)]


# Basic widget class which can be inherited
class Widget():
    def __init__(self) -> None:
        self.blitsurface: pygame.SurfaceType = None
        self.position = (0, 0)
        self.layoutobject: lh.LayoutObject = lh.LayoutObject()
        self._prevargsrecalculate = [0, 0, (0, 0)]
        self._prevresults = None

    def render(self, window: pygame.SurfaceType):
        pygame.draw.rect(window, (255, 255, 255), (*self.layoutobject.rendered.pos, *self.layoutobject.rendered.dim))
        pygame.draw.rect(window, (0, 0, 0), (*self.layoutobject.rendered.pos, *self.layoutobject.rendered.dim), 1)
        pygame.draw.line(window, (0, 0, 0), self.layoutobject.rendered.topleft, self.layoutobject.rendered.bottomright)
        pygame.draw.line(window, (0, 0, 0), self.layoutobject.rendered.topright, self.layoutobject.rendered.bottomleft)

    def recalculate_layout(self, spacex: int = None, spacey: int = None, offset: Tuple[int, int] = None, forced: bool = False) -> Tuple[int, int]:
        forcedrun = forced
        if spacex is None:
            spacex = self.layoutobject.rendered.dim[0]
            forcedrun = True
        if spacey is None:
            spacey = self.layoutobject.rendered.dim[1]
            forcedrun = True
        if offset is None:
            offset = self.layoutobject.rendered.pos

        if self.layoutobject.rendered.dim[0] == spacex and self.layoutobject.rendered.dim[1] == spacey and self.layoutobject.rendered.pos == offset and not forcedrun:
            return self.layoutobject.rendered.dim
        
        data = self.layoutobject.calculate(spacex, spacey, offset)
        self.after_layout_recalculation()
        return data
    
    def after_layout_recalculation(self):
        pass
    
    def handle_mouse_movement(self, pos: Tuple[int, int]) -> bool: # These 3 functions will return true if the event is consumed and hence an action is performed
        return False

    def handle_mouse_down(self, pos: Tuple[int, int]) -> bool:
        return False

    def handle_mouse_up(self, pos: Tuple[int, int]) -> bool:
        return False

class PlaceHolder(Widget):
    def __init__(self, size: str = ",") -> None:
        super().__init__()
        self.layoutobject=lh.LayoutObject(**_sizeargs(size))


class WidgetWithChild(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.child: Widget = None

    def after_layout_recalculation(self):
        if self.child is not None:
            self.child.after_layout_recalculation()

    def set_child(self, child: Widget):
        self.child = child

    def handle_mouse_down(self, pos: Tuple[int, int]) -> bool:
        if self.child is not None:
            self.child.handle_mouse_down(pos)
    
    def handle_mouse_up(self, pos: Tuple[int, int]) -> bool:
        if self.child is not None:
            self.child.handle_mouse_up(pos)

    def handle_mouse_movement(self, pos: Tuple[int, int]) -> bool:
        if self.child is not None:
            self.child.handle_mouse_movement(pos)

class WidgetWithChildren(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.children: List[Widget] = []

    def after_layout_recalculation(self):
        for child in self.children:
            child.after_layout_recalculation()
    
    def add_child(self, child: Widget):
        self.children.append(child)
    
    def insert_child(self, position: int, child: Widget):
        self.children.insert(position, child)
    
    def remove_child(self, position: int):
        self.children.pop(position)


class AppRoot(WidgetWithChild):
    def __init__(self, title: str, icon: pygame.surface.Surface, fps: int = 60, *, child: Widget) -> None:
        super().__init__()
        self.child = child
        self.layoutobject = lh.LayoutObjectStack()
        self.layoutobject.children = [self.child.layoutobject]
        self._clock = pygame.time.Clock()
        self.fps = fps
        self.running = False

        BuildContext().root_widget = self

        self.window = pygame.display.set_mode((_scale(800), _scale(500)), pygame.RESIZABLE)
        pygame.display.set_caption(title)
        pygame.display.set_icon(icon)

    def set_child(self, child: Widget):
        self.child = child
        self.layoutobject.children = [self.child.layoutobject]
        self.recalculate_layout(*pygame.display.get_window_size(), (0, 0))
    
    def render(self, window: pygame.SurfaceType):
        window.fill(c_windowbg)
        self.child.render(window)

    def run(self, debug: bool = False) -> None:
        self.running = True
        self.recalculate_layout(*pygame.display.get_window_size(), (0, 0))
        while self.running:
            self._clock.tick(self.fps)
            for evt in pygame.event.get():
                if evt.type == pygame.QUIT:
                    self.running = False
                elif evt.type == pygame.MOUSEMOTION:
                    self.child.handle_mouse_movement(evt.pos)
                elif evt.type == pygame.MOUSEBUTTONDOWN:
                    self.child.handle_mouse_down(evt.pos)
                elif evt.type == pygame.MOUSEBUTTONUP:
                    self.child.handle_mouse_up(evt.pos)
                elif evt.type == pygame.VIDEORESIZE:
                    self.recalculate_layout(*pygame.display.get_window_size(), (0, 0))
        
            self.render(self.window)
            pygame.display.flip()


class Column(WidgetWithChildren):
    def __init__(self, *, children: List[Widget] = None, mainalign: lh.LayoutMainAxisAlignment = lh.LayoutCrossAxisAlignment.START, crossalign: lh.LayoutCrossAxisAlignment = lh.LayoutCrossAxisAlignment.START, size: str = ",", _direct=None) -> None:
        super().__init__()
        if _direct == None:
            _direct = lh.LayoutDirection.VERTICAL
        self.layoutobject = lh.LayoutObjectList(**_sizeargs(size), direction=_direct, mainalign=mainalign, crossalign=crossalign)
        if children is None:
            children = []
        
        for child in children:
            self.add_child(child, cancel_recalculate=True)

    def render(self, window: pygame.SurfaceType):
        for x in self.children:
            x.render(window)
        
    def add_child(self, child: Widget, *, cancel_recalculate: bool = False):
        super().add_child(child)
        self.layoutobject.add(child.layoutobject)
        if not cancel_recalculate:
            self.recalculate_layout()

    def insert_child(self, position: int, child: Widget, *, cancel_recalculate: bool = False):
        super().insert_child(position, child)
        self.layoutobject.insert(position, child.layoutobject)
        if not cancel_recalculate:
            self.recalculate_layout()

    def remove_child(self, position: int, *, cancel_recalculate: bool = False):
        super().remove_child(position)
        self.layoutobject.remove(position)
        if not cancel_recalculate:
            self.recalculate_layout()

    def handle_mouse_down(self, pos: Tuple[int, int]) -> bool:
        for child in self.children:
            child.handle_mouse_down(pos)
        return False
    
    def handle_mouse_movement(self, pos: Tuple[int, int]) -> bool:
        for child in self.children:
            child.handle_mouse_movement(pos)
        return False

    def handle_mouse_up(self, pos: Tuple[int, int]) -> bool:
        for child in self.children:
            child.handle_mouse_up(pos)
        return False


class Row(Column):
    def __init__(self, *, children: List[Widget] = None, mainalign: lh.LayoutMainAxisAlignment = lh.LayoutCrossAxisAlignment.START, crossalign: lh.LayoutCrossAxisAlignment = lh.LayoutCrossAxisAlignment.START, size: str = ",") -> None:
        super().__init__(children=children, mainalign=mainalign, crossalign=crossalign, size=size, _direct=lh.LayoutDirection.HORIZONTAL)


class VSep(Widget):
    def __init__(self, sep: int = 16) -> None:
        super().__init__()
        self._surf = None
        self.layoutobject = lh.LayoutObject(**_sizeargs(f"{_scale(3)},100%"))
        self.sep = _scale(sep)

    def render(self, window) -> None:
        pygame.draw.line(
            window,
            c_inversewindowbg,
            (_scale(1)+self.layoutobject.rendered.pos[0], self.sep+self.layoutobject.rendered.pos[1]),
            (_scale(1)+self.layoutobject.rendered.pos[0], self.layoutobject.rendered.dim[1]-self.sep+self.layoutobject.rendered.pos[1]),
            width=_scale(1)
        )

class HSep(Widget):
    def __init__(self, sep: int = 16) -> None:
        super().__init__()
        self._surf = None
        self.layoutobject = lh.LayoutObject(**_sizeargs(f"100%,{_scale(3)}"))
        self.sep = _scale(sep)

    def render(self, window) -> None:
        pygame.draw.line(
            window,
            c_inversewindowbg,
            (self.sep+self.layoutobject.rendered.pos[0], _scale(1)+self.layoutobject.rendered.pos[1]),
            (self.layoutobject.rendered.dim[0]-self.sep+self.layoutobject.rendered.pos[0], _scale(1)+self.layoutobject.rendered.pos[1]),
            width=_scale(1)
        )


class Button(Widget):
    def __init__(self, size: str = ',') -> None:
        super().__init__()
        self.layoutobject = lh.LayoutObject(**_sizeargs(size))
        self.hovering = False
        self.pressed = False
        self.disabled = False

    def action(self) -> None:
        pass

    def handle_mouse_movement(self, pos: Tuple[int, int], changecursor: bool = True):
        if self.layoutobject.rendered.collides(pos):
            self.hovering = True
            if changecursor:
                if not self.disabled:
                    pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_NO)
            return True
        else:
            if self.hovering:
                if changecursor:
                    pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_ARROW)
            self.hovering = False
        return False
    
    def handle_mouse_down(self, pos: Tuple[int, int]):
        if self.layoutobject.rendered.collides(pos):
            self.pressed = True
            return True
        return False
    
    def handle_mouse_up(self, pos: Tuple[int, int]):
        if self.layoutobject.rendered.collides(pos):
            if self.pressed and not self.disabled:
                self.pressed = False
                self.action()
                return True
        if self.pressed:
            self.pressed = False
        return False
    
    def set_disabled(self, disabled: bool = False):
        self.disabled = disabled


class MenuItemButton(Button):
    def __init__(self, text: str) -> None:
        self.textrendered = BuildContext().get_font(_scale(16)).render(text, True, c_primarytext)
        self.padding_width = _scale(16)
        self.padding_height = _scale(4)
        super().__init__(size=f"{self.padding_width*2 + self.textrendered.get_width()},{self.padding_height*2 + self.textrendered.get_height()}")

        self._hoversurf = pygame.Surface((self.layoutobject.x, self.layoutobject.y))
        self._hoversurf.fill((0, 0, 0))
        self._hoversurf.set_alpha(30)
        
    def render(self, window: pygame.SurfaceType):
        pygame.draw.rect(window, c_primary, self.layoutobject.rendered.pgrect)
        window.blit(self.textrendered, (self.layoutobject.rendered.pos[0]+self.padding_width, self.layoutobject.rendered.pos[1]+self.padding_height))
        if self.pressed:
            self._hoversurf.set_alpha(50)
        else:
            self._hoversurf.set_alpha(30)
        if self.hovering:
            window.blit(self._hoversurf, self.layoutobject.rendered.pos)


class MenuItem:
    def __init__(self, label: str, action: Callable) -> None:
        self.label = str
        self.action = action
        self.widget = MenuItemButton(text=label)
        self.widget.action = action


class _MenuSep(Widget):
    def __init__(self) -> None:
        self.layoutobject = lh.LayoutObject(**_sizeargs(size=f"{_scale(3)},100%"))
        self._surf = None
    
    def after_layout_recalculation(self):
        self._surf = pygame.Surface(self.layoutobject.rendered.dim)
        self._surf.fill(c_primary)
        pygame.draw.line(self._surf, c_inverseprimary, (_scale(1), _scale(8)), (_scale(1), self.layoutobject.rendered.dim[1]-_scale(8)), width=_scale(1))
    
    def render(self, window: pygame.SurfaceType):
        window.blit(self._surf, self.layoutobject.rendered.pos)


class MenuBar(Row):
    def __init__(self, *, menu_items = []) -> None:
        super().__init__(crossalign=lh.LayoutCrossAxisAlignment.CENTER, size="100%, 0" if len(menu_items) == 0 else f"100%,{menu_items[0].widget.layoutobject.y}")

        for i, menuitem in enumerate(menu_items):
            self.add_child(menuitem.widget, cancel_recalculate=True)
            if i != len(menu_items)-1:
                self.add_child(_MenuSep(), cancel_recalculate=True)

    def render(self, window: pygame.SurfaceType):
        pygame.draw.rect(window, c_primary, self.layoutobject.rendered.pgrect)
        super().render(window)

class ImageView(Widget):
    def __init__(self, *, image: pygame.Surface = None):
        super().__init__()
        self.image = image
        self.image_view = None
        self.imrect = None
    
    def set_image(self, image: pygame.Surface = None):
        self.image = image
        self.imrect = None
        self.after_layout_recalculation()

    def after_layout_recalculation(self):
        if self.image is None:
            self.image_view = BuildContext().get_font(_scale(64), "bold").render("No Image", True, c_disabledtext)
        else:
            self.image_view = pygame.transform.smoothscale(self.image, self.image.get_rect().fit(self.layoutobject.rendered.pgrect).size)
        self.imrect = self.image_view.get_rect()
        self.imrect.center = self.layoutobject.rendered.pgrect.center
    
    def render(self, window: pygame.Surface):
        window.blit(self.image_view, self.imrect)

class PILImageView(ImageView):
    def __init__(self, *, image: Image.Image = None):
        self.image: Image.Image = None
        self.boundingrect: pygame.Rect = None
        super().__init__(image=image)
    
    def set_image(self, image: Image = None):
        super().set_image(image)
    
    def after_layout_recalculation(self):
        if self.image is None:
            self.image_view = BuildContext().get_font(_scale(64), "bold").render("No Image", True, c_disabledtext)
        else:
            self.image_view = pygame.transform.smoothscale(_PILImagetopgsurf(self.image), pygame.Rect((0, 0), self.image.size).fit(self.layoutobject.rendered.pgrect).size)
        self.imrect = self.image_view.get_rect()
        self.imrect.center = self.layoutobject.rendered.pgrect.center


class StatusBar(Widget):
    def __init__(self, *, status: str = ""):
        self.status = {}
        self.set_status(status=status)
        self.layoutobject = lh.LayoutObject(**_sizeargs(f"100%,{self.statussurf.get_height()+_scale(4)}"))
        
        
    def set_status(self, statuskey: str = "main", status: str = ""):
        self.status[statuskey] = status
        self._render_status()

    def _render_status(self):
        self.statussurf: pygame.Surface = BuildContext().get_font(_scale(10)).render(', '.join(self.status.values()), True, c_primarytext)

    def unset(self, statuskey: str):
        if statuskey in self.status:
            del self.status[statuskey]
            self._render_status()


    def render(self, window: pygame.SurfaceType):
        pygame.draw.rect(window, c_primary, self.layoutobject.rendered.pgrect)
        window.blit(self.statussurf, self.layoutobject.rendered.with_offset(x=_scale(4), y=_scale(2)))


class PillButton(Button):
    def __init__(self, *, label: str = "", disabled: bool = False, action: Callable, hsize: str = None):
        super().__init__()
        self.action = action
        self.disabled = disabled
        self.labelstr = label
        self.labelsurf = BuildContext().get_font(_scale(16), "bold").render(label, True, c_disabledtext if disabled else c_accenttext)
        self.labelsurfrect = self.labelsurf.get_rect()

        if hsize is None:
            hsize = self.labelsurf.get_width()+_scale(40)

        self.layoutobject = lh.LayoutObject(**_sizeargs(f"{hsize},{_scale(40)}"))
        self._hoversurf: pygame.Surface = None
        self._pressedsurf: pygame.Surface = None

    def after_layout_recalculation(self):
        self._hoversurf = pygame.Surface((self.layoutobject.rendered.dim[0], self.layoutobject.rendered.dim[1]), pygame.SRCALPHA)
        self._pressedsurf = pygame.Surface(self._hoversurf.get_size(), pygame.SRCALPHA)
        self.labelsurfrect.center = self.layoutobject.rendered.pgrect.center
        self._hoversurf.fill((0, 0, 0, 0))
        self._pressedsurf.fill((0, 0, 0, 0))
        self._drawshape(self._hoversurf, c_accent, self.layoutobject.rendered.with_poszero())
        mask = pygame.mask.from_surface(self._hoversurf)
        mask.to_surface(self._hoversurf, setcolor=(0, 0, 0, 30), unsetcolor=(0, 0, 0, 0))
        mask.to_surface(self._pressedsurf, setcolor=(0, 0, 0, 50), unsetcolor=(0, 0, 0, 0))
        
    def set_disabled(self, disabled: bool):
        super().set_disabled(disabled)
        self.labelsurf = BuildContext().get_font(_scale(16), "bold").render(self.labelstr, True, c_disabledtext if disabled else c_accenttext)

    def render(self, window: pygame.SurfaceType):
        self._drawshape(window, c_disabled if self.disabled else c_accent, self.layoutobject.rendered)
        window.blit(self.labelsurf, self.labelsurfrect)
        if not self.disabled:
            if self.pressed:
                window.blit(self._pressedsurf, self.layoutobject.rendered.pos)
            elif self.hovering:
                window.blit(self._hoversurf, self.layoutobject.rendered.pos)

    def _drawshape(self, window: pygame.SurfaceType, color: Tuple[int, int, int], renderedlayoutobj: lh.RenderedLayoutObject):
        scaledval = _scale(40)
        pygame.gfxdraw.aacircle(window, *renderedlayoutobj.with_offset(x=scaledval//2, y=scaledval//2), scaledval//2, color)
        pygame.gfxdraw.aacircle(window, *renderedlayoutobj.with_offset(x=renderedlayoutobj.dim[0]-scaledval//2, y=scaledval//2), scaledval//2, color)
        pygame.gfxdraw.filled_circle(window, *renderedlayoutobj.with_offset(x=scaledval//2, y=scaledval//2), scaledval//2, color)
        pygame.gfxdraw.filled_circle(window, *renderedlayoutobj.with_offset(x=renderedlayoutobj.dim[0]-scaledval//2, y=scaledval//2), scaledval//2, color)
        pygame.gfxdraw.box(window, (renderedlayoutobj.with_offset(x=scaledval//2), (renderedlayoutobj.dim[0]-scaledval, (scaledval//2)*2+1)), color)


class Spacer(Widget):
    def __init__(self, size: str = ',') -> None:
        super().__init__()
        self.layoutobject = lh.LayoutObject(**_sizeargs(size))
        
    def render(self, window):
        pass

class Slider(Button):
    def __init__(self, *, disabled: bool = False, on_change: Callable = lambda: None) -> None:
        super().__init__()
        self.value = 0
        self.layoutobject = lh.LayoutObject(**_sizeargs(f"100%,{_scale(10)}"))
        self.lastknownhoverpos = (0, 0)
        self.disabled = disabled
        self.on_change = on_change
    
    def render(self, window: pygame.Surface):
        if self.pressed and not self.disabled:
            val = self.value
            xval = self.lastknownhoverpos[0] - self.layoutobject.rendered.pos[0]  # offset it to local
            xval -= _scale(5) # offset it to start of the line
            width = self.layoutobject.rendered.dim[0] - _scale(5)  # to account for early stop
            self.value = 100*(xval/width)
            if xval/width > 1:
                self.value = 100
            elif xval/width < 0:
                self.value = 0

            if val != self.value:
                self.on_change(self)
            

        if self.value > 100:
            self.value = 100
        if self.value < 0:
            self.value = 0

        pygame.draw.line(window, c_disabled, self.layoutobject.rendered.with_offset(x=_scale(5), y=_scale(5)), self.layoutobject.rendered.with_offset(x=self.layoutobject.rendered.dim[0]-_scale(5), y=_scale(5)), _scale(4))
        if self.value != 0:
            pygame.draw.line(window, c_accent, self.layoutobject.rendered.with_offset(x=_scale(5), y=_scale(5)), self.layoutobject.rendered.with_offset(x=_scale(5)+int((self.value/100)*(self.layoutobject.rendered.dim[0]-_scale(10))), y=_scale(5)), _scale(4))

        pygame.gfxdraw.aacircle(window, *self.layoutobject.rendered.with_offset(x=_scale(5)+int((self.value/100)*(self.layoutobject.rendered.dim[0]-_scale(10))), y=_scale(5)), _scale(5), c_disabledtext if self.disabled else c_accent)
        pygame.gfxdraw.filled_circle(window, *self.layoutobject.rendered.with_offset(x=_scale(5)+int((self.value/100)*(self.layoutobject.rendered.dim[0]-_scale(10))), y=_scale(5)), _scale(5), c_disabledtext if self.disabled else c_accent)

    def handle_mouse_movement(self, pos: Tuple[int, int]):
        self.lastknownhoverpos = pos
        return super().handle_mouse_movement(pos)

    def get_value(self) -> float:
        return float(self.value)

    def set_value(self, val: float):
        self.value = val

class Label(Widget):
    def __init__(self, text: str, size: int, color: Tuple[int, int, int], variant: str = "medium") -> None:
        super().__init__()
        self.text = text
        self.textsurf = BuildContext().get_font(_scale(size), variant=variant).render(text, True, color)
        self.layoutobject = lh.LayoutObject(**_sizeargs(f"{self.textsurf.get_width()},{self.textsurf.get_height()}"))
    
    def render(self, window: pygame.Surface):
        window.blit(self.textsurf, self.layoutobject.rendered.pos)


class NotificationPill(Widget):
    def __init__(self, notification: str, on_destroy: Callable = lambda self, args: None, on_destroy_args = []) -> None:
        super().__init__()

        self.layoutobject = lh.LayoutObject(x=0,y=0)
        self.notificationsurf = BuildContext().get_font(_scale(12)).render(notification, True, c_windowtext)
        self._animationtime = 45
        self._currenttime = 0
        self._notificationlength = len(notification)*4
        self._animationendpoint = self._animationtime+self._notificationlength
        self._rendersurf = pygame.Surface((self.notificationsurf.get_width()+_scale(30), _scale(30)), pygame.SRCALPHA)
        self._rendersurf.fill((0, 0, 0, 0))
        
        self._shapesurf = pygame.Surface(self._rendersurf.get_size(), pygame.SRCALPHA)
        self._shapesurf.fill((0, 0, 0, 0))
        self._shapesurf.set_alpha(200)
        pygame.gfxdraw.aacircle(self._shapesurf, _scale(30)//2, _scale(30)//2, _scale(30)//2, (0, 0, 0))
        pygame.gfxdraw.filled_circle(self._shapesurf, _scale(30)//2, _scale(30)//2, _scale(30)//2, (0, 0, 0))

        pygame.gfxdraw.aacircle(self._shapesurf, _scale(15)+self.notificationsurf.get_width(), _scale(30)//2, _scale(30)//2, (0, 0, 0))
        pygame.gfxdraw.filled_circle(self._shapesurf, _scale(15)+self.notificationsurf.get_width(), _scale(30)//2, _scale(30)//2, (0, 0, 0))
        
        self._shapesurf.fill((0, 0, 0), (_scale(15), 0, self.notificationsurf.get_width(), self._shapesurf.get_height()))
        
        self._rendersurf.blit(self._shapesurf, (0, 0))
        notificationsurfrect = self.notificationsurf.get_rect()
        notificationsurfrect.center = self._rendersurf.get_rect().center
        self._rendersurf.blit(self.notificationsurf, notificationsurfrect)
        self.on_destroy = on_destroy
        self.on_destroy_args = on_destroy_args
        self.on_destroy_called = False

    def render(self, window: pygame.Surface):
        rendersurfrect = self._rendersurf.get_rect()
        rendersurfrect.centerx = window.get_rect().centerx
        if self._currenttime <= self._animationtime:
            rendersurfrect.y = window.get_rect().bottom -_scale(30+math.sin((self._currenttime/self._animationtime)*(math.pi/2))*50)
            self._rendersurf.set_alpha(int((self._currenttime/self._animationtime)*256))
        elif self._currenttime >= self._animationendpoint:
            self._rendersurf.set_alpha(int(((self._animationtime-(self._currenttime-self._animationendpoint))/self._animationtime)*256))
            rendersurfrect.y = window.get_rect().bottom -_scale(30+math.sin(((self._animationtime-(self._currenttime-self._animationendpoint))/self._animationtime)*(math.pi/2))*50)
        else:
            rendersurfrect.y = window.get_rect().bottom -_scale(80)

        window.blit(self._rendersurf, rendersurfrect)
        
        if self._animationendpoint+self._animationtime >= self._currenttime:
            self._currenttime += 1
        else:
            if not self.on_destroy_called:
                self.on_destroy(self, self.on_destroy_args)
                self.on_destroy_called = True

class Stack(WidgetWithChildren):
    def __init__(self, *, children: List[Widget] = None, xalign: lh.LayoutCrossAxisAlignment= lh.LayoutCrossAxisAlignment.START, yalign: lh.LayoutCrossAxisAlignment = lh.LayoutCrossAxisAlignment.START, size: str = ",") -> None:
        super().__init__()
        self.layoutobject = lh.LayoutObjectStack(**_sizeargs(size), xalign=xalign, yalign=yalign)
        if children is None:
            children = []

        for child in children:
            self.add_child(child, cancel_recalculate=True)


    def render(self, window: pygame.Surface):
        for x in self.children:
            x.render(window)
    
    def add_child(self, child: Widget, *, cancel_recalculate: bool = False):
        super().add_child(child)
        self.layoutobject.add(child.layoutobject)
        if not cancel_recalculate:
            self.recalculate_layout()

    def insert_child(self, position: int, child: Widget, *, cancel_recalculate: bool = False):
        super().insert_child(position, child)
        self.layoutobject.insert(position, child.layoutobject)
        if not cancel_recalculate:
            self.recalculate_layout()

    def remove_child(self, position: int, *, cancel_recalculate: bool = False):
        super().remove_child(position)
        self.layoutobject.remove(position)
        if not cancel_recalculate:
            self.recalculate_layout()

    def handle_mouse_down(self, pos: Tuple[int, int]) -> bool:
        for child in self.children:
            child.handle_mouse_down(pos)
        return False
    
    def handle_mouse_movement(self, pos: Tuple[int, int]) -> bool:
        for child in self.children:
            child.handle_mouse_movement(pos)
        return False

    def handle_mouse_up(self, pos: Tuple[int, int]) -> bool:
        for child in self.children:
            child.handle_mouse_up(pos)
        return False

class Container(WidgetWithChild):
    def __init__(self, *, child: Widget = None, size: str = ",") -> None:
        super().__init__()
        self.layoutobject: lh.LayoutObjectStack = lh.LayoutObjectStack(**_sizeargs(size))
        self.child = child
        if self.child is not None:
            self.layoutobject.add(self.child.layoutobject)

    def render(self, window: pygame.SurfaceType):
        if self.child is not None:
            self.child.render(window)

    def set_child(self, child: Widget = None):
        self.child = child
        if len(self.layoutobject.children) > 0:
            self.layoutobject.remove(0)
        if self.child is not None:
            self.layoutobject.add(self.child.layoutobject)

class CropView(Container, Button):
    def __init__(self, *, child: Widget = None, size: str = ",") -> None:
        super().__init__(child=child, size=size)
        self.boxrect: pygame.Rect = None
        self.boxrectoriginal: pygame.Rect = None
        self.boxrectdarkensurf: pygame.Surface = None
        self.visible = False

        self.cropping_attr = None

    def get_crop_ratios(self):
        boxrectzero_offset = self.boxrect.copy()
        boxrectzero_offset.top -= self.boxrectoriginal.top
        boxrectzero_offset.left -= self.boxrectoriginal.left
        boxrectoriginalzero_offset = self.boxrectoriginal.copy()
        boxrectoriginalzero_offset.topleft = (0, 0)
        
        leftratio = boxrectzero_offset.left / boxrectoriginalzero_offset.w
        rightratio = (boxrectoriginalzero_offset.right-boxrectzero_offset.right) / boxrectoriginalzero_offset.w
        topratio = boxrectzero_offset.top  / boxrectoriginalzero_offset.h
        bottomratio = (boxrectoriginalzero_offset.bottom-boxrectzero_offset.bottom) / boxrectoriginalzero_offset.h

        return (leftratio, topratio, rightratio, bottomratio)

    def after_layout_recalculation(self):
        super().after_layout_recalculation()
        newboxrect = self.child.imrect.copy()
        
        if self.boxrect is None:
            self.boxrect = self.child.imrect.copy()
            self.boxrectoriginal = newboxrect
        scalefactorx = newboxrect.w / self.boxrectoriginal.w
        scalefactory = newboxrect.h / self.boxrectoriginal.h

        self.boxrect.w *= scalefactorx
        self.boxrect.h *= scalefactory

        self.boxrect.left = (self.boxrect.left-self.boxrectoriginal.left)*scalefactorx+newboxrect.left
        self.boxrect.top = (self.boxrect.top-self.boxrectoriginal.top)*scalefactory+newboxrect.top


        br = pygame.Rect(0, 0, _scale(20), _scale(20))
        br.bottomright = self.boxrect.bottomright
        self._br = br

        bl = pygame.Rect(0, 0, _scale(20), _scale(20))
        bl.bottomleft = self.boxrect.bottomleft
        self._bl = bl

        tr = pygame.Rect(0, 0, _scale(20), _scale(20))
        tr.topright = self.boxrect.topright
        self._tr = tr

        tl = pygame.Rect(self.boxrect.topleft, (_scale(20), _scale(20)))
        self._tl = tl

        self.boxrectoriginal = newboxrect

        self.boxrectdarkensurf = pygame.Surface(self.boxrectoriginal.size, pygame.SRCALPHA)

    
    def render(self, window: pygame.SurfaceType):
        dims = super().render(window)
        
        if self.visible:
            br = pygame.Rect(0, 0, _scale(15), _scale(15))
            br.bottomright = self.boxrect.bottomright
            self._br = br

            bl = pygame.Rect(0, 0, _scale(15), _scale(15))
            bl.bottomleft = self.boxrect.bottomleft
            self._bl = bl

            tr = pygame.Rect(0, 0, _scale(15), _scale(15))
            tr.topright = self.boxrect.topright
            self._tr = tr

            tl = pygame.Rect(self.boxrect.topleft, (_scale(15), _scale(15)))
            self._tl = tl

            boxrectzero_offset = self.boxrect.copy()
            boxrectzero_offset.top -= self.boxrectoriginal.top
            boxrectzero_offset.left -= self.boxrectoriginal.left

            self.boxrectdarkensurf.fill((0, 0, 0, 128))
            self.boxrectdarkensurf.fill((0, 0, 0, 0), boxrectzero_offset)#, pygame.BLENDMODE_NONE)

            window.blit(self.boxrectdarkensurf, self.boxrectoriginal)

            self.prevhovering = self.hovering
            

            pygame.draw.rect(window, c_accent, tl)
            pygame.draw.rect(window, c_accent, bl)
            pygame.draw.rect(window, c_accent, tr)
            pygame.draw.rect(window, c_accent, br)
            
            pygame.draw.rect(window, c_white, self.boxrect, _scale(2))
            pygame.draw.line(window, c_white, (self.boxrect.left+self.boxrect.w//3, self.boxrect.top), (self.boxrect.left+self.boxrect.w//3, self.boxrect.bottom), _scale(1))
            pygame.draw.line(window, c_white, (self.boxrect.left+2*self.boxrect.w//3, self.boxrect.top), (self.boxrect.left+2*self.boxrect.w//3, self.boxrect.bottom), _scale(1))
            pygame.draw.line(window, c_white, (self.boxrect.left, self.boxrect.top+self.boxrect.h//3), (self.boxrect.right, self.boxrect.top+self.boxrect.h//3), _scale(1))
            pygame.draw.line(window, c_white, (self.boxrect.left, self.boxrect.top+2*self.boxrect.h//3), (self.boxrect.right, self.boxrect.top+2*self.boxrect.h//3), _scale(1))

            
        return dims
    
    def handle_mouse_movement(self, pos: Tuple[int, int]) -> bool:
        self.prevhovering = self.hovering
        Button.handle_mouse_movement(self, pos, False)
        rval = False

        if self.visible:
            if self._bl.collidepoint(pos) or self._tr.collidepoint(pos):
                pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_SIZENESW)
                rval = True
            elif self._br.collidepoint(pos) or self._tl.collidepoint(pos):
                pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_SIZENWSE)
                rval = True
            elif self.prevhovering:
                pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_ARROW)
                rval = True

            if self.cropping_attr == "tl":
                if self.boxrect.bottom - pos[1] < _scale(50):  # Top Limitter
                    self.boxrect.top = self.boxrect.bottom-_scale(50)
                    self.boxrect.h = _scale(50)
                elif pos[1] < self.boxrectoriginal.top:
                    bottom = self.boxrect.bottom
                    self.boxrect.top = self.boxrectoriginal.top
                    self.boxrect.h = bottom - self.boxrect.top
                else:
                    bottom = self.boxrect.bottom
                    self.boxrect.top = pos[1]
                    self.boxrect.h = bottom - self.boxrect.top

                if self.boxrect.right - pos[0] < _scale(50):  # Left Limitter
                    self.boxrect.left = self.boxrect.right-_scale(50)
                    self.boxrect.w = _scale(50)
                elif pos[0] < self.boxrectoriginal.left:
                    right = self.boxrect.right
                    self.boxrect.left = self.boxrectoriginal.left
                    self.boxrect.w = right - self.boxrect.left
                else:
                    right = self.boxrect.right
                    self.boxrect.left = pos[0]
                    self.boxrect.w = right - self.boxrect.left

            elif self.cropping_attr == "tr":
                if self.boxrect.bottom - pos[1] < _scale(50):  # Top Limitter
                    self.boxrect.top = self.boxrect.bottom-_scale(50)
                    self.boxrect.h = _scale(50)
                elif pos[1] < self.boxrectoriginal.top:
                    bottom = self.boxrect.bottom
                    self.boxrect.top = self.boxrectoriginal.top
                    self.boxrect.h = bottom - self.boxrect.top
                else:
                    bottom = self.boxrect.bottom
                    self.boxrect.top = pos[1]
                    self.boxrect.h = bottom - self.boxrect.top

                if pos[0] - self.boxrect.left < _scale(50):  # Right Limitter
                    self.boxrect.w = _scale(50)
                elif pos[0] > self.boxrectoriginal.right:
                    left = self.boxrect.left
                    self.boxrect.w = self.boxrectoriginal.right - left
                    self.boxrect.right = self.boxrectoriginal.right
                else:
                    left = self.boxrect.left
                    self.boxrect.w = pos[0] - left
                    self.boxrect.right = pos[0]

            elif self.cropping_attr == "bl":
                if pos[1] - self.boxrect.top < _scale(50):  # Bottom Limitter
                    self.boxrect.h = _scale(50)
                elif pos[1] > self.boxrectoriginal.bottom:
                    top = self.boxrect.top
                    self.boxrect.h = self.boxrectoriginal.bottom - top
                    self.boxrect.bottom = self.boxrectoriginal.bottom
                else:
                    top = self.boxrect.top
                    self.boxrect.h = pos[1] - top
                    self.boxrect.bottom = pos[1]

                if self.boxrect.right - pos[0] < _scale(50):  # Left Limitter
                    self.boxrect.left = self.boxrect.right-_scale(50)
                    self.boxrect.w = _scale(50)
                elif pos[0] < self.boxrectoriginal.left:
                    right = self.boxrect.right
                    self.boxrect.left = self.boxrectoriginal.left
                    self.boxrect.w = right - self.boxrect.left
                else:
                    right = self.boxrect.right
                    self.boxrect.left = pos[0]
                    self.boxrect.w = right - self.boxrect.left

            elif self.cropping_attr == "br":
                if pos[1] - self.boxrect.top < _scale(50):  # Bottom Limitter
                    self.boxrect.h = _scale(50)
                elif pos[1] > self.boxrectoriginal.bottom:
                    top = self.boxrect.top
                    self.boxrect.h = self.boxrectoriginal.bottom - top
                    self.boxrect.bottom = self.boxrectoriginal.bottom
                else:
                    top = self.boxrect.top
                    self.boxrect.h = pos[1] - top
                    self.boxrect.bottom = pos[1]

                if pos[0] - self.boxrect.left < _scale(50):  # Right Limitter
                    self.boxrect.w = _scale(50)
                elif pos[0] > self.boxrectoriginal.right:
                    left = self.boxrect.left
                    self.boxrect.w = self.boxrectoriginal.right - left
                    self.boxrect.right = self.boxrectoriginal.right
                else:
                    left = self.boxrect.left
                    self.boxrect.w = pos[0] - left
                    self.boxrect.right = pos[0]

        return rval
    
    def handle_mouse_down(self, pos: Tuple[int, int]):
        Button.handle_mouse_down(self, pos)
        if self._bl.collidepoint(pos):
            self.cropping_attr = "bl"
            return True
        elif self._br.collidepoint(pos):
            self.cropping_attr = "br"
            return True
        elif self._tr.collidepoint(pos):
            self.cropping_attr = "tr"
            return True
        elif self._tl.collidepoint(pos):
            self.cropping_attr = "tl"
            return True
        else:
            self.cropping_attr = None
    
    def handle_mouse_up(self, pos: Tuple[int, int]):
        Button.handle_mouse_up(self, pos)
        self.cropping_attr = None

    def showcropview(self):
        if self.child.image is not None:
            self.visible = True

    def hidecropview(self):
        self.visible = False
        self.boxrect = self.boxrectoriginal.copy()


class Notifier(Column):
    def __init__(self):
        super().__init__()
        self.layoutobject.x = 0
        self.layoutobject.y = 0
        self.layoutobject.unit_x = lh.LayoutUnit.ABSOLUTE
        self.layoutobject.unit_y = lh.LayoutUnit.ABSOLUTE

    def notify(self, notifcation_content: str, on_destroy_callback: Callable = lambda: None):
        def on_destroy(self, args):
            on_destroy_callback()
            for i, x in enumerate(args[0].children):
                if x == self:
                    args[0].remove_child(i, cancel_recalculate=True)
        self.add_child(NotificationPill(notifcation_content, on_destroy, [self]), cancel_recalculate=True)


def HPadding(left: int = 0, right: int = None, *, child: Widget):
    """
    Warning: the child must have absolute sized y-axis
    """

    assert child.layoutobject.unit_y == lh.LayoutUnit.ABSOLUTE
    if right is None:
        right = left
    return Row(
        children=[
            Spacer(f"{left},0"),
            child,
            Spacer(f"{right},0")
        ],
        size = f",{child.layoutobject.y}"
    )

def VPadding(top: int = 0, bottom: int = None, *, child: Widget):
    """
    Warning: the child must have absolute sized x-axis
    """

    assert child.layoutobject.unit_x == lh.LayoutUnit.ABSOLUTE
    if bottom is None:
        bottom = top
    return Row(
        children=[
            Spacer(f"0,{top}"),
            child,
            Spacer(f"0,{bottom}")
        ],
        size = f"{child.layoutobject.x},"
    )

class Icon():
    def __init__(self, iconimage: pygame.Surface) -> None:
        if iconimage.get_height() != iconimage.get_width():
            raise ValueError("Icons can only be square")
        
        self.iconimage = iconimage
        self.buttonradius = iconimage.get_width()/math.sin(math.pi/4)

    def get_rect(self) -> pygame.Rect:
        return self.iconimage.get_rect()

def _render_icon(icon: int, size: int, color):
    font = BuildContext().get_font(size, "round", "material-symbols")
    render = font.render(chr(icon), True, color)
    real_render = render.get_bounding_rect()
    real_render_surf = pygame.Surface(real_render.size, pygame.SRCALPHA)
    real_render_surf.blit(render, (0, 0), real_render)
    return real_render_surf

class Icons:
    @staticmethod
    @lru_cache()
    def cross(size: int, color):
        return Icon(_render_icon(0xe5cd, size, color))

class IconPosition(enum.Enum):
    TOPLEFT = 0
    TOPRIGHT = 1
    BOTTOMLEFT = 2
    BOTTOMRIGHT = 3
    TOP = 4
    LEFT = 5
    RIGHT = 6
    BOTTOM = 7
    CENTER = 8


class IconButton(Button):
    def __init__(self, *, icon: Icon, position: IconPosition = IconPosition.TOPRIGHT, xpad: int = 0, ypad: int = 0, disabled: bool = False, action: Callable = lambda: None) -> None:
        super().__init__()
        self.action = action
        self.layoutobject = lh.LayoutObject(**_sizeargs(","))
        self.icon = icon
        self.position = position
        self.iconrect = icon.get_rect()
        self.ypad = ypad
        self.xpad = xpad
        self.buttonrect = icon.get_rect()
        self.buttonsurf = pygame.Surface((self.icon.buttonradius*2, self.icon.buttonradius*2), pygame.SRCALPHA)
        self.disabled = disabled

    def after_layout_recalculation(self):
        self.buttonrect.w = self.icon.buttonradius*2
        self.buttonrect.h = self.icon.buttonradius*2
        
        if self.position == IconPosition.TOPLEFT:
            self.buttonrect.topleft = (self.layoutobject.rendered.pos[0] + self.xpad, self.layoutobject.rendered.pos[1] + self.ypad)
        elif self.position == IconPosition.TOPRIGHT:
            self.buttonrect.topright = (self.layoutobject.rendered.pos[0] + self.layoutobject.rendered.dim[0] - self.xpad, self.layoutobject.rendered.pos[1] + self.ypad)
        elif self.position == IconPosition.BOTTOMLEFT:
            self.buttonrect.bottomleft = (self.layoutobject.rendered.pos[0] + self.xpad, self.layoutobject.rendered.pos[1] + self.layoutobject.rendered.dim[1] - self.ypad)
        elif self.position == IconPosition.BOTTOMRIGHT:
            self.buttonrect.bottomright = (self.layoutobject.rendered.pos[0] + self.layoutobject.rendered.dim[0] - self.xpad, self.layoutobject.rendered.pos[1] + self.layoutobject.rendered.dim[1] - self.ypad)
        elif self.position == IconPosition.TOP:
            self.buttonrect.centerx = self.layoutobject.rendered.pgrect.centerx
            self.buttonrect.top = self.layoutobject.rendered.pos[1] + self.ypad
        elif self.position == IconPosition.LEFT:
            self.buttonrect.centery = self.layoutobject.rendered.pgrect.centery
            self.buttonrect.left = self.layoutobject.rendered.pos[0] + self.xpad
        elif self.position == IconPosition.RIGHT:
            self.buttonrect.centery = self.layoutobject.rendered.pgrect.centery
            self.buttonrect.right = self.layoutobject.rendered.pos[0] + self.layoutobject.rendered.dim[0] - self.xpad
        elif self.position == IconPosition.BOTTOM:
            self.buttonrect.centerx = self.layoutobject.rendered.pgrect.centerx
            self.buttonrect.bottom = self.layoutobject.rendered.pos[1] + self.layoutobject.rendered.dim[1] - self.ypad
        elif self.position == IconPosition.CENTER:
            self.buttonrect.center = self.layoutobject.rendered.pgrect.center
            
        self.iconrect.center = self.buttonrect.center

        self.buttonsurf.fill((0, 0, 0, 0))
        
        pygame.gfxdraw.aacircle(self.buttonsurf, *(int(self.icon.buttonradius),)*2, int(self.icon.buttonradius)-1, (0, 0, 0))
        pygame.gfxdraw.filled_circle(self.buttonsurf, *(int(self.icon.buttonradius),)*2, int(self.icon.buttonradius)-1, (0, 0, 0))
        
    def render(self, window: pygame.SurfaceType):
        if not self.disabled:
            if self.pressed:
                self.buttonsurf.set_alpha(227)
            elif self.hovering:
                self.buttonsurf.set_alpha(177)
            else:
                self.buttonsurf.set_alpha(127)

            window.blit(self.buttonsurf, self.buttonrect)
            window.blit(self.icon.iconimage, self.iconrect)

    def handle_mouse_down(self, pos: Tuple[int, int]):
        if self.buttonrect.collidepoint(pos):
            self.pressed = True
            return True
        return False
    
    def handle_mouse_up(self, pos: Tuple[int, int]):
        if self.buttonrect.collidepoint(pos):
            if self.pressed and not self.disabled:
                self.pressed = False
                self.action()
                return True
        self.pressed = False
        return False
    
    def handle_mouse_movement(self, pos: Tuple[int, int], changecursor: bool = True):
        if self.buttonrect.collidepoint(pos):
            self.hovering = True
            if changecursor:
                if not self.disabled:
                    pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_HAND)
            return True
        else:
            if self.hovering:
                if changecursor:
                    pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_ARROW)
            self.hovering = False
        return False
        
class AnchorToImageView(WidgetWithChild):
    def __init__(self, image_view: ImageView, child: Widget) -> None:
        self.imview = image_view
        self.layoutobject = lh.LayoutObjectStack()
        self.set_child(child)

    def set_child(self, child: Widget = None):
        if child is None:
            self.child = None
            if len(self.layoutobject.children) > 0:
                self.layoutobject.remove(0)
        else:
            self.child = child
            if len(self.layoutobject.children) > 0:
                self.layoutobject.remove(0)
            self.layoutobject.add(self.child.layoutobject)
    
    def after_layout_recalculation(self):
        self.layoutobject.calculate(self.imview.imrect.w, self.imview.imrect.h, self.imview.imrect.topleft)
        self.child.after_layout_recalculation()

    def render(self, window):
        self.child.render(window)
