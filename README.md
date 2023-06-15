<<<<<<< HEAD
# Bilibili-Download
一个基于python编写的B站视频下载器

## 1. 项目使用的第三方库
* beautifulsoup4
* requests
* qrcode
* rich

安装项目所需第三方库：

    pip install -r requirements.txt

## 2. 使用说明
### 2.1 相关参数

    -h, --help     查看帮助信息
    -b, --bvid     视频BV号
    -e, --epid     番剧EP号
    -q, --qn       视频质量(required), 支持参数为[16, 32, 64, 80, 112, 116, 120, 127]
    -n, --name     视频重新命名
    -l, --login    仅登录, 生成config.json文件
    -t, --thread   下载视频线程数, 默认为8线程, 支持线程数为[2, 4, 8, 16, 32]
    -o, --output   允许ffmpeg输出视频合并日志
    -s, --start    番剧批量下载开始集数
    -f, --final    番剧批量下载结束集数
    
### 2.2 视频质量（qn）参数说明

    "超高清 8K", 127         "超清 4K", 120   
    "高清 1080P60", 116      "高清 1080P+", 112    
    "高清 1080P", 80         "高清 720P", 64    
    "清晰 480P", 32          "流畅 360P" 16

### 2.3 使用方法

    python bilibili.py [OPTIONS]

    examples:
        python bilibili.py -b BV1E44y1t7Kn -q 120
        python bilibili.py -b BV1E44y1t7Kn -q 120 -n test -t 16 -o
        python bilibili.py -e 400972 -q 80 
        python bilibili.py -e 400972 -q 80 -s 2 -f 4

## 3. Tips
* 目前已经支持番剧批量下载，番剧批量下载指定集数，需要输入番剧的ep号

    链接示例: 'https://www.bilibili.com/bangumi/play/ep400973' [ep号为400973]

    请用网页端打开番剧后再次选择任意一集，即可获取到ep号
* 音频目前获取的默认为最高质量音频，未提供可选择接口，若有需求，可自行更改源码

    ```python
    # line 85
    def detail(bvid:str, cid:int, headers:dict, qn=112):
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
                    audio_url = res.json()['data']['dash']['audio'][0]['baseUrl']  #  此处可以更改音频获取链接, 将[0]改成其他索引即可，建议索引范围在0~2
                    return video_url, audio_url
    ```
* 目前B站cookies获取方式为二维码登录，cookies有效期在15天-30天之间，建议定期重新登录
* 番剧BV号获取方法：
=======
# Bilibili-Download

一个基于python编写的B站视频下载器

## 1. 项目使用的第三方库

* beautifulsoup4
* requests
* qrcode
* rich

安装项目所需第三方库：

    pip install -r requirements.txt

## 2. 使用说明

### 2.1 相关参数

    -h, --help     查看帮助信息
    -b, --bvid     视频BV号
    -e, --epid     番剧EP号
    -q, --qn       视频质量(required), 支持参数为[16, 32, 64, 80, 112, 116, 120, 127]
    -n, --name     视频重新命名
    -l, --login    仅登录, 生成config.json文件
    -t, --thread   下载视频线程数, 默认为8线程, 支持线程数为[2, 4, 8, 16, 32]
    -o, --output   允许ffmpeg输出视频合并日志
    -s, --start    番剧批量下载开始集数
    -f, --final    番剧批量下载结束集数

### 2.2 视频质量（qn）参数说明

    "超高清 8K", 127         "超清 4K", 120   
    "高清 1080P60", 116      "高清 1080P+", 112    
    "高清 1080P", 80         "高清 720P", 64    
    "清晰 480P", 32          "流畅 360P" 16

### 2.3 使用方法

    python bilibili.py [OPTIONS]
    
    examples:
        python bilibili.py -b BV1E44y1t7Kn -q 120
        python bilibili.py -b BV1E44y1t7Kn -q 120 -n test -t 16 -o
        python bilibili.py -e 400972 -q 80 
        python bilibili.py -e 400972 -q 80 -s 2 -f 4

## 3. Tips

* 目前已经支持番剧批量下载，番剧批量下载指定集数，需要输入番剧的ep号
  
    链接示例: 'https://www.bilibili.com/bangumi/play/ep400973' [ep号为400973]
  
    请用网页端打开番剧后再次选择任意一集，即可获取到ep号

* 音频目前获取的默认为最高质量音频，未提供可选择接口，若有需求，可自行更改源码
  
  ```python
  # line 85
  def detail(bvid:str, cid:int, headers:dict, qn=112):
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
                  audio_url = res.json()['data']['dash']['audio'][0]['baseUrl']  #  此处可以更改音频获取链接, 将[0]改成其他索引即可，建议索引范围在0~2
                  return video_url, audio_url
  ```

* 目前B站cookies获取方式为二维码登录，cookies有效期在15天-30天之间，建议定期重新登录

* 番剧BV号获取方法：
>>>>>>> 0f4a33f (add vision 1.0.1)
    在网页端打开想要下载的番剧，浏览器全屏后，可以在番剧介绍处找到BV号