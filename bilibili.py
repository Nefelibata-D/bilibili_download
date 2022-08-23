import requests
import os
import time
import qrcode
import json
from bs4 import BeautifulSoup
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn, BarColumn, TimeRemainingColumn, TextColumn, TimeElapsedColumn
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys

def login(headers:dict):
    """
    模拟B站二维码登录功能, 获取用户cookies有效内容
    cookies 有效时间应在 15d-30d
    """

    login_url = 'https://passport.bilibili.com/qrcode/getLoginUrl'  #  获取登录二维码
    res = requests.get(url = login_url, headers = headers)
    qrcode_url = res.json()['data']['url']  #  登录二维码所含内容
    oauth_key = res.json()['data']['oauthKey']
    img = qrcode.make(qrcode_url)

    with open ('./qrcode.png', 'wb') as file:
        img.save(file)
    os.system('start qrcode.png')

    login_info_url = 'https://passport.bilibili.com/qrcode/getLoginInfo?oauthKey={}'.format(oauth_key)  #  二维码状态获取
    cookies = ''
    for i in range(60):  #  等待用户登录扫码, 等待时间60s
        res = requests.post(url = login_info_url, headers = headers)
        if res.json()['status']:
            user = res.json()['data']['url']
            for n in user.split('?')[1].split('&gourl')[0].split('&'):  #  获取cookies有效参数
                cookies += n + ';'
            break
        time.sleep(1)
    os.system('del qrcode.png')

    if not cookies:
        return None

    return cookies

def set_config(cookies, path):
    # 保存用户登录信息
    mid = cookies.split(';')[0].split('=')[1]
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    cof = {
        'mid': mid,
        'cookies': cookies,
        'timestamp': timestamp
    }

    with open('{}\config.json'.format(path), 'w') as file:
        file.write(json.dumps(cof))

    return None

def bvid_to_cid(bvid:int, headers:dict):
    url = 'https://api.bilibili.com/x/player/pagelist?bvid={}'.format(bvid)
    res = requests.get(url=url, headers=headers)
    cid = res.json()['data'][0]['cid']

    return cid

def get_aid(bvid:int, cid:int, headers:dict, name:str):
    url = 'https://api.bilibili.com/x/web-interface/view?cid={}&bvid={}'.format(cid, bvid)
    res = requests.get(url = url, headers=headers)
    aid = res.json()['data']['aid']
    if name != '':
        file_name = name
    else:
        file_name = res.json()['data']['title']

    return aid, file_name

def heartbeat(aid:int, mid:int, cid:int, headers:dict):
    #  ttl握手, 目前不起作用, 不知后期是否会作为反爬虫判定
    url = 'https://api.bilibili.com/x/click-interface/web/heartbeat?mid={}&aid={}&cid={}'.format(mid, aid, cid)
    res = requests.post(url=url, headers=headers)

    return res.json()['ttl']

def detail(bvid:str, cid:int, headers:dict, qn=112):
    #  fourk为4k请求参数, fnval=4048为8k请求参数
    #  |"超高清 8K", 127         |"超清 4K", 120   
    #  |"高清 1080P60", 116      |"高清 1080P+", 112    
    #  |"高清 1080P", 80         |"高清 720P", 64    
    #  |"清晰 480P", 32          |"流畅 360P" 16
    url = 'https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&qn={}&fourk=1&fnval=4048'.format(bvid, cid, qn)
    res = requests.get(url=url, headers=headers)
    if qn not in res.json()['data']['accept_quality']:
        print("Can't find the video quality")
        sys.exit(1)
    else:
        video_inf = res.json()['data']['dash']['video']
        for i in video_inf:
            if i['id'] == qn:
                video_url = i['baseUrl']
                # 音频链接有多个, 这里只取了最高音质
                audio_url = res.json()['data']['dash']['audio'][0]['baseUrl']
                return video_url, audio_url

class Download_threader:
    def __init__(self, url:str, cookie:str, size:int, thread:int, progress, task, file_name:str, download_path:str):
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
    
    def download_parts(self, part:int, cookie:str, Range:str):
        # 视频分片下载
        headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1336.2',
        'Referer': 'https://www.bilibili.com/',
        'Cookie': cookie,
        'Range': Range  # 指定视频分片链接
    }   
        res = requests.get(url=self.url, headers=headers, stream=True)  # 流式下载视频
        with open('{}\part{}.tmp'.format(self.download_path, part), 'wb') as file:
            for i in res.iter_content(chunk_size= 64 * 1024):
                file.write(i)
                file.flush()
                self.get_size += len(i)  # 更新视频已经下载大小
                time.sleep(0.005)  # 防线程堵塞, 可注释
    
    def copy_tmps(self):
        # 分片视频合并
        for i in range(self.thread):
            with open('{}\part{}.tmp'.format(self.download_path, i), 'rb') as tmp:
                content = tmp.read()
            os.remove('{}\part{}.tmp'.format(self.download_path, i))
            with open('{}\{}.m4s'.format(self.download_path, self.file_name), 'ab+') as file:
                file.write(content)
                file.flush()
    
    def download_thread(self):
        # 多线程下载
        futures = []
        tp = ThreadPoolExecutor(max_workers=self.thread)
        for i in range(self.thread):
            if i < self.thread -1:
                Range = 'bytes={}-{}'.format(int(self.file_size/self.thread) * i, int(self.file_size/self.thread) * (i + 1) - 1)
            else:
                if self.file_name == 'video':
                    Range = 'bytes={}-{}'.format(int(self.file_size/self.thread) * i, self.file_size)
                else:
                    Range = 'bytes={}-{}'.format(int(self.file_size/self.thread) * i, self.file_size-1)  # 请求音频有概率出现不能分片问题
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

def ep(headers, epid):
    # 番剧批量视频链接获取, 批量下载尚未支持
    res = requests.get('https://www.bilibili.com/bangumi/play/ep{}'.format(epid), headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    for i in soup.find_all('script'):
        if 'window.__INITIAL_STATE__' in str(i):
            inf = json.loads(str(i).split('</script>')[0].split('window.__INITIAL_STATE__=')[1].split(';(function')[0])
            break
    
    inf = inf['mediaInfo']['episodes']
    episodes = []

    for ep in inf:
        ep_inf = {
            # 'aid' : ep['aid'],
            # 'name' : ep['name'],
            # 'cid' : ep['cid'],
            'bvid' : ep['bvid'],
            'share_copy' : ep['share_copy'],
        }
        episodes.append(ep_inf)
    
    return episodes

def main(bvid:str, qn:int, thread:int, download_path:str, output:int, name:str, headers:dict):
    if os.path.exists('{}\config.json'.format(os.path.dirname(os.path.realpath(__file__)))):
        print('Find config.json')
        with open('{}\config.json'.format(os.path.dirname(os.path.realpath(__file__))), 'r') as file:
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

    mid = cookies.split(';')[0].split('=')[1]
    cid = bvid_to_cid(bvid, headers)
    aid , file_name = get_aid(bvid, cid, headers, name)   
    # ttl = heartbeat(aid, mid, cid, headers)

    tuple = detail(bvid, cid, headers, qn)
    print('')
    print("File name: " + file_name)
    print('')

    if tuple:
        with Progress(TextColumn('{task.description}'), DownloadColumn(binary_units = True), BarColumn(), TransferSpeedColumn(), '·' , TimeRemainingColumn(), '·', TimeElapsedColumn()) as progress:
            res = requests.get(url=tuple[0], headers = headers, stream=True)
            size = res.headers['Content-Length']
            task = progress.add_task('Downloading_Video...', total = int(size))
            download_threader = Download_threader(tuple[0], headers['Cookie'], int(size), thread, progress, task, 'video', download_path)
            download_threader.download_thread()
        with Progress(TextColumn('{task.description}'), DownloadColumn(binary_units = True), BarColumn(), TransferSpeedColumn(), '·' , TimeRemainingColumn(), '·', TimeElapsedColumn()) as progress:
            res = requests.get(url=tuple[1], headers = headers, stream=True)
            size = res.headers['Content-Length']
            task = progress.add_task('Downloading_Audio...', total = int(size))
            download_threader = Download_threader(tuple[1], headers['Cookie'], int(size), thread, progress, task, 'audio', download_path)
            download_threader.download_thread()
    print('Combining...')
    if output:
        os.system(r"{0}\\ffmpeg.exe -i {1}\\video.m4s -i {1}\\audio.m4s -c copy {1}\\output.mp4 ".format(os.path.dirname(os.path.realpath(__file__)), download_path))
    else:
        os.system(r"{0}\\ffmpeg.exe -i {1}\\video.m4s -i {1}\\audio.m4s -c copy {1}\\output.mp4 -loglevel quiet".format(os.path.dirname(os.path.realpath(__file__)), download_path))
    os.remove(r'{}\\video.m4s'.format(download_path))
    os.remove(r'{}\\audio.m4s'.format(download_path))
    os.rename('{}\\output.mp4'.format(download_path), '{}\\{}.mp4'.format(download_path, file_name))
    print('Done')

# cmd 输入参数
parser = argparse.ArgumentParser(description='bilibili download ')
parser.add_argument('-b', '--bvid', type=str, help="指定视频BV号")
parser.add_argument('-q', '--qn',  type=int, choices=[16,32,64,80,112,116,120,127], help="超高清8K:127 超清4K:120 1080P60:116 1080P+:112 1080P:80 720P:64 480P:32 320P:16")
parser.add_argument('-t', '--thread',  type=int, default=8, choices=[2,4,8,16,32], help='下载线程数, 默认为8')
parser.add_argument('-n', '--name',  type=str, default = '', help='对下载视频重新命名')
parser.add_argument('-e', '--epid',  type=str, help='指定番剧号')
parser.add_argument('-l', '--login', action='store_true', default=False, help='仅登录')
parser.add_argument('-o', '--output', action='store_true', default=False, help='保留ffmpeg输出')

args = parser.parse_args()

if __name__ == '__main__':
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1336.2',
        'Referer': 'https://www.bilibili.com/'
    } 
    if args.login:
        login(headers)
        print('Login successful. Login cookies is saved to config.json.')
        sys.exit(0)    
    if args.bvid==None and args.epid==None:
        print('Please enter BVID or EPID')
        print("Use 'python bilibili.py -h' to show helps.")
        sys.exit(1)
    if args.qn==None:
        print('Please enter the video quality.')
        print("Use 'python bilibili.py -h' to show helps.")
        sys.exit(1)

    download_path = os.path.dirname(os.path.realpath(__file__)) + r'\Download'
    try:
        os.mkdir(download_path)  # 创建下载目录
    except FileExistsError:
        pass
    print('Download Directory : ' + download_path)
    print('')
    
    if os.path.exists(os.path.dirname(os.path.realpath(__file__)) + r'\\ffmpeg.exe'):
        if args.bvid:
            main(args.bvid, args.qn, args.thread, download_path, args.output, args.name, headers)
        if args.epid:
            for i in ep(headers, args.epid):
                print('=================================================')
                main(i['bvid'], args.qn, args.thread, download_path, args.output, i['share_copy'], headers)
                print('')
    else:
        print("Can't find ffmpeg.exe. Please put ffmpeg.exe in your working directory.")
        sys.exit(1)