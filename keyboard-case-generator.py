#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback


def run(context):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        from .generator import main
        main(app)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
