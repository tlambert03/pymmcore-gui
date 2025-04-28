from app_model import Application
from pymmcore_plus import CMMCorePlus

from ._actions import ACTIONS

mmgui_app_model = Application("pymmcore-gui")

for action in ACTIONS:
    mmgui_app_model.register_action(action)


mmgui_app_model.injection_store.register_provider(CMMCorePlus.instance, CMMCorePlus)
