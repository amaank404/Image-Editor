from wyper.widgets import *
from wyper.layouthandler import *
from wyper import colors
from wyper import init
from wyper import scale as _scale

import pygame
import os
import darkdetect
from PIL import Image, ImageFilter

from tkinter.filedialog import askopenfilename as _askopenfilename
from tkinter.filedialog import asksaveasfilename as _asksaveasfilename
import tkinter as tk

# import importlib
# from time import sleep
# from threading import Thread
# def reload():
#     while True:
#         print("Reload")
#         importlib.reload(colors)
#         colors.setSchemeLight()
#         sleep(1)

# Thread(target=reload, daemon=True).start()



def runapp():
    if not darkdetect.isDark():
        colors.setSchemeLight()
    else:
        colors.setSchemeDark()
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

    def tkinterwrapper(func):
        def _tkinterwrapper(*args, **kwargs):
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-alpha", 0)
            returndata = func(*args, **kwargs)
            root.destroy()
            return returndata
        return _tkinterwrapper

    askopenfilename = tkinterwrapper(_askopenfilename)
    asksaveasfilename = tkinterwrapper(_asksaveasfilename)

    def saveimage():
        imagefile = BuildContext()["imagefilepath"]
        if imagefile is None:
            notifier.notify("No image file is currently opened")
            return
        imview.image.save(imagefile)
        notifier.notify(f"Image saved to: {imagefile}")

    def saveasimage():
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
        

    def openimage(*buttons: List[Button]):
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

    def blurimage():
        if not BuildContext()["allowimagechanges"] and BuildContext()["curop"] != "blur":
            notifier.notify("Can not perform this operation while another operation is in progress")
            return
        if not blurslider.get_value() > 0:
            notifier.notify("Please set a blur value before applying this filter")
            return
        
        BuildContext()["allowimagechanges"] = True
        BuildContext()["curop"] = None
        val = blurslider.get_value()
        blurslider.set_value(0)
        statusbar.unset("preview")
        
        imview.image = imview.image.filter(ImageFilter.GaussianBlur(radius=val))

        cancelbutton.set_disabled(True)
        notifier.notify("Applied Blur")

    def cancelop():
        BuildContext()["allowimagechanges"] = True

        if BuildContext()["curop"] == "crop":
            cropview.hidecropview()
        elif BuildContext()["curop"] == "blur":
            imview.image = imview.original_image
            del imview.original_image
            statusbar.unset("preview")
            imview.after_layout_recalculation()
            blurslider.set_value(0)
        elif BuildContext()["curop"] in filterbuttonops:
            imview.image = imview.original_image
            del imview.original_image
            statusbar.unset("preview")
            imview.after_layout_recalculation()

        cancelbutton.set_disabled(True)

        BuildContext()["curop"] = None

    def startcrop():
        
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
            cancelbutton.set_disabled()
        else:
            leftr, topr, rightr, bottomr = cropview.get_crop_ratios()
            left = imview.image.size[0]*leftr
            top = imview.image.size[1]*topr
            right = imview.image.size[0] - imview.image.size[0]*rightr
            bottom = imview.image.size[1] - imview.image.size[1]*bottomr
            cropview.hidecropview()

            cancelbutton.set_disabled(True)

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

    def filtersliderchange(self: Slider, filter: str,  attr: str, filterobj: ImageFilter):
        if not BuildContext()["allowimagechanges"] and BuildContext()["curop"] != filter:
            self.set_value(0)
            if not BuildContext()["filternotification"]:
                set_filter_notification(True)
                notifier.notify(f"Can't preview {filter} while another operation is in progress", lambda: set_filter_notification(False))
            return
        
        if BuildContext()["allowimagechanges"]:
            cancelbutton.set_disabled()
            imview.original_image = imview.image.copy()
        imview.image = imview.original_image.filter(filterobj(**{attr: int(self.get_value())}))
        statusbar.set_status("preview", f"Previewing {filter.title()}")
        imview.after_layout_recalculation()
        if self.get_value() > 0:
            BuildContext()["allowimagechanges"] = False
            BuildContext()["curop"] = filter
        elif self.get_value() == 0:
            if BuildContext()["curop"] == filter:
                cancelbutton.set_disabled(True)
                imview.image = imview.original_image
                del imview.original_image
                statusbar.unset("preview")
                BuildContext()["allowimagechanges"] = True
                BuildContext()["curop"] = None
                imview.after_layout_recalculation()

    def builtinfilter(filter, fname: str, sname: str = None):
        if sname is None:
            sname = fname
        if not BuildContext()["allowimagechanges"] and BuildContext()["curop"] != fname:
            notifier.notify(f"Can't preview '{sname}' while another operation is in progress")

        statusbar.set_status("preview", "Previewing "+sname)
        
        if BuildContext()["allowimagechanges"]:
            cancelbutton.set_disabled(False)
            imview.original_image = imview.image.copy()
            imview.image = filter(imview.image)
            imview.after_layout_recalculation()
            BuildContext()["allowimagechanges"] = False
            BuildContext()["curop"] = fname
        else:
            cancelbutton.set_disabled(True)
            del imview.original_image
            statusbar.unset("preview")
            BuildContext()["allowimagechanges"] = True
            BuildContext()["curop"] = None


    filterbuttons = []
    filterbuttonops = []

    def filterbutton(filter, fname, sname = None):
        button = PillButton(
            label=sname,
            action=lambda: builtinfilter(filter, fname, sname), 
            disabled=True,
            hsize="1f",
        )
        filterbuttons.append(button)
        filterbuttonops.append(fname)

        return (Spacer(f"0,{_scale(8)}"),
        HPadding(
            _scale(8),
            child = (button) 
        ))
    
    def filterlambda(filter):
        return lambda image: image.filter(filter)

    main_widget = AppRoot(
        "Image Editor", pygame.Surface((32, 32)), fps=90, init_resolution=(1000, 600),
        child = Column(
            children=[
                MenuBar(
                    menu_items=[
                        MenuItem("Open Image", lambda: openimage(cropbutton, blurbutton, blurslider, *filterbuttons)),
                        MenuItem("Save", lambda: saveimage()),
                        MenuItem("Save As", lambda: saveasimage())
                    ]
                ),
                Row(
                    children=[
                        Spacer(f"{_scale(10)},0"),
                        containerstack := Stack(children=[
                            cropview := CropView(
                                child= (imview := PILImageView())
                            ),
                            AnchorToImageView(
                                imview, 
                                cancelbutton := IconButton(
                                    icon=Icons.cross(_scale(20), colors.c_iconbutton),
                                    ypad=_scale(10),
                                    xpad=_scale(10),
                                    disabled=True,
                                    action=lambda: cancelop()
                                )
                            )
                        ]),
                        Spacer(f"{_scale(10)},0"),
                        VSep(),
                        Column(
                            size = "20%,",
                            crossalign=LayoutCrossAxisAlignment.CENTER,
                            children=[
                                Spacer(f"0,{_scale(8)}"),
                                HPadding(
                                    _scale(8),
                                    child = (cropbutton := PillButton(
                                        label="Crop",
                                        action=lambda: startcrop(), 
                                        disabled=True,
                                        hsize="1f",
                                    ))
                                ),
                                Spacer(f"0,{_scale(8)}"),
                                HSep(8),
                                Spacer(f"0,{_scale(8)}"),
                                Label("Filters", 20, colors.c_disabledtext, "bold"),
                                Spacer(f"0,{_scale(4)}"),
                                Row(
                                    crossalign = LayoutCrossAxisAlignment.CENTER,
                                    children = [
                                        Spacer(f"{_scale(8)},0"),
                                        blurbutton := PillButton(
                                            label="Blur",
                                            action=lambda: blurimage(),
                                            disabled=True
                                        ),
                                        Spacer(f"{_scale(8)},0"),
                                        blurslider := Slider(disabled=True, on_change=lambda self: filtersliderchange(self, "blur", "radius", ImageFilter.GaussianBlur)),
                                        Spacer(f"{_scale(8)},0"),
                                    ],
                                    size = f",{blurbutton.layoutobject.y}",
                                ),
                                *filterbutton(filterlambda(ImageFilter.FIND_EDGES), "findedge", "Find Edges"),
                                *filterbutton(filterlambda(ImageFilter.CONTOUR), "contour", "Contour"),
                                *filterbutton(filterlambda(ImageFilter.SMOOTH), "smooth", "Smooth"),
                                *filterbutton(filterlambda(ImageFilter.SHARPEN), "sharpen", "Sharpen"),
                                *filterbutton(filterlambda(ImageFilter.EMBOSS), "emboss", "Emboss"),
                                *filterbutton(filterlambda(ImageFilter.EDGE_ENHANCE), "edgeenhance", "Edge Enhance"),
                                *filterbutton(filterlambda(ImageFilter.DETAIL), "detail", "Detail"),
                            ]
                        ),
                        VSep(),
                        Column(
                            size = "20%,",
                            crossalign=LayoutCrossAxisAlignment.CENTER,
                            children=[]
                        )
                    ],
                ),
                statusbar := StatusBar(status="Image Editor, Load an image to edit it"),
                notifier := Notifier()
            ]
        )
    )

    main_widget.run(debug=True)
