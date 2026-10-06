import os
from tools import _venv
_venv.ensure(os.path.dirname(os.path.abspath(__file__)))

from utils.functions import sendEvent, showLogo
from objects.Tester.index import tester
from objects.Device.index import device
from objects.Server.index import server
from time import sleep


version = 'v2.2.0'

if __name__ == '__main__':
    while True:
        showLogo(version)
        sendEvent('program', 'Sighir Tester Program', 'orange', repeat=True)
        sleep(0.5)
        tester.start()
        sleep(1.5)
        print()
