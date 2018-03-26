import os
import subprocess
import shlex
import threading
import pyautogui
import requests
import time


class Server:

    # author: https://gist.github.com/Integralist/3f004c3594bbf8431c15ed6db15809ae

    def __init__(self, url, vbox):
        self.url = url
        self.vbox = vbox

    def request(self):
        result = None
        url = self.url + 'request'
        req = requests.post(url, data={'arch': "IMAGE_FILE_MACHINE_I386", 'vbox': self.vbox})  # IMAGE_FILE_MACHINE_I386 is x86
        if req.status_code == 200:
            result = req
        return result

    def download(self, id, name):
        result = None
        url = self.url + 'download'
        with open(name, "wb") as file:
            # get request
            req = requests.post(url, data={'id': id, 'vbox': vbox})
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
            req = requests.post(url,
                                data={
                                    'vbox': vbox,
                                    'id': id,
                                    'response': response,
                                    'sequence': sequence,
                                    'run_pe_sequence': run_pe_sequence,
                                    'run_pe': run_pe
                                },
                                files={
                                    'run_pe_file': open(run_pe_file, 'rb'),
                                    'screen_shot': open(screen_shot, 'rb'),
                                })
        elif screen_shot is not None:
            req = requests.post(url,
                                data={
                                    'vbox': vbox,
                                    'id': id,
                                    'response': response,
                                    'sequence': sequence,
                                    'run_pe': run_pe
                                },
                                files={
                                    'screen_shot': open(screen_shot, 'rb')
                                })
        else:
            req = requests.post(url,
                                data={
                                    'vbox': vbox,
                                    'id': id,
                                    'response': response,
                                    'sequence': sequence,
                                    'run_pe': run_pe
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
        status = 0
        x = ""
        y = ""
        z = ""
        file = None
        sequence = ""
        if self.arch == "IMAGE_FILE_MACHINE_I386":
            try:
                x, y, z = Executor(
                    self.pin_path + "ia32/bin/pin -t " + self.pin_path + "source/tools/godware/obj-ia32/godware.dll -- " + self.file_path + " " + self.pin_path + "source/tools/godware/msgbox.exe",
                    self.timeout).run()
                if x is not None:
                    if "We've finished dumping the remote process." in y.decode('ascii') and os.stat(
                            "logz.txt").st_size > 0:
                        status = 1
                        y = y.decode('ascii')
                        z = z.decode('ascii')
                        file = "logz.txt"
                        sequence = y
            except Exception as e:
                status = 0
        return status, file, sequence, x, y, z


def __screen_shot(timeout):
    name = 'screenshot.png'
    time.sleep(timeout)
    pic = pyautogui.screenshot()
    pic.save(name)
    return name


if __name__ == '__main__':

    # configuration
    vbox = "win7-1"
    timeout = 10
    screen_shot_time = 5
    server = Server('http://localhost:8000/api/', vbox)
    this_pin_path = "C:/Users/MA/Desktop/work/api-seq-tools/pin-2.14-71313-msvc9-windows/"
    this_wao_path = "C:/Users/MA/Desktop/work/api-seq-tools/WinAPIOverride32.exe"
    wao_pin = 1  # 0 for wao and 1 for pin
    response = None
    file = None
    screen_shot = None

    # wait for 120 seconds to if a new file uploaded. it must be infinite loop in production
    while 1:
        try:
            response = server.request().json()
            if not response == 0:
                print("(*) Got a file for trace ...")
                break
            print("(!) No file provided. Will try after 1 second.")
            time.sleep(1)
        except Exception as e:
            continue

    file_id = response['id']
    file_name = response['name']
    file_arch = response['arch']
    file = server.download(file_id, file_name)
    if file is None:
        result = "(!) Can't download file"
        print(result)
        result = server.result(file_id, result, "", None, "", None, 0)
    else:
        # get a screenshot
        print("(*) Start screen shot thread ...")
        screen_shot = "screenshot.png"
        screen_shot_thread = threading.Thread(target=__screen_shot, args={screen_shot_time})
        screen_shot_thread.start()

        # set path of two tools and the file that will be traced
        wao_path = this_wao_path
        pin_path = this_pin_path
        file_path = os.path.join(file_name)

        # we will first check the runpe for all samples then in second phase we will trace with wao
        trace = Trace(pin_path, wao_path, file_path, file_arch, timeout)

        # trace file with wao. there must be only one option wao or pin. the vm must revert before other test.
        sequence = ""
        if wao_pin == 0:
            print("(*) Start WAO thread ...")
            # sequence = trace.wao() path this_wao_path

        # trace file with pintool for runpe
        run_pe = 0
        run_pe_file = None
        run_pe_sequence = ""
        if wao_pin == 1:
            print("(*) Start Pin tool thread ...")
            run_pe, run_pe_file, run_pe_sequence, x, y, z = trace.pintool()
            print(x, y, z)

        # final result
        result = "Process Done."

        # check screen_shot threads
        print("(*) Wait for screen shot thread ...")
        screen_shot_thread.join()

        # sending results
        print("(*) Sending results ...")
        result = server.result(file_id, result, sequence, run_pe_file, run_pe_sequence, screen_shot, run_pe)

        print("(*) Done.")
