from os import popen, system
from ..tools import findAllWithRe, sleep
from random import randint
from ..mysql import Retrieve, Update


def getOnlineDevices():
    res = popen('adb devices').read()
    res = findAllWithRe(res, r'(.+)\tdevice')
    for i in range(len(res)):
        res[i] = res[i].replace(':5555', '')
    return res


class ADB:

    def __init__(self, deviceSN):
        """
        :param deviceSN:
        """
        self.deviceSN = deviceSN
        self.device = Retrieve(deviceSN)
        self.cmd = 'adb -s %s ' % self.device.ID
        self.usb()
        IPv4Address = self.getIPv4Address()
        if not IPv4Address == self.device.IP:
            Update(deviceSN).updateIP(IPv4Address)
            self.device = Retrieve(deviceSN)
        self.tcpip()
        self.reconnect()
        self.cmd = 'adb -s %s ' % self.device.IP
        if 'com.android.settings/com.android.settings.Settings$UsbDetailsActivity' in self.getCurrentFocus():
            self.pressBackKey()

    def getCurrentFocus(self):
        r = popen(self.cmd + 'shell dumpsys window | findstr mCurrentFocus').read()
        r = r.replace("  mCurrentFocus=Window{", '')
        r = r[:-2]
        print(r)
        return r

    def pressKey(self, keycode):
        print('正在让%s按下%s键' % (self.deviceSN, keycode))
        system(self.cmd + 'shell input keyevent ' + keycode)
        sleep(1)

    def pressHomeKey(self):
        self.pressKey('KEYCODE_HOME')

    def pressMenuKey(self):
        self.pressKey('KEYCODE_MENU')

    def pressBackKey(self):
        self.pressKey('KEYCODE_BACK')

    def usb(self, timeout=2):
        """
        restart adbd listening on USB
        :return:
        """
        system(self.cmd + 'usb')
        sleep(timeout)
        if self.device.ID not in getOnlineDevices():
            self.usb(timeout + 1)

    def tcpip(self):
        """
        restart adbd listening on TCP on PORT
        :return:
        """
        system(self.cmd + 'tcpip 5555')
        sleep(1)

    def connect(self, timeout=1):
        """
        connect to a device via TCP/IP [default port=5555]
        :return:
        """
        system('adb connect %s' % self.device.IP)
        sleep(timeout)
        if self.device.IP not in getOnlineDevices():
            self.connect(timeout + 1)

    def disconnect(self):
        """
        disconnect from given TCP/IP device [default port=5555], or all
        :return:
        """
        system('adb disconnect %s' % self.device.IP)
        sleep(3)

    def reconnect(self):
        self.disconnect()
        self.connect()

    def tap(self, x, y):
        print('正在让%s点击(%d,%d)' % (self.deviceSN, x, y))
        system(self.cmd + 'shell input tap %d %d' % (x, y))
        sleep(1)

    def start(self, Activity, wait=True):
        cmd = 'shell am start '
        if wait:
            cmd += '-W '
        system(self.cmd + cmd + Activity)

    def swipe(self, x1, y1, x2, y2, duration=-1):
        """
        :param x1:
        :param y1:
        :param x2:
        :param y2:
        :param duration: the default duration is a random integer from 300 to 500
        :return:
        """
        if duration == -1:
            duration = randint(300, 500)
        system(self.cmd + 'shell input swipe %d %d %d %d %d' % (x1, y1, x2, y2, duration))

    def longPress(self, x, y, duration=-1):
        """
        :param x:
        :param y:
        :param duration: the default duration is a random integer from 1000 to 1500
        :return:
        """
        if duration == -1:
            duration = randint(1000, 1500)
        self.swipe(x, y, x, y, duration)

    def reboot(self):
        popen(self.cmd + 'reboot')
        print('已向设备%s下达重启指令' % self.device.SN)
        sleep(60)
        self.__init__(self.device.SN)

    def getIPv4Address(self):
        rd = popen(self.cmd + 'shell ifconfig wlan0').read()
        IPv4Address = findAllWithRe(rd, r'inet addr:(\d+.\d+.\d+.\d+)  Bcast:.+')
        if len(IPv4Address) == 1:
            IPv4Address = IPv4Address[0]
        # print(IPv4Address)
        return IPv4Address

    def getIPv6Address(self):
        rd = popen(self.cmd + 'shell ifconfig wlan0').read()
        # print(rd)
        IPv6Address = findAllWithRe(rd, r'inet6 addr: (.+:.+:.+)/64 Scope: Global')
        if len(IPv6Address) <= 2:
            IPv6Address = IPv6Address[0]
            print('设备%s的公网IPv6地址为：%s' % (self.device, IPv6Address))
        else:
            print('%s的公网IPv6地址数大于2，正在尝试重新获取')
            self.reboot()
            self.getIPv6Address()
