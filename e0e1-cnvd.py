# -*- coding: utf-8 -*-
import argparse, requests
import os, re
import sys
from concurrent import futures
import pandas as pd
from colorama import Fore
from bs4 import BeautifulSoup
from functools import partial
from yaml import safe_load

requests.packages.urllib3.disable_warnings()


class Config:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        config = safe_load(open(config_path, "r",encoding="utf-8").read())
        self.Cookie = config["cnvd_token"]["cookie"]
        self.ua = config["cnvd_token"]["ua"]

        self.cnvd_bug_file = config["cnvd"]["cnvd-file"]["cnvd_bug_file"]
        self.cnvd_file_xlsx = config["cnvd"]["cnvd-file"]["cnvd_file_xlsx"]
        self.cnvd_product_file = config["cnvd"]["cnvd-file"]["cnvd_product_file"]

        self.cnvd_true_re = config["cnvd"]["cnvd-condition"]["cnvd_true_re"]
        self.edu_file = config["edu"]["edu-file"]

    class Colored(object):
        def red(self, s):
            return Fore.RED + s + Fore.RESET

        def green(self, s):
            return Fore.GREEN + s + Fore.RESET

        def yellow(self, s):
            return Fore.YELLOW + s + Fore.RESET

        def blue(self, s):
            return Fore.BLUE + s + Fore.RESET

        def magenta(self, s):
            return Fore.MAGENTA + s + Fore.RESET


class Cnvd_org:
    def __init__(self):
        self.prams_cnvd = "https://www.cnvd.org.cn"
        self.product_result = []
        self.cp_result = ["厂商", "厂商优化", "绵羊厂商"]
        self.p_count = 1
        self.p_count_all = 500
        self.error_count = 1
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7,ja;q=0.6',
            'User-Agent': Config().ua,
            'Origin': 'https://www.cnvd.org.cn',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Cookie': Config().Cookie,
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': 'Windows',
        }

    def cnvd_get_url(self):
        try:
            print(Config.Colored().magenta(f"开始检索 cnvd厂商列表~~~~"))
            cnvd_result = []
            reqose = self.proxy_req(self.prams_cnvd + "/assetNew/aelectedManuList?offset=1&max=1", False).text
            try:
                all_int = int(int(re.findall(r"共&nbsp;(.*?)&nbsp;条", reqose, re.S)[0]) / 1000)
                print(Config.Colored().magenta(f"总共{all_int}条"))
            except:
                print(Config.Colored().red("token失效或者被waf拦截，请重新搞~~~~~~~"))
                exit(0)

            for i in range(1, all_int + 1):
                reqose = requests.get(self.prams_cnvd + f"/assetNew/aelectedManuList?offset={i}000&max=1000", headers=self.headers, verify=False).text
                if self.cookie_false(reqose):
                    Process_Print(Config().cnvd_file_xlsx).if_xlsx_file(cnvd_result, ["厂商名"], "厂商")
                    exit(0)
                soup = BeautifulSoup(reqose, "lxml")
                td_elements = soup.find_all('td')
                for td in td_elements:
                    cnvd_result.append([td.get_text(strip=True)])
                print(Config.Colored().green(f"正在检索第{i}页~~~~"))
            cnvd_result = [item for item in cnvd_result if item != ['']]
            Process_Print(Config().cnvd_file_xlsx).if_xlsx_file(cnvd_result, ["厂商名"], "厂商")
            print(Config.Colored().yellow(f"检索完成已保存至{Config().cnvd_bug_file}-厂商 表中~~"))
        except Exception as e:
            print(Config.Colored().red(str(e)))

    def cnvd_get_product(self, cnvd_tart):
        try:
            cnvd_data = {
                "manuName": cnvd_tart,
                "manuId": "",
            }

            cnvd_reqs = self.proxy_req(self.prams_cnvd + "/assetNew/aelectedProductCategoryList", data=cnvd_data).text
            # print(cnvd_reqs)
            if self.cookie_false(cnvd_reqs):
                try:
                    Process_Print(Config().cnvd_product_file).add_xlsx_file(self.product_result, ["厂商名", "厂商产品"], self.cp_result[int(args.Cnvd_product_int) - 1]+"-产品")
                except:
                    pass
                os._exit(0)

            soup = BeautifulSoup(cnvd_reqs, "lxml")
            td_elements = soup.find_all("td")
            for td in td_elements:
                if str(td.get_text(strip=True)) != "":
                    self.product_result.append([cnvd_tart, td.get_text(strip=True)])
            print(Config.Colored().green(f"检测了该公司产品：{cnvd_tart}"))

            self.p_count += 1
            if self.p_count % self.p_count_all == 0:
                Process_Print(Config().cnvd_product_file).add_xlsx_file(self.product_result, ["厂商名", "厂商产品"], self.cp_result[int(args.Cnvd_product_int) - 1]+"-产品")
                print(Config.Colored().yellow(f"检测了{self.p_count_all}个厂商,进行保存中~~~"))
                self.product_result.clear()
        except Exception as e:
            print(Config.Colored().red(str("出现报错，大概率为超时~~~")))
            print(Config.Colored().red(e))

    def product_list(self):
        cnvd_product_file = Config().cnvd_product_file
        cnvd_file_xlsx = Config().cnvd_file_xlsx

        try:
            if str(args.Cnvd_product_int) in ["1", "2", "3"]:
                index = int(args.Cnvd_product_int) - 1
                sheet_name = self.cp_result[index]
            else:
                print(Config.Colored().red("厂商选择输入错误,请输入1、2、3"))
                exit(0)

            if os.path.isfile(cnvd_product_file):
                excel_file = pd.ExcelFile(cnvd_product_file)
                cnvd_df = pd.read_excel(pd.ExcelFile(cnvd_file_xlsx), header=0, sheet_name=sheet_name)
                old_list = cnvd_df.iloc[:, 0].tolist()

                if sheet_name+"-产品" in excel_file.sheet_names:
                    all_list = pd.read_excel(cnvd_product_file, header=0, sheet_name=sheet_name + "-产品").iloc[:, 0].tolist()
                    if len(all_list) > 500:
                        print(Config.Colored().magenta(f"检测存在《{sheet_name}》该表，进行去重中~~~~"))
                        cnvd_file = [item for item in old_list if item not in all_list]
                    else:
                        cnvd_file = old_list
                else:
                    Process_Print(cnvd_product_file).add_xlsx_file([["", ""]], ["厂商", "产品"], sheet_name + "-产品")
                    cnvd_df = pd.read_excel(cnvd_file_xlsx, header=0, sheet_name=sheet_name)
                    cnvd_file = cnvd_df.iloc[:, 0].tolist()
            else:
                Process_Print(cnvd_product_file).all_xlsx_file([["", ""]], ["厂商", "产品"], sheet_name + "-产品")
                cnvd_df = pd.read_excel(cnvd_file_xlsx, header=0, sheet_name=sheet_name)
                cnvd_file = cnvd_df.iloc[:, 0].tolist()
            return cnvd_file
        except Exception as e:
            print(Config.Colored().red(str(e)))

    def th_product_main(self):
        try:
            print(Config.Colored().magenta("开始检索产品~~~~"))
            cnvd_file = self.product_list()

            with futures.ThreadPoolExecutor(max_workers=2) as executor:
                executor.map(self.cnvd_get_product, cnvd_file)
        except Exception as e:
            print(Config.Colored().red(str("th_product_main bug: {}".format(e))))

    def cnvd_get_parms(self, typeId, sheet_bug):
        try:
            print(Config.Colored().magenta(f"开始检索 {sheet_bug}列表~~~~~"))
            bug_result = []
            reqose = self.proxy_req(self.prams_cnvd + f"/flaw/typeResult?typeId={typeId}&max=10&offset=10", False).text
            try:
                all_int = int(int(re.findall(r"共&nbsp;(.*?)&nbsp;条", reqose, re.S)[0]) / 100)
                print(Config.Colored().magenta(f"总共{all_int}条"))
            except:
                print(Config.Colored().red("token失效或者被waf拦截，请重新搞~~~~~~~"))
                exit(0)

            for i in range(1, all_int + 1):
                reqose = self.proxy_req(self.prams_cnvd + f"/flaw/typeResult?typeId={typeId}&max=100&offset={i}00", False).text
                if self.cookie_false(reqose):
                    Process_Print(Config().cnvd_bug_file).if_xlsx_file(bug_result, ["漏洞标题"], sheet_bug)
                    exit(0)
                soup = BeautifulSoup(reqose, "lxml")
                a_elements = soup.find_all('a')
                for a_tag in a_elements:
                    try:
                        bug_result.append([a_tag["title"]])
                    except:
                        pass
                print(Config.Colored().green(f"开始检索第{i}页~~"))
            Process_Print(Config().cnvd_bug_file).if_xlsx_file(bug_result, ["漏洞标题"], sheet_bug)
            print(Config.Colored().yellow(f"检索完成已保存至{Config().cnvd_bug_file}-{sheet_bug} 表中~~"))
        except Exception as e:
            print(Config.Colored().red(str(e)))

    def cnvd_sheep(self):
        try:
            print(Config.Colored().magenta("开始检索 绵羊列表~~~~~"))
            sheep_list = []
            repose = self.proxy_req('https://www.cnvd.org.cn/sheepWall/list', False).text
            # print(repose)
            try:
                all_int = int(int(re.findall(r"共&nbsp;(.*?)&nbsp;条", repose, re.S)[0]) / 100)
                print(Config.Colored().magenta(f"总共{all_int}条"))
            except:
                print(Config.Colored().red("token失效或者被waf拦截，请重新搞~~~~~~~"))
                exit(0)

            for i in range(1, all_int + 1):
                repose = self.proxy_req(self.prams_cnvd + f"/sheepWall/list?max=100&offset={i}00", False).text
                if self.cookie_false(repose):
                    if not sheep_list:
                        print(Config.Colored().red("结果为空不做保存"))
                    else:
                        Process_Print(Config().cnvd_file_xlsx).if_xlsx_file(sheep_list, ["厂商"], "绵羊厂商")
                    exit(0)
                soup = BeautifulSoup(repose, "lxml")
                td_list = soup.find_all("td", width="30%")
                for td_tar in td_list:
                    sheep_list.append(td_tar.get_text(strip=True))
                print(Config.Colored().green(f"开始检索第{i}页~~"))
            sheep2_list = [[tar] for tar in list(set(sheep_list))]
            Process_Print(Config().cnvd_file_xlsx).if_xlsx_file(sheep2_list, ["厂商"], "绵羊厂商")
            print(Config.Colored().yellow(f"检索完成已保存至{Config().cnvd_file_xlsx}-绵羊厂商 表中~~"))
        except Exception as e:
            print(Config.Colored().red(str(e)))

    def cookie_false(self, html_text):
        try:
            if any(waf in str(BeautifulSoup(html_text, "lxml").find_all("script")[0]) for waf in ["<script>document.cookie", "创宇【创宇盾】产品"]):
                print(Config.Colored().red("token失效或者触发了waf，请重新搞~~~~~~~"))
                return True
            else:
                return False
        except Exception as e:
            print(Config.Colored().red(str(e)))
            return True

    def proxy_req(self, poc_url, data):
        try:
            proxy = {
                "http": args.Proxy_tf,
                "https": args.Proxy_tf
            }
            if args.Proxy_tf:
                if data:
                    repose = requests.post(poc_url, data=data, headers=self.headers, proxies=proxy, timeout=10, verify=False)
                else:
                    repose = requests.get(poc_url, headers=self.headers, proxies=proxy, timeout=10, verify=False)
            else:
                if data:
                    repose = requests.post(poc_url, data=data, headers=self.headers, timeout=10, verify=False)
                else:
                    repose = requests.get(poc_url, headers=self.headers, timeout=10, verify=False)
            return repose
        except Exception as e:
            print(Config.Colored().red(str(str(e))))


class CNVD_plus:
    def cnvd_url_plus(self):
        try:
            result = []
            print(Config.Colored().magenta("正在执行公司过滤优化~~"))
            excel_file = pd.ExcelFile(Config().cnvd_file_xlsx).sheet_names
            if "厂商" in excel_file:
                cnvd_df = pd.read_excel(Config().cnvd_file_xlsx, header=0, sheet_name="厂商")
                cnvd_file = cnvd_df.iloc[:, 0].tolist()
                for cn_tar in cnvd_file:
                    if any(keyword in str(cn_tar) for keyword in Config().cnvd_true_re):
                        result.append([str(cn_tar)])
                Process_Print(Config().cnvd_file_xlsx).add_xlsx_file(result, ["厂商"], "厂商优化")
                print(Config.Colored().yellow("过滤完成~~"))
            else:
                print(Config.Colored().red("检测不存在《厂商》该表，请先检索厂商"))
                exit(0)
        except Exception as e:
            print(Config.Colored().red(str(e)))


class Edu_org:
    def __init__(self):
        self.edu_parms_url = "https://src.sjtu.edu.cn/list/firm/new/"
        self.edu_gongsi_url = "https://src.sjtu.edu.cn/rank/company/"
        self.edu_result = []

    def edu_get_parms(self, page, edu_url):
        try:
            parms_list = requests.get(edu_url + f"?page={page}", verify=False)
            soup = BeautifulSoup(parms_list.text, 'lxml')
            td_a_tags = soup.select('td a')
            for tag in td_a_tags:
                self.edu_result.append([tag.text])
            print(Config.Colored().green(f"正在读取第{page}页"))
        except Exception as e:
            print(Config.Colored().red(str(f"edu_get_parms bug:{e}")))

    def edu_get_parms_main(self, edu_url, edu_sheet):
        print(Config.Colored().magenta("开始检索edusrc列表~~~"))
        max_list = list(range(1, int(BeautifulSoup(requests.get(edu_url, verify=False).text, "lxml").select('li a')[-2].text) + 1))

        fixed_url_func = partial(self.edu_get_parms, edu_url=edu_url)

        with futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fixed_url_func, max_list)

        if os.path.isfile(Config().edu_file):
            Process_Print(Config().edu_file).add_xlsx_file(self.edu_result, [edu_sheet], edu_sheet)
            print(Config.Colored().yellow(f"文件存在,在{Config().edu_file} 另起一页{edu_sheet} 保存内容"))
        else:
            Process_Print(Config().edu_file).all_xlsx_file(self.edu_result, [edu_sheet], edu_sheet)
            print(Config.Colored().yellow(f"保存文件，在{Config().edu_file},{edu_sheet}页面中"))

    def edu_main(self):
        if args.Edu_tf:
            self.edu_get_parms_main(self.edu_parms_url, "单位")
        if args.EduC_tf:
            self.edu_get_parms_main(self.edu_gongsi_url, "厂商公司")


class Process_Print:
    def __init__(self, file_path):
        self.file_path = file_path

    def all_xlsx_file(self, data, columns_name, sheet_name="all"):
        df = pd.DataFrame.from_records(data)
        df.columns = columns_name
        with pd.ExcelWriter(self.file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    def add_xlsx_file(self, data, columns_name, sheet_name="all"):
        df = pd.DataFrame.from_records(data)
        df.columns = columns_name
        with pd.ExcelWriter(self.file_path, engine="openpyxl", mode='a', if_sheet_exists="overlay") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    def if_xlsx_file(self, data, columns_name, sheet_name):
        if os.path.isfile(self.file_path):
            self.add_xlsx_file(data, columns_name, sheet_name)
        else:
            self.all_xlsx_file(data, columns_name, sheet_name)


def args_port():
    try:
        parser = argparse.ArgumentParser(description='eeeeee input')
        parser.add_argument('--cnvd', dest='Cnvd_tf', action='store_true', help='获取cnvd厂商')
        parser.add_argument('--url-plus', dest='Url_tf', action='store_true', help='对cnvd厂商列表进行优化')
        parser.add_argument('--cnvd-sheep', dest='sheep_tf', action='store_true', help='获取cnvd 绵羊厂商')
        parser.add_argument('--product-int', dest='Cnvd_product_int', default="1", help="输入1、2、3，分别代表获取 厂商、优化后的厂商、绵羊厂商 的产品，默认为1")
        parser.add_argument('--cn-web', dest='Cnvd_web_tf', action='store_true', help='获取cnvd web应用漏洞列表')
        parser.add_argument('--cn-apply', dest='Cnvd_apply_tf', action='store_true', help='获取cnvd 应用程序漏洞列表')
        parser.add_argument('--cn-system', dest='Cnvd_system_tf', action='store_true', help='获取cnvd 操作系统漏洞列表')
        parser.add_argument('--cn-database', dest='Cnvd_database_tf', action='store_true', help='获取cnvd 数据库漏洞列表')
        parser.add_argument('--cn-ment', dest='Cnvd_ment_tf', action='store_true', help='获取cnvd 网络设备漏洞列表')
        parser.add_argument('--edu-danwei', dest='Edu_tf', action='store_true', help='获取edusrc的单位')
        parser.add_argument('--edu-chang', dest='EduC_tf', action='store_true', help='获取edusrc的被提交的漏洞公司单位')
        parser.add_argument('--proxy', dest='Proxy_tf', default=False, help='设置代理，举例：http://127.0.0.1:5555')
        args = parser.parse_args()
        return args
    except Exception as e:
        print("args_port bugs: {}".format(e))


def main_task():
    cnvd_org = Cnvd_org()
    cnvd_plus = CNVD_plus()
    edu_org = Edu_org()
    task_items = {
        "Cnvd_tf": cnvd_org.cnvd_get_url,
        "Cnvd_product_int": cnvd_org.th_product_main,
        "sheep_tf": cnvd_org.cnvd_sheep,
        "Url_tf": cnvd_plus.cnvd_url_plus,
        "Cnvd_web_tf": lambda: cnvd_org.cnvd_get_parms(29, "web应用"),
        "Cnvd_apply_tf": lambda: cnvd_org.cnvd_get_parms(28, "应用程序"),
        "Cnvd_system_tf": lambda: cnvd_org.cnvd_get_parms(27, "操作系统"),
        "Cnvd_database_tf": lambda: cnvd_org.cnvd_get_parms(30, "数据库"),
        "Cnvd_ment_tf": lambda: cnvd_org.cnvd_get_parms(31, "网络设备"),
        "Edu_tf": edu_org.edu_main,
        "EduC_tf": edu_org.edu_main,
    }

    print(Config.Colored().green('''
     ------------------------------------------------
    |        ___       _                          _  |
    |   ___ / _ \  ___/ |       ___ _ ____   ____| | |
    |  / _ \ | | |/ _ \ |_____ / __| '_ \ \ / / _` | |
    | |  __/ |_| |  __/ |_____| (__| | | \ V / (_| | |
    |  \___|\___/ \___|_|      \___|_| |_|\_/ \__,_| |
    |               -- by: eeeeee --                 |         
    |      -- 该工具仅用于学习参考，均与作者无关 --  |              
     ------------------------------------------------
   |下载地址：https://github.com/eeeeeeeeee-code/e0e1-cnvd |
    -----------------------------------------------------
           '''))

    for arg, action in task_items.items():
        if getattr(args, arg, False):
            action()


if __name__ == "__main__":
    global args
    args = args_port()
    main_task()
