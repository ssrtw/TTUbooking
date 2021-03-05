from bs4 import BeautifulSoup
import requests
import json
import time
import re


class Booking:
    url_format = "https://stucis.ttu.edu.tw/selcourse/%s"
    mode_map = {1: 'Class', 2: 'General', 3: 'UGRR'}

    def __init__(self):
        self.load_setting()
        self.s = requests.session()
        self.s.headers.update({
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Safari/537.36"
        })
        self.loginAndPrevSetting()

    def load_setting(self):
        # 取得設定內容
        with open("setting.json", 'r', encoding='utf-8') as file:
            self.setting = setting = json.load(file)
        # 設定好登入資訊
        self.login_info = {
            "ID": setting['ID'],
            "PWD": setting['password'],
            "Submit": "%B5n%A4J%A8t%B2%CE",  #登入系統
        }
        self.mode = setting['mode']
        # 如果是剛開放時要搶課，用快速選課
        if setting['mode'] == 0:
            all_course_id = [i for i in setting['general']]
            for i in setting['UGRR']:
                all_course_id.append(i)
            for i in setting['Class']:
                all_course_id.append(i)
            self.fast_data=[]
            for i in range(len(all_course_id)//5+1):
                self.fast_data.append("%0D%0A".join(all_course_id[i*5:i*5+5]))
        elif setting['mode'] == 1:
            self.check_url = Booking.url_format % "ListClassCourse.php"
            self.check_course = setting['Class']
        elif setting['mode'] == 2:
            self.check_url = Booking.url_format % "ListGeneral.php"
            self.check_course = setting['General']
        elif setting['mode'] == 3:
            self.check_url = Booking.url_format % "ListUGRR.php"
            self.check_course = setting['UGRR']

    def save_setting(self):
        with open('setting.json', 'w', encoding='utf-8') as file:
            json.dump(self.setting, file)

    def loginAndPrevSetting(self):
        self.s.get('https://stucis.ttu.edu.tw/login.php')
        self.s.post('https://stucis.ttu.edu.tw/login.php',
                    data=self.login_info)
        self.s.get('https://stucis.ttu.edu.tw/menu/seltop.php')

    def getConfirmVal(self):
        while True:
            r = self.s.get(
                'https://stucis.ttu.edu.tw/selcourse/FastSelect.php')
            soup = BeautifulSoup(r.text, 'lxml')
            queryBtn = soup.find('input', {"type": "submit"})
            if queryBtn != None:
                self.Confirm_val = queryBtn['value']
                break
            else:
                time.sleep(0.8)

    def fast_booking(self):
        # 先檢查快速選課頁面是否有送出按鈕
        self.getConfirmVal()
        # 接著post搶課資料
        for data in self.fast_data:
            self.s.post('https://stucis.ttu.edu.tw/selcourse/FastSelect.php',
                        data={
                            "EnterSbj": data,
                            "Confirm": self.Confirm_val
                        })
            # 怕連續搶課出問題
            time.sleep(0.25)

    def check_booking(self):
        r = self.s.get(self.check_url)
        soup = BeautifulSoup(r.text, 'lxml')
        # 直接找科目代碼在href屬性中元素，有就代表有這堂課能選了
        for course in self.setting[Booking.mode_map[self.mode]]:
            # text那部分其實不確定到底對不對，因加退選時間過了，無法得知真正的網頁元素狀況
            element = soup.find(href=re.compile(course), text="加")
            if element != None:
                self.s.get(
                    "https://stucis.ttu.edu.tw/selcourse/DoAddDelSbj.php?AddSbjNo="
                    + course)
                # 搶到的話就不用繼續check這門課
                self.check_course.remove(course)
                self.save_setting()
        if len(self.check_course) == 0:
            return True
        else:
            return False

    def wait_remain(self):
        notYet = True
        i = 0
        while notYet:
            notYet = self.check_booking()
            i += 1
            print("\r還沒" + (i % 3 + 1) * '.' + '\t(' + str(i) + ")", end="")
            time.sleep(5)

    def booking(self):
        if self.mode == 0:
            self.fast_booking()
        else:
            self.wait_remain()