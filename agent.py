import os
import subprocess
import shlex
import threading
import pyautogui
import requests
import time


class Server:

    # author: https://gist.github.com/Integralist/3f004c3594bbf8431c15ed6db15809ae

    def __init__(self, url):
        self.url = url

    def request(self):
        result = None
        req = requests.post(self.url, data={'arch': "IMAGE_FILE_MACHINE_I386"})  # IMAGE_FILE_MACHINE_I386 is x86
        if req.status_code == 200:
            result = req
        return result

    def download(self, id, name):
        result = None
        url = self.url + 'download'
        with open(name, "wb") as file:
            # get request
            req = requests.post(url, data={'id': id})
            if not req.status_code == 404:
                # write to file
                file.write(req.content)
        if os.path.getsize(name) > 0:
            result = file
        return result

    def result(self, id, response, sequence, run_pe_file, run_pe_sequence, screen_shot, run_pe):
        result = None
        url = self.url + 'result'
        if run_pe_file is not None:
            req = requests.post(url, data={
                'id': id,
                'response': response,
                'sequence': sequence,
                'run_pe_file': {'file': open(run_pe_file, 'rb')},
                'run_pe_sequence': run_pe_sequence,
                'screen_shot': {'file': open(screen_shot, 'rb')},
                'run_pe': run_pe
            })
        else:
            req = requests.post(url, data={
                'id': id,
                'response': response,
                'sequence': sequence,
                'screen_shot': {'file': open(screen_shot, 'rb')},
                'run_pe': 0
            })
        if req.status_code == 200:
            result = req
        return result


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
            print(
                self.pin_path + "ia32/bin/pin -t " + self.pin_path + "source/tools/godware/obj-ia32/godware.dll -- " + self.file_path + " " + self.pin_path + "source/tools/godware/msgbox.exe")
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


def __get_screen_shot_(timeout):
    thread = threading.Thread(target=__screen_shot(timeout))
    thread.start()
    thread.join()


def __screen_shot(timeout):
    time.sleep(timeout)
    pic = pyautogui.screenshot()
    pic.save('screenshot.png')


if __name__ == '__main__':

    # configuration
    timeout = 120
    scree_shot_time = 30
    server = Server('http://localhost:8000/api/')
    wao_pin = 1  # 0 for wao and 1 for pin
    response = None
    file = None

    # wait for 120 seconds to if a new file uploaded. it must be infinite loop in production
    while 1:
        response = server.request().json()
        if not response == 0:
            break
        print("No file provided. Will try after 1 second.")
        time.sleep(1)

    file_id = response['id']
    file_name = response['name']
    file_arch = response['arch']
    file = server.download(file_id, file_name)
    if file is None:
        result = "Can't download file"
        print(result)
    else:
        # get a screenshot
        __get_screen_shot_(scree_shot_time)

        # set path of two tools and the file that will be traced
        pin_path = "C:/Users/MA/Desktop/work/api-seq-tools/pin-2.14-71313-msvc9-windows/"
        file_path = pin_path + "/source/tools/godware/poc2.exe"

        # we will first check the runpe for all samples then in second phase we will trace with wao
        trace = Trace(pin_path, "", file_path, file_arch, timout)

        # trace file with wao. there must be only one option wao or pin. the vm must revert before other test.
        sequence = ""
        if wao_pin == 0:
            print(0)
            # sequence = trace.wao()

        # trace file with pintool for runpe
        run_pe = 0
        run_pe_file = None
        run_pe_sequence = ""
        if wao_pin == 1:
            print(1)
            # runpe, runpe_file, runpe_sequence = trace.pintool()

        result = "Process Done."

        # sending results
        # result = server.result(file_id, result, sequence, run_pe_file, run_pe_sequence, screen_shot, run_pe)
