from app_model import Application
from pymmcore_plus import CMMCorePlus

from ._actions import ACTIONS

my_app = Application("pymmcore-gui")

for action in ACTIONS:
    my_app.register_action(action)


my_app.injection_store.register_provider(CMMCorePlus.instance, CMMCorePlus)
