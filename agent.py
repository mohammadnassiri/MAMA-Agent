import os
import subprocess
import shlex
import threading
import urllib
import pefile
import requests
import time


class Server:

    # author: https://gist.github.com/Integralist/3f004c3594bbf8431c15ed6db15809ae

    def __init__(self, url):
        self.url = url

    def request(self):
        response = None
        r = requests.post(self.url, data={'arch': "IMAGE_FILE_MACHINE_I386"})  # IMAGE_FILE_MACHINE_I386 is x86
        if r.status_code == 200:
            response = r
        return response

    def download(self, id, name):
        status = False
        url = self.url + '/download'
        file = urllib.URLopener()
        if file.retrieve(url, name):
            status = True
        return status


class Executor:

    # author: https://gist.github.com/mindprince/793ffd546126b7e2fae8
    # Executor("command arg1 arg2", 10).run()

    def __init__(self, cmd, timeout=None):
        """
        `cmd`: The command to run
        `timeout`: The number of seconds to wait for the command to finish
                execution. After timeout seconds have passed, a terminate
                signal is send to the command, followed by a kill signal.
        """
        self.cmd = shlex.split(str(cmd))
        self.timeout = timeout
        self.process = None
        self.stdout = None
        self.stderr = None

    def target(self):
        self.process = subprocess.Popen(self.cmd,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        self.stdout, self.stderr = self.process.communicate()

    def run(self):
        thread = threading.Thread(target=self.target)
        thread.start()

        thread.join(self.timeout)
        if thread.is_alive():
            self.process.terminate()
            self.process.kill()
            thread.join(self.timeout)
        return self.process.returncode, self.stdout, self.stderr


class PEInfo:
    # author: https://github.com/nheijmans/malzoo/blob/master/malzoo/modules/tools/pe.py
    def __init__(self, filename):
        try:
            self.pe = pefile.PE(filename)
            self.filename = filename

        except pefile.PEFormatError:
            self.pe = False
            pass

    def get_cpu_type(self):
        """ Return the CPU architecture (x86, x64) """
        if self.pe:
            machine = 0
            machine = self.pe.FILE_HEADER.Machine

            return pefile.MACHINE_TYPE[machine]
        else:
            return None


class Trace:
    def __init__(self, pin_path, wao_path, file_path, arch, timeout=None):
        self.pin_path = pin_path
        self.wao_path = wao_path
        self.file_path = file_path
        self.arch = arch
        self.timeout = timeout

    def wao(self):
        return

    def pintool(self):
        if self.arch is "IMAGE_FILE_MACHINE_I386":
            print(self.pin_path + "ia32/bin/pin -t " + self.pin_path + "source/tools/godware/obj-ia32/godware.dll -- " + self.file_path + " " + self.pin_path + "source/tools/godware/msgbox.exe")
            x, y, z = Executor(
                self.pin_path + "ia32/bin/pin -t " + self.pin_path + "source/tools/godware/obj-ia32/godware.dll -- " + self.file_path + " " + self.pin_path + "source/tools/godware/msgbox.exe",
                self.timeout).run()
            print(x)
            if x is not None:
                print(y.decode('ascii'))
                print(z.decode('ascii'))
                if "We've finished dumping the remote process." in y.decode('ascii') and os.stat(
                        "logz.txt").st_size > 0:
                    print('OK :)')


if __name__ == '__main__':

    the_end = 120
    server = Server('http://localhost:8000/api/')

    # wait for 120 seconds to if a new file uploaded. it must be infinite loop in production
    while the_end > 0:
        response = server.request().json()
        if response is not None:
            break
        the_end -= 1
        time.sleep(1)

    file_id = response['id']
    file_name = response['name']
    file_arch = response['arch']

    # set path of two tools and the file that will be traced
    pin_path = "C:/Users/MA/Desktop/work/api-seq-tools/pin-2.14-71313-msvc9-windows/"
    file_path = pin_path + "/source/tools/godware/poc2.exe"

    # we will first check the runpe for all samples then in second phase we will trace with wao
    trace = Trace(pin_path, "", file_path, 120)

    # trace file with pintool for runpe
    #trace.pintool()

    # trace file with wao. there must be only one option wao or pin. the vm must revert before other test.
    #trace.wao()

