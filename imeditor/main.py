from .gui.widgets import *
from .gui.layouthandler import *
from .gui import init
import pygame
import os
from PIL import Image, ImageFilter

from tkinter.filedialog import askopenfilename, asksaveasfilename

from .gui.widgets import _scale

init()

exts = Image.registered_extensions()
supported_extensions_open = {ex for ex, f in exts.items() if f in Image.OPEN}
supported_extensions_save = {ex for ex, f in exts.items() if f in Image.SAVE}

filetypes = (
    ("Image File", tuple(supported_extensions_save)),
)

filetypesopen = (
    ("Image File", tuple(supported_extensions_open)),
)

BuildContext().setdefault("allowimagechanges", True)
BuildContext().setdefault("filternotification", False)

def saveimage(imview: PILImageView, notifier: Notifier):
    imagefile = BuildContext()["imagefilepath"]
    if imagefile is None:
        notifier.notify("No image file is currently opened")
        return
    imview.image.save(imagefile)
    notifier.notify(f"Image saved to: {imagefile}")

def saveasimage(imview: PILImageView, notifier: Notifier, statusbar: StatusBar):
    imagefile = BuildContext()["imagefilepath"]
    if imagefile is None:
        notifier.notify("No image file is currently opened")
        return

    imagefilenew = asksaveasfilename(
        confirmoverwrite=True,
        defaultextension=".png",
        initialdir=None if BuildContext()["imagefilepath"] is None else os.path.dirname(BuildContext()["imagefilepath"]),
        filetypes=filetypes
    )

    if not imagefilenew:
        return
    
    BuildContext()["imagefilepath"] = imagefilenew

    try:
        saveimage(imview, notifier)
    except Exception as e:
        notifier.notify(f"Error encountered while saving: {e}")
        BuildContext()["imagefilepath"] = imagefile
        return
    
    statusbar.set_status(status = f"{os.path.basename(imagefilenew)}")
    

def openimage(imview: PILImageView, statusbar: StatusBar, notifier: Notifier, containerstack: Stack, *buttons: List[Button]):
    imagefile = askopenfilename(defaultextension=".png", filetypes=filetypesopen)
    if not imagefile:
        return
    try:
        imview.set_image(pilimage := Image.open(imagefile))
    except Exception as e:
        notifier.notify(f"Error encountered while loading file: {e}")
        return
    BuildContext()["imagefilepath"] = imagefile
    statusbar.set_status(status = f"{os.path.basename(imagefile)}")
    statusbar.set_status("resolution", f"{pilimage.size[0]}x{pilimage.size[1]}px")
    for x in buttons:
        x.set_disabled(False)
    containerstack.recalculate_layout(forced=True)

def blurimage(imview: PILImageView, slider: Slider, statusbar: StatusBar, notifier: Notifier):
    if not BuildContext()["allowimagechanges"] and BuildContext()["curop"] != "blur":
        notifier.notify("Can not perform this operation while another operation is in progress")
        return
    if not slider.get_value() > 0:
        notifier.notify("Please set a blur value before applying this filter")
        return
    
    BuildContext()["allowimagechanges"] = True
    BuildContext()["curop"] = None
    val = slider.get_value()
    slider.set_value(0)
    statusbar.unset("preview")
    
    imview.image = imview.image.filter(ImageFilter.GaussianBlur(radius=val))
    notifier.notify("Applied Blur")

def startcrop(cropview: CropView, notifier: Notifier, imview: PILImageView, statusbar: StatusBar, containerstack: Stack):
    
    if not BuildContext()["allowimagechanges"] and BuildContext()["curop"] != "crop":
        notifier.notify("Can not perform this operation while another operation is in progress")
        return
    
    BuildContext()["curop"] = "crop"
    
    if not cropview.visible:
        BuildContext()["allowimagechanges"] = False
        BuildContext().setdefault("cropnotification", False)
        if not BuildContext()["cropnotification"]:
            notifier.notify("Please adjust the handles to crop the image")
            BuildContext()["cropnotification"] = True
        cropview.showcropview()
    else:
        leftr, topr, rightr, bottomr = cropview.get_crop_ratios()
        left = imview.image.size[0]*leftr
        top = imview.image.size[1]*topr
        right = imview.image.size[0] - imview.image.size[0]*rightr
        bottom = imview.image.size[1] - imview.image.size[1]*bottomr
        cropview.hidecropview()

        if right - left < 2 or bottom - top < 2:
            notifier.notify("Can't crop further, the image is too small")
        else:
            imview.image = imview.image.crop((left, top, right, bottom))
            statusbar.set_status("resolution", f"{imview.image.size[0]}x{imview.image.size[1]}px")
            containerstack.after_layout_recalculation()
        
        BuildContext()["allowimagechanges"] = True
        BuildContext()["curop"] = None

def set_filter_notification(status: bool):
    BuildContext()["filternotification"] = status

def filtersliderchange(self: Slider, filter: str, imview: PILImageView, statusbar: StatusBar, notifier: Notifier, *, attr="", filterobj: ImageFilter):
    if not BuildContext()["allowimagechanges"] and BuildContext()["curop"] != filter:
        self.set_value(0)
        if not BuildContext()["filternotification"]:
            set_filter_notification(True)
            notifier.notify(f"Can't preview {filter} while another operation is in progress", lambda: set_filter_notification(False))
        return
    
    if BuildContext()["allowimagechanges"]:
        imview.original_image = imview.image.copy()
    imview.image = imview.original_image.filter(filterobj(**{attr: int(self.get_value())}))
    statusbar.set_status("preview", f"Previewing {filter.title()}")
    imview.after_layout_recalculation()
    if self.get_value() > 0:
        BuildContext()["allowimagechanges"] = False
        BuildContext()["curop"] = filter
    elif self.get_value() == 0:
        if BuildContext()["curop"] == filter:
            imview.image = imview.original_image
            del imview.original_image
            statusbar.unset("preview")
            BuildContext()["allowimagechanges"] = True
            BuildContext()["curop"] = None
            imview.after_layout_recalculation()


def runapp():
    main_widget = AppRoot(
        "Image Editor", pygame.Surface((32, 32)), fps=90,
        child = Column(
            children=[
                MenuBar(
                    menu_items=[
                        MenuItem("Open Image", lambda: openimage(imview, statusbar, notifier, containerstack, cropbutton, blurbutton, blurslider)),
                        MenuItem("Save", lambda: saveimage(imview, notifier)),
                        MenuItem("Save As", lambda: saveasimage(imview, notifier, statusbar))
                    ]
                ),
                Row(
                    children=[
                        Spacer(f"{_scale(10)},0"),
                        containerstack := Stack(children=[
                            cropview := CropView(
                                child= (imview := PILImageView())
                            ),
                            AnchorToImageView(imview, IconButton(icon=Icons.cross(_scale(20), c_white), ypad=_scale(10), xpad=_scale(10)))
                        ]),
                        Spacer(f"{_scale(10)},0"),
                        VSep(),
                        Column(
                            size = "30%,",
                            crossalign=LayoutCrossAxisAlignment.CENTER,
                            children=[
                                Spacer(f"0,{_scale(8)}"),
                                HPadding(
                                    _scale(8),
                                    child = (cropbutton := PillButton(
                                        label="Crop",
                                        action=lambda: startcrop(cropview, notifier, imview, statusbar, containerstack), 
                                        disabled=True,
                                        hsize="1f",
                                    ))
                                ),
                                Spacer(f"0,{_scale(8)}"),
                                HSep(8),
                                Spacer(f"0,{_scale(8)}"),
                                Label("Filters", 20, c_disabledtext, "bold"),
                                Spacer(f"0,{_scale(4)}"),
                                Row(
                                    crossalign = LayoutCrossAxisAlignment.CENTER,
                                    children = [
                                        Spacer("8,0"),
                                        blurbutton := PillButton(
                                            label="Blur",
                                            action=lambda: blurimage(imview, blurslider, statusbar, notifier),
                                            disabled=True
                                        ),
                                        Spacer("16,0"),
                                        blurslider := Slider(disabled=True, on_change=lambda self: filtersliderchange(self, "blur",  imview, statusbar, notifier, attr="size", filterobj=ImageFilter.MinFilter)),
                                        Spacer("8,0"),
                                    ],
                                    size = f",{blurbutton.layoutobject.y}",
                                )
                            ]
                        )
                    ],
                ),
                statusbar := StatusBar(status="Image Editor, Load an image to edit it"),
                notifier := Notifier()
            ]
        )
    )

    main_widget.run(debug=True)