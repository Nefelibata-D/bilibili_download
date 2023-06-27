import requests
import os
import time
import qrcode
import json
from bs4 import BeautifulSoup
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn, BarColumn, TimeRemainingColumn, TextColumn, \
    TimeElapsedColumn
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys


# noinspection PyShadowingNames
def login(headers: dict):
    """
    模拟B站二维码登录功能, 获取用户cookies有效内容
    cookies 有效时间应在 15d-30d
    """

    login_url = 'https://passport.bilibili.com/qrcode/getLoginUrl'  # 获取登录二维码
    res = requests.get(url=login_url, headers=headers)
    qrcode_url = res.json()['data']['url']  # 登录二维码所含内容
    oauth_key = res.json()['data']['oauthKey']
    img = qrcode.make(qrcode_url)

    #  将二维码图片保存为图像
    with open('./qrcode.png', 'wb') as file:
        img.save(file)
    os.system('start qrcode.png')

    login_info_url = 'https://passport.bilibili.com/qrcode/getLoginInfo?oauthKey={}'.format(oauth_key)  # 二维码状态获取
    cookies = ''
    for i in range(60):  # 等待用户登录扫码, 等待时间60s
        res = requests.post(url=login_info_url, headers=headers)
        if res.json()['status']:
            user = res.json()['data']['url']
            for n in user.split('?')[1].split('&gourl')[0].split('&'):  # 获取cookies有效参数
                cookies += n + ';'
            break
        time.sleep(1)  # 1s刷新一次状态，直到登录成功
    os.system('del qrcode.png')

    if not cookies:
        return None

    return cookies


# noinspection PyShadowingNames
def set_config(cookies, path):
    # 保存用户登录信息
    mid = cookies.split(';')[0].split('=')[1]
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    cof = {
        'mid': mid,  # 用户账号唯一id
        'cookies': cookies,  # cookies有效值
        'timestamp': timestamp  # 登录时间，目前cookies过期可能性较低
    }

    with open(r'{}\config.json'.format(path), 'w') as file:
        file.write(json.dumps(cof))

    return None


# noinspection PyShadowingNames
# 由bvid获取cid，B站api中常用cid
def bvid_get_part(bvid: str, headers: dict):
    url = 'https://api.bilibili.com/x/player/pagelist?bvid={}'.format(bvid)
    res = requests.get(url=url, headers=headers)
    part_list = []
    for i in res.json()['data']:
        cid = i['cid']
        part = i['part']
        part_list.append((cid, part))

    return part_list


# noinspection PyShadowingNames
# 由bvid，cid获取aid
def get_aid(bvid: str, cid: int, headers: dict, name: str):
    url = 'https://api.bilibili.com/x/web-interface/view?cid={}&bvid={}'.format(cid, bvid)
    res = requests.get(url=url, headers=headers)
    aid = res.json()['data']['aid']
    if name != '':
        file_name = name
    else:
        file_name = res.json()['data']['title']

    return aid, file_name


# noinspection PyShadowingNames
def heartbeat(aid: int, mid: int, cid: int, headers: dict):
    #  ttl握手, 目前不起作用, 不知后期是否会作为反爬虫判定
    url = 'https://api.bilibili.com/x/click-interface/web/heartbeat?mid={}&aid={}&cid={}'.format(mid, aid, cid)
    res = requests.post(url=url, headers=headers)

    return res.json()['ttl']


def dolby(cid: int, headers: dict):
    url = 'https://api.bilibili.com//pgc/player/web/v2/playurl?support_multi_audio=true&cid={}&fnval=4048'.format(cid)
    res = requests.get(url, headers=headers)
    result = res.json()['result']['video_info']['dash']['dolby']['audio'][0]
    url = result['base_url']
    codecs = result['codecs']
    size = result['size']

    return url, codecs, size


# noinspection PyShadowingNames,PyUnusedLocal
def detail(bvid: str, cid: int, headers: dict, choice, type: int, ep):
    #  fourk为4k请求参数, fnval=4048为8k请求参数
    #  |"超高清 8K", 127         |"超清 4K", 120       |"杜比视界", 126
    #  |"高清 1080P60", 116      |"高清 1080P+", 112
    #  |"高清 1080P", 80         |"高清 720P", 64
    #  |"清晰 480P", 32          |"流畅 360P" 16

    qn = {'127': '超高清 8K', '126': '杜比视界', '120': '超清 4K', '116': '高清 1080P60', '112': '高清 1080P+',
          '80': '高清 1080P', '64': '高清 720P', '32': '清晰 480P', '16': '流畅 360P'}

    all_inf = []  # 所有视频/音频信息列表

    if type == 0:
        url = 'https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&fourk=1&fnval=4048'.format(bvid, cid)
    else:
        url = 'https://api.bilibili.com/pugv/player/web/playurl?fnval=16&fourk=1&ep_id={}'.format(ep)
    res = requests.get(url=url, headers=headers)

    if choice is None:  # 在番剧批量下载中，用于保持用户最初选择
        choice = []
        os.system('cls')

        # 视频信息输出
        print('')
        print('============================================================')
        print('Video Quality: ')
        print('')
        times = 0
        have_dolby = False  # 检测是否有视频对应杜比音效
        for i in res.json()['data']['dash']['video']:
            id = i['id']
            base_url = i['base_url']
            codecs = i['codecs']
            quality = qn[str(id)]
            size = round(
                int(requests.get(base_url, headers=headers, stream=True).headers['Content-Length']) / 1024 / 1024)
            if id == 126:
                have_dolby = True
            if size > 1024:
                print('[{:0>2}]  Quality: {: <10}  Size: {: <4} {}  Codec: {}  '.format(times, qn[str(id)],
                                                                                        str(round(size / 1024, 2)),
                                                                                        'GB', codecs))
            else:
                print(
                    '[{:0>2}]  Quality: {: <10}  Size: {: <4} {}  Codec: {}  '.format(times, qn[str(id)], str(size),
                                                                                      'MB', codecs))
            all_inf.append((id, base_url, codecs, quality))
            times += 1
        print('[{:0>2}]  Not download video (Only audio)'.format(times))
        print('============================================================')
        video_number = input('Please choose the number before the video you want to download.')
        if int(video_number) == times:
            video = None
        else:
            video = all_inf[int(video_number)][1]
        all_inf.clear()

        # 音频信息输出
        os.system('cls')
        print('')
        print('============================================================')
        print('Audio Quality: ')
        print('')
        times = 0

        if have_dolby:  # 获取杜比音效信息
            dolby_inf = dolby(cid, headers)
            base_url = dolby_inf[0]
            codecs = dolby_inf[1]
            size = round(dolby_inf[2] / 1024 / 1024)
            all_inf.append((base_url, codecs, size))
            print('[{:0>2}]  Size: {: <8}  Codec: {}     (杜比音效)'.format(times, str(size) + ' MB', codecs))
            times += 1

        for i in res.json()['data']['dash']['audio']:
            base_url = i['base_url']
            codecs = i['codecs']
            size = round(
                int(requests.get(base_url, headers=headers, stream=True).headers['Content-Length']) / 1024 / 1024)
            all_inf.append((base_url, codecs, size))
            print('[{:0>2}]  Size: {: <8}  Codec: {}  '.format(times, str(size) + ' MB', codecs))
            times += 1
        print('[{:0>2}]  Not download audio (Only video)'.format(times))
        print('============================================================')
        audio_number = input('Please choose the number before the audio you want to download.')
        if int(audio_number) == times:
            audio = None
        else:
            audio = all_inf[int(audio_number)][0]
        all_inf.clear()
        os.system('cls')

        choice.append(video_number)
        choice.append(audio_number)
    else:
        try:
            video = res.json()['data']['dash']['video'][int(choice[0])]['base_url']
        except IndexError:
            video = None

        try:
            audio = res.json()['data']['dash']['audio'][int(choice[1])]['base_url']
        except IndexError:
            audio = None

    return video, audio, choice


def get_ep_bvid(aid: int, cid: int, headers: dict):
    res = requests.get("https://api.bilibili.com/x/player/wbi/v2?aid={}&cid={}".format(aid, cid), headers=headers)
    bvid = res.json()['data']['bvid']

    return bvid


# noinspection PyUnboundLocalVariable,PyShadowingNames,PyShadowingBuiltins,PyPep8Naming
class Download_threader:
    def __init__(self, url: str, cookie: str, size: int, thread: int, progress, task, file_name: str,
                 download_path: str):
        self.url = url
        self.file_size = size  # 文件实际大小
        self.get_size = 0  # 文件下载大小
        self.last_size = 0  # 最后一次更新进度条是文件下载大小
        self.thread = thread  # 线程数量
        self.task = task  # rich.task
        self.progress = progress  # rich.progress
        self.cookie = cookie
        self.file_name = file_name
        self.download_path = download_path

    def download_parts(self, part: int, cookie: str, Range: str):
        # 视频分片下载
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1336.2',
            'Referer': 'https://www.bilibili.com/',
            'Cookie': cookie,
            'Range': Range  # 指定视频分片链接
        }
        res = requests.get(url=self.url, headers=headers, stream=True)  # 流式下载视频
        with open(r'{}\part{}.tmp'.format(self.download_path, part), 'wb') as file:
            for i in res.iter_content(chunk_size=64 * 1024):
                file.write(i)
                self.get_size += len(i)  # 更新视频已经下载大小
                file.flush()
                time.sleep(0.005)  # 防线程堵塞, 可注释

    def copy_tmps(self):
        # 分片视频合并
        for i in range(self.thread):
            with open(r'{}\part{}.tmp'.format(self.download_path, i), 'rb') as tmp:
                content = tmp.read()
            os.remove(r'{}\part{}.tmp'.format(self.download_path, i))
            with open(r'{}\{}.m4s'.format(self.download_path, self.file_name), 'ab+') as file:
                file.write(content)
                file.flush()

    def download_thread(self):
        # 多线程下载
        futures = []
        tp = ThreadPoolExecutor(max_workers=self.thread)
        for i in range(self.thread):
            if i < self.thread - 1:
                Range = 'bytes={}-{}'.format(int(self.file_size / self.thread) * i,
                                             int(self.file_size / self.thread) * (i + 1) - 1)
            else:
                if self.file_name == 'video':
                    Range = 'bytes={}-{}'.format(int(self.file_size / self.thread) * i, self.file_size)
                else:
                    Range = 'bytes={}-{}'.format(int(self.file_size / self.thread) * i,
                                                 self.file_size - 1)  # 请求音频有概率出现不能分片问题
            future = tp.submit(self.download_parts, i, self.cookie, Range)
            futures.append(future)

        while True:
            # 更新进度条进度, 刷新时间0.5s
            advance = self.get_size - self.last_size
            self.progress.update(self.task, advance=advance)
            self.last_size = self.get_size
            time.sleep(0.5)

            if self.last_size == self.file_size or self.last_size == self.file_size - 1:  # 下载结束跳出循环
                break

        tp.shutdown(wait=True)
        self.copy_tmps()


# noinspection PyUnboundLocalVariable,PyShadowingNames
def get_ep_list(headers, session_id):
    # 通过session_id获取所有视频的aid、cid
    res = requests.get('https://api.bilibili.com/pgc/web/season/section?season_id={}'.format(session_id),
                       headers=headers)
    ep_json = res.json()['result']['main_section']['episodes']
    ep_list = []

    for i in ep_json:
        aid = i['aid']
        cid = i['cid']
        bvid = get_ep_bvid(aid, cid, headers)
        title = i['long_title']
        ep_list.append({
            'bvid': bvid,
            'title': title
        })

    return ep_list


# noinspection PyShadowingNames
def get_class_list(headers, ep_id):
    res = requests.get('https://api.bilibili.com/pugv/view/web/season?ep_id={}'.format(ep_id), headers=headers)
    all_class = res.json()['data']['episodes']
    class_list = []

    for i in all_class:
        aid = i['aid']
        cid = i['cid']
        bvid = get_ep_bvid(aid, cid, headers)
        title = i['title']
        id = i['id']
        class_list.append({
            'bvid': bvid,
            'title': title,
            'epid': id
        })

    return class_list


# noinspection PyShadowingBuiltins,PyShadowingNames
def main(bvid: str, thread: int, download_path: str, output: int, name: str, headers: dict, choice, type: int, ep=None):
    if os.path.exists(r'{}\config.json'.format(os.path.dirname(os.path.realpath(__file__)))):
        print('Find config.json')
        with open(r'{}\config.json'.format(os.path.dirname(os.path.realpath(__file__))), 'r') as file:
            file = json.loads(file.read())
            cookies = file['cookies']
            print('Last login time:  {}'.format(file['timestamp']))
        headers['Cookie'] = cookies
    else:
        print('Please scan QR Code to login. You will have 60 seconds to login.')
        cookies = login(headers)
        if cookies:
            set_config(cookies, os.path.dirname(os.path.realpath(__file__)))
            headers['Cookie'] = cookies
            print('Login successful. Login cookies is saved to config.json.')
        else:
            print('Login failed. Please try again later.')
            sys.exit(1)

    if os.path.exists('{}\\output.mp4'.format(download_path)):
        os.remove(r'{}\output.mp4'.format(download_path))

    final_list = []  # 最终所有待下载视频列表

    part_list = bvid_get_part(bvid, headers)

    if len(part_list) == 1:
        cid = part_list[0][0]
        if name:
            file_name = name
        else:
            file_name = part_list[0][1]
        final_list.append((cid, file_name))
    else:
        os.system('cls')
        print('该视频有多个分集, 请选择想要下载的内容, 若为空, 则全部下载')
        print('============================================================')
        print('')
        times = 0
        for i in part_list:
            print('[{:0>2}]  {}'.format(times, i[1]))
            times += 1
        print('')
        print('============================================================')
        part_no = input('请输入名称前的数字: ')
        if part_no:
            part_no = int(part_no)
            final_list.append((part_list[part_no][0], part_list[part_no][1]))
        else:
            final_list = part_list

    for i in final_list:
        tuple = detail(bvid, i[0], headers, choice, type, ep)
        choice = tuple[2]
        file_name = i[1]
        print('')
        print("File name: " + file_name)
        print('')

        if tuple[0]:
            with Progress(TextColumn('{task.description}'), DownloadColumn(binary_units=True), BarColumn(),
                          TransferSpeedColumn(), '·', TimeRemainingColumn(), '·', TimeElapsedColumn()) as progress:
                res = requests.get(url=tuple[0], headers=headers, stream=True)
                size = res.headers['Content-Length']
                task = progress.add_task('Downloading_Video...', total=int(size))
                download_threader = Download_threader(tuple[0], headers['Cookie'], int(size), thread, progress, task,
                                                      'video', download_path)
                download_threader.download_thread()
                os.rename('{}\\video.m4s'.format(download_path), '{}\\video.mp4'.format(download_path, file_name))
        if tuple[1]:
            with Progress(TextColumn('{task.description}'), DownloadColumn(binary_units=True), BarColumn(),
                          TransferSpeedColumn(), '·', TimeRemainingColumn(), '·', TimeElapsedColumn()) as progress:
                res = requests.get(url=tuple[1], headers=headers, stream=True)
                size = res.headers['Content-Length']
                task = progress.add_task('Downloading_Audio...', total=int(size))
                download_threader = Download_threader(tuple[1], headers['Cookie'], int(size), thread, progress, task,
                                                      'audio', download_path)
                download_threader.download_thread()
                os.rename('{}\\audio.m4s'.format(download_path), '{}\\audio.mp3'.format(download_path, file_name))
        if None not in tuple:
            print('Combining...')
            if output:
                os.system(r"{0}\\ffmpeg.exe -i {1}\\video.mp4 -i {1}\\audio.mp3 -c copy {1}\\output.mp4 ".format(
                    os.path.dirname(os.path.realpath(__file__)), download_path))
            else:
                os.system(
                    r"{0}\\ffmpeg.exe -i {1}\\video.mp4 -i {1}\\audio.mp3 -c copy {1}\\output.mp4 -loglevel quiet".format(
                        os.path.dirname(os.path.realpath(__file__)), download_path))
            os.remove(r'{}\\video.mp4'.format(download_path))
            os.remove(r'{}\\audio.mp3'.format(download_path))
            os.rename('{}\\output.mp4'.format(download_path), '{}\\{}.mp4'.format(download_path, file_name))
        elif tuple[0]:
            os.rename('{}\\video.mp4'.format(download_path), '{}\\{}.mp4'.format(download_path, file_name))
        else:
            os.rename('{}\\audio.mp3'.format(download_path), '{}\\{}.mp3'.format(download_path, file_name))
        print('Done')

        choice = tuple[2]

    return choice


# cmd 输入参数
parser = argparse.ArgumentParser(description='bilibili download ')
parser.add_argument('-b', '--bvid', type=str, help="指定视频BV号")
parser.add_argument('-t', '--thread', type=int, default=8, choices=[2, 4, 8, 16, 32], help='下载线程数, 默认为8')
parser.add_argument('-n', '--name', type=str, default='', help='对下载视频重新命名')
parser.add_argument('-s', '--ssid', type=int, help='指定番剧ss号')
parser.add_argument('-e', '--epid', type=int, help='指定该课程任意ep号')
parser.add_argument('-l', '--login', action='store_true', default=False, help='扫二维码登录')
# parser.add_argument('-c', '--cookie', action='store_true', default=False, help='手动输入cookies登录')
parser.add_argument('-o', '--output', action='store_true', default=False, help='保留ffmpeg输出')

args = parser.parse_args()

if __name__ == '__main__':
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1336.2',
        'Referer': 'https://www.bilibili.com/'
    }
    if args.login:
        cookies = login(headers)
        set_config(cookies, os.path.dirname(os.path.realpath(__file__)))
        print('Login successful. Login cookies is saved to config.json.')
        sys.exit(0)
    '''
    if args.cookie:
        c = input('Enter your account cookies: ')
        cookies = ''
        for i in c.split(';'):
            if 'SESSDATA' in i or 'bili_jct' in i or 'DedeUserID' in i or 'DedeUserID__ckMd5' in i:
                print('================================================================')
                cookies += i + ';'
    '''
    if args.bvid is None and args.ssid is None and args.epid is None:
        print('Please enter BVID or SESSION_ID or EPID')
        print("Use 'python bilibili.py -h' to show helps.")
        sys.exit(1)

    download_path = os.path.dirname(os.path.realpath(__file__)) + r'\Download'
    try:
        os.mkdir(download_path)  # 创建下载目录
    except FileExistsError:
        pass
    print('')
    print('Download Directory : ' + download_path)
    print('')

    if os.path.exists(os.path.dirname(os.path.realpath(__file__)) + r'\\ffmpeg.exe'):
        os.system('cls')
        if args.bvid:
            main(args.bvid, args.thread, download_path, args.output, args.name, headers, None, 0)
        if args.ssid or args.epid:
            dir_name = input("为该批量下载的文件夹取个名字吧~ (不要有空格哦)： ")
            new_download_path = os.path.join(download_path, dir_name)
            try:
                os.mkdir(new_download_path)
            except FileExistsError:
                pass

            print('Getting episodes information...')
            print('')
            print('============================================================')
            # 输出批量下载所有视频内容
            if args.ssid:
                eps = get_ep_list(headers, args.ssid)
            else:
                eps = get_class_list(headers, args.epid)
            times = 0
            for i in eps:
                print('[{:0>2}]   {}'.format(times, i['title']))
                times += 1
            print('')
            print('============================================================')
            video_choice = input('请选择要下载的视频, 例如：1,3,5-12, 若不输入, 默认全部下载~(英文逗号, 不要空格!!!):  ')

            if video_choice:
                video_index = []
                v1 = video_choice.split(',')
                for i in v1:
                    if '-' in i:
                        for j in range(int(i.split('-')[0]), int(i.split('-')[1]) + 1):
                            video_index.append(j)
                    else:
                        video_index.append(int(i))
            else:
                video_index = None
            try:
                video_index = list(set(video_index))  # 去除列表中重复元素
            except TypeError:
                pass

            choice = None
            if video_index:
                for i in video_index:
                    print('')
                    print('Video index: {}'.format(i))
                    if args.ssid:
                        choice = main(eps[i]['bvid'], args.thread, new_download_path, args.output, eps[i]['title'],
                                      headers, choice, 0)
                    else:
                        choice = main(eps[i]['bvid'], args.thread, new_download_path, args.output, eps[i]['title'],
                                      headers, choice, 1, eps[i]['epid'])
                    time.sleep(0.5)
                    os.system('cls')
            else:
                index = 0
                choice = None
                for i in eps:
                    index += 1
                    print('')
                    print('Video index: {}'.format(str(index)))
                    if args.ssid:
                        choice = main(i['bvid'], args.thread, new_download_path, args.output, i['title'], headers, choice, 0)
                    else:
                        choice = main(i['bvid'], args.thread, new_download_path, args.output, i['title'],
                                      headers, choice, 1, i['epid'])
                    time.sleep(0.5)
                    os.system('cls')
    else:
        print("Can't find ffmpeg.exe. Please put ffmpeg.exe in your working directory.")
        sys.exit(1)
