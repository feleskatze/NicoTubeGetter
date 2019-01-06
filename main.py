
import os, sys, re
import datetime
import time
import tkinter as T
from tkinter import ttk
import subprocess
import threading
import yaml
import urllib
import urllib.request
import urllib.parse
import http
import http.cookiejar
import xml.etree.ElementTree as ET
import atexit
import traceback

from pytube import YouTube

import logging
import logging.handlers

import winsound

class logger:
    def __init__(self, name=__name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("[%(asctime)s] [%(process)d] [%(name)s] [%(levelname)s] %(message)s")

        # stdout
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # fileout
        handler = logging.handlers.RotatingFileHandler(filename = './data/logfile.log', maxBytes = 1048576, backupCount = 3)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warn(self, msg):
        self.logger.warn(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)

log = logger()

# niconico var
video_url_format = "http://www.nicovideo.jp/watch/"
login_url = "https://secure.nicovideo.jp/secure/login"
api_url = "http://www.nicovideo.jp/api/getflv?v="
video_params_re = re.compile(r"([^&]+)=([^&]*)")


class window:
    def __init__(self):
        log.debug('window start')
        self.root = T.Tk()
        self.root.title('TubeGetter')
        self.root.geometry('500x250')

        self.option_button = T.Button(self.root, text='ニコニコ設定', command=self.option_nico)
        self.option_button.pack()

        T.Label(self.root, text='YoutubeのURLもしくはニコニコのsmを入力してください').pack()
        self.box_url = T.Entry(width=80)
        self.box_url.pack()
        self.button = T.Button(self.root, text='変換', command=self.wake)
        self.button.pack()
 
        self.down_var = 0
        self.con_var = 0

        self.bar_download = ttk.Progressbar(self.root, orient="horizontal", length=400, mode='determinate')
        self.bar_download.configure(maximum=100, value=self.down_var)
        self.bar_download.pack()

        self.bar_convert = ttk.Progressbar(self.root, orient="horizontal", length=400, mode='determinate')
        self.bar_convert.configure(maximum=100, value=self.con_var)
        self.bar_convert.pack()

        self.result_buff = T.StringVar()
        self.result_buff.set('')
        T.Label(self.root, textvariable=self.result_buff).pack()
    
        self.click_menu = T.Menu(self.root, tearoff=0)
        self.click_menu.add_command(label="貼り付け")
        self.root.bind_class("Entry", "<Button-3><ButtonRelease-3>", self.show_menu)

        T.Button(self.root, text='resultフォルダを開く', command=self.open_result_folder).pack()

    def show_menu(self, e):
        w = e.widget 
        self.click_menu.entryconfigure("貼り付け", command=lambda: w.event_generate("<<Paste>>")) 
        self.click_menu.tk.call("tk_popup", self.click_menu, e.x_root, e.y_root)

    def option_nico(self):
        sub_win = T.Toplevel()
        T.Label(sub_win, text='メールアドレス').pack()
        self.box_mail = T.Entry(sub_win, width=40)
        self.box_mail.pack()
        T.Label(sub_win, text='パスワード').pack()
        self.box_pass = T.Entry(sub_win, width=40)
        self.box_pass.pack()
        self.option_request_button = T.Button(sub_win, text='反映', command=self.option_write)
        self.option_request_button.pack()
        self.option_suc_label = T.StringVar()
        self.option_suc_label.set('')
        T.Label(sub_win, textvariable=self.option_suc_label).pack()
        data = self.option_read()
        if data:
            self.box_mail.insert(T.END, data['mail'])
            self.box_pass.insert(T.END, data['pass'])

    def open_result_folder(self):
        cwd = os.getcwd()
        subprocess.call('explorer ' + cwd + r'\result', shell=True)

    def option_read(self):
        if os.path.exists('./data/config.yml'):
            f = open('./data/config.yml', 'r')
            data = yaml.load(f)
            f.close()
            return data
        else:
            f = open('./data/config.yml', 'w')
            f.close()

    
    def option_write(self):
        data = {'mail': self.box_mail.get(), 'pass': self.box_pass.get()}
        f = open('./data/config.yml', 'w')
        f.write(yaml.dump(data))
        f.close()
        self.option_suc_label.set('反映しました')

    def wake(self):
        self.down_var = 0
        self.con_var = 0
        if 'youtube' in self.box_url.get():
            sound('./data/sound/con_start.wav')
            time.sleep(1)
            self.button['state'] = 'disabled'
            tube = threading.Thread(target=self.TubeGet)
            tube.start()
        elif 'sm' in self.box_url.get():
            sound('./data/sound/con_start.wav')
            time.sleep(1)
            self.button['state'] = 'disabled'
            nico = threading.Thread(target=self.NicoGet)
            nico.start()



    def TubeGet(self):
        try:
            log.debug('TubeGet Start')
            yt = YouTube(self.box_url.get())
            log.debug(self.box_url.get())
            self.title = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', yt.title)
            self.result_buff.set(self.title + 'を取得中')
            log.debug(self.title)
                
            filename = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

            video = yt.streams.filter(progressive=True, mime_type='video/mp4').desc().first()
            video.player_config_args['title'] = filename
            self.MaxfileSize = video.filesize

            callback = threading.Thread(target=yt.register_on_progress_callback, args=(self.show_progress_bar, ))
            download = threading.Thread(target=video.download, args=('./tmp/', ))
            log.debug('TubeGet Download Start')
            callback.start()
            download.start()
            download.join()

        except:
            log.error('TubeGet Error')
            log.error(traceback.format_exc())
            self.result_buff.set('取得中にエラーが起きました。')
            self.button['state'] = 'normal'
            sound('./data/sound/con_downerror.wav')
            return 0

        log.debug('TubeGet Success')
        convert(self, filename, '.mp4', self.title)

    def show_progress_bar(self, stream=None, chunk=None, file_handle=None, bytes_remaining=None):
        self.down_var = 100 - (100*(bytes_remaining/self.MaxfileSize))
        self.bar_download.configure(maximum=100, value=self.down_var)
        self.result_buff.set(self.title + 'を取得中\n' + str(bytes_remaining) + '/' + str(self.MaxfileSize))



    def NicoGet(self):
        try:
            log.debug('NicoGet Start')
            target = self.box_url.get()
            log.debug(target)

            # title get
            title_req = urllib.request.Request('http://www.nicovideo.jp/api/getthumbinfo/' + target)
            with urllib.request.urlopen(title_req) as response:
                XmlData = response.read()
                root = ET.fromstring(XmlData)
                title = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', root[0][1].text)
            self.result_buff.set(title + 'を取得中')
            log.debug(title)

            # login
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            urllib.request.install_opener(opener)
            option_data = self.option_read()
            if option_data:
                post = {'mail': option_data['mail'], 'password': option_data['pass']}
            else:
                log.error('NicoGet Mail or Password Get Error')
                sound('./data/sound/log_error.wav')
                self.result_buff.set('ログインエラーが起きました。')
                self.button['state'] = 'normal'
                return 0
            data = urllib.parse.urlencode(post).encode('ascii')
            urllib.request.urlopen(login_url, data)
            log.debug('NicoGet Login Success')

            # pretend watching
            html_data = urllib.request.urlopen(video_url_format + target).read()
            log.debug('NicoGet Pretend Watching')

            # download
            response = urllib.request.urlopen(api_url + target).read()
            params = dict(video_params_re.findall(str(response)))
            if 'url' in params:
                flv_url = urllib.parse.unquote(params["url"])

            log.debug('NicoGet Download Start')
            response = urllib.request.urlopen(flv_url)
            total_size = response.info()
            filename = target
            video_file = open('./tmp/' + filename + '.flv', 'wb')
            downloaded_size = 0
            while True:
                video_data = response.read(1024 * 10 * 10)
                if not video_data: break
                video_file.write(video_data)
                downloaded_size += len(video_data)
                self.down_var = 100*(float(downloaded_size)/float(total_size['Content-Length']))
                self.bar_download.configure(maximum=100, value=self.down_var)
                self.result_buff.set(title + 'を取得中\n' + str(downloaded_size) + '/' + str(total_size['Content-Length']))
            video_file.close()
        except:
            log.error('NicoGet Error')
            log.error(traceback.format_exc())
            self.result_buff.set('取得中にエラーが起きました。')
            self.button['state'] = 'normal'
            sound('./data/sound/con_downerror.wav')
            return 0

        log.debug('NicoGet Success')
        convert(self, filename, '.flv', title)


def convert(w, input_filename, input_filetype, output_filename):
    try:
        log.debug('Convert Start')
        w.result_buff.set(output_filename + 'を変換中')
        cmd = ['./ffmpeg.exe', '-i' ,'./tmp/' + input_filename + input_filetype, './result/' + input_filename + '.mp3']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, universal_newlines=True)
        for line in process.stdout:
            if 'Duration' in line:
                Duration = line.split()[1].strip(",").split(':')
                DurationTime = float(Duration[0]) * 60 * 60 + float(Duration[1]) * 60 + float(Duration[2])
            if 'time=' in line:
                Suc = line.split()[2].strip("time=").split(':')
                SucTime = float(Suc[0]) * 60 * 60 + float(Suc[1]) * 60 + float(Suc[2])
                w.con_var = 100*(SucTime/DurationTime)
                w.bar_convert.configure(maximum=100, value=w.con_var)

        os.remove('./tmp/' + input_filename + input_filetype)
        os.rename('./result/' + input_filename + '.mp3', './result/' + output_filename + '.mp3')

        w.result_buff.set('変換完了\n' + output_filename + '.mp3' + '\nresultフォルダに保存されました')
        w.button['state'] = 'normal'
        sound('./data/sound/con_end.wav')
    except:
        log.error('Convert Error')
        log.error(traceback.format_exc())
        w.result_buff.set('変換中にエラーが起きました。')
        w.button['state'] = 'normal'
        sound('./data/sound/con_convererror.wav')

    
def sound(Filename):
    threading.Thread(target=winsound.PlaySound, args=(Filename, winsound.SND_FILENAME)).start()

if __name__ == '__main__':
    log.debug('Start App')
    sound('./data/sound/pro_start.wav')
    w = window()
    w.root.mainloop()
    atexit.register(lambda: log.debug('End App'))