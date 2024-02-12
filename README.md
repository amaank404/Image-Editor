# A Proof of Concept Image Editor (pygame)

The following image editor is made using pygame and a custom GUI
library under the hood. The GUI library takes some inspiration from
flutter. The layout calculation part of the GUI library has been separated
into its own module. 

**Update: The GUI library has been separated from this project into its own library named wyper**

The Image editor comes with the following features:

* Automatic Dark/Light mode depending on your system settings.
* Fractional DPI Scaling GUI for crystel clear interface on even high DPI monitors
* Resizable Layout
* Interactive Image Cropping Functionality


![](scrshots/mainwindow.png)

### How it works

The gui component of this program is completely reusable and can be used to create other GUI applications. Please look at wyper library for reference.

Widgets are easy to create with only a few methods needed to be overriden.

Widgets at bare minimum need to provide `__init__` method and `render` method. Widgets if need be can change their own layoutobject as they see fit. The `after_layout_recalculation` method should be overriden if you need to preprocess or draw something after the layout is calculated. The calculated layout is stored in `self.layoutobject.rendered`.

Subclasses of `Widget` such as `WidgetWithChild` and `WidgetWithChildren` are also available for some extra methods. Other widgets can also be overriden to make changes.

LayoutObjects are used for layout positioning, sizing and calculations. These LayoutObject come in the following variations:

1. LayoutObject - A single layoutobject for widgets without children

2. LayoutObjectList - A single layoutobject that can have multiple children. These children can be any of the listed LayoutObject including list itself. Widgets such as Column, Row derive from this

3. LayoutObjectStack - A sinlge layoutobject that can have multiple children stacked on top of each other. The layoutobject does not care about overlapping and simply provides the widgets with overlay capabilities

The 2 and 3 type objects also have properties such as mainAxisAlignment and crossAxisAlignment. 

Each LayoutObject can be sized with the folowing possible units.

1. `LayoutUnit.ABSOLUTE` - This is the most basic unit and says that the size of the child is fixed

2. `LayoutUnit.PERCENTAGE` - This unit takes a percentage amount of space from the parent. A little quirk about this is that the percentages are calculated after absolute sized widgets have been allocated. Hence a 100% sized widget will occupy 100% of remaining space instead of parent space

3. `LayoutUnit.FLEX` - This unit is for distributing leftover space proportionally. Simply put, the values with this unit are proportions that the leftover space is to be distributed in after calculations for 1 and 2 type units is complete.

to calculate a tree of layout. Call the `calculate(spacex, spacey, offset)` on the parent method. The spacex is space available in x-axis and same is for spacey. Offset defines how the widgets are to be initally placed from reference. Offset for parent widget is usually set to `(0, 0)`.

Here is how the parent layoutobject for this image editor looks like:

```
LayoutObjectStack[x0, y0, w1000, h625
    LayoutObjectList[x0, y0, w1000, h625
        LayoutObjectList[x0, y0, w1000, h37
            LayoutObject[x0, y0, w154, h37],
            LayoutObject[x154, y0, w3, h37],
            LayoutObject[x157, y0, w85, h37],
            LayoutObject[x242, y0, w3, h37],
            LayoutObject[x245, y0, w114, h37],
        ],
        LayoutObjectList[x0, y37, w1000, h567
            LayoutObject[x0, y37, w12, h0],
            LayoutObjectStack[x12, y37, w682, h567
                LayoutObjectStack[x12, y37, w682, h567
                    LayoutObject[x12, y37, w682, h567],
                ],
                LayoutObjectStack[x171, y268, w364, h105
                    LayoutObject[x171, y268, w364, h105],
                ],
            ],
            LayoutObject[x694, y37, w12, h0],
            LayoutObject[x706, y37, w3, h567],
            LayoutObjectList[x709, y37, w291, h567
                LayoutObject[x854, y37, w0, h10],
                LayoutObjectList[x709, y47, w291, h50
                    LayoutObject[x709, y47, w10, h0],
                    LayoutObject[x719, y47, w271, h50],
                    LayoutObject[x990, y47, w10, h0],
                ],
                LayoutObject[x854, y97, w0, h10],
                LayoutObject[x709, y107, w291, h3],
                LayoutObject[x854, y110, w0, h10],
                LayoutObject[x816, y120, w76, h33],
                LayoutObject[x854, y153, w0, h5],
                LayoutObjectList[x709, y158, w291, h50
                    LayoutObject[x709, y183, w8, h0],
                    LayoutObject[x717, y158, w88, h50],
                    LayoutObject[x805, y183, w16, h0],
                    LayoutObject[x821, y177, w171, h12],
                    LayoutObject[x992, y183, w8, h0],
                ],
            ],
        ],
        LayoutObject[x0, y604, w1000, h21],
        LayoutObjectList[x0, y625, w0, h0],
    ],
]
```

As you can see, the calculated layout is stored as rectangles with x, y, width, height.

Internally, the widgets use the `_scale(int) -> int` function to scale the UI according system DPI scaling. All this works thanks to `BuildContext()` object which implements a singleton class. This class can only have a single instance throughout the thread and hence this is used to save state information and is used to cache font sizes.

Since the pygame library is used internally to draw the pixels. Anti Aliasing is done to prevent pixelated looks. This in turn has the effect of working with workarounds to anti alias shapes that do not have an anti aliasing methods.

Under the hood, this application uses the widget `PILImageView` to convert PIL (Pillow) library images to viewable pygame surfaces. The actual image processing is done on the Pillow Image itself.

