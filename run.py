#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Created on 2015年3月26日

@author: haoquanbai
'''
import getopt, sys
from optparse import OptionParser
import requests
import time
import json
import pypinyin
from pypinyin import pinyin, lazy_pinyin


# 腾讯API http://blog.csdn.net/ustbhacker/article/details/8365756
# 新浪API http://blog.sina.com.cn/s/blog_58fc3aad01015nu7.html

g_wanted_stock_file_name = "wanted_stock.txt"
g_loc_stock_code_list = []

g_show_chinese_name = False         # 中文股票名
g_show_turnover = False             # 换手率
g_show_main_flow = False            # 主力资金流入率
g_show_retail_flow = False          # 散户资金流入率
g_indexes_code_list = ["sh000001", "sz399005", "sz399006"]


class StockItemInfo(object):
    def __init__(self):
        self.code = ""              # 代码
        self.name = ""              # 股票名称
        self.price = ""             # 当前价
        self.increase = ""          # 涨幅 %
        self.turnover = ""          # 换手率 %
        self.main_flow_rate = ""    # 主力净流入/资金流入流出总和
        self.retail_flow_rate = ""  # 散户净流入/资金流入流出总和
    
    def __str__(self):
        if float(self.increase) >= 0:
            color = "31"
        else:
            color = "32"

        if g_show_chinese_name:    
            name_just = 16 + len(self.name)/len("涨") - 4
            if "*" in self.name:
                name_just -= 1

            stock_name = self.name
        else:
            stock_name = get_stock_alpha_code(self.name)
            name_just = 8
    

        turnover_color = 33 # 黄色
        main_flow_color = 35 # 紫红色
        retail_flow_color = 44 # 蓝色

        main_info_str = "\033[1;%s;40m%s\033[0m" % (color, \
            stock_name.ljust(name_just) + \
            str(self.price.ljust(10)) + \
            str(self.increase.rjust(8))+"%(i)")

        turnover_str = "\033[1;%s;40m%s\033[0m" % (turnover_color, (str(self.turnover).rjust(10)+"%(t)" if g_show_turnover else ""))
        mainflow_str = "\033[1;%s;40m%s\033[0m" % (main_flow_color, (str(self.main_flow_rate).rjust(10)+"%(m)" if g_show_main_flow else ""))
        retailflow_str = "\033[1;%s;40m%s\033[0m" % (retail_flow_color, (str(self.retail_flow_rate).rjust(10)+"%(r)" if g_show_retail_flow else ""))

        return main_info_str + turnover_str + mainflow_str + retailflow_str


def format_loc_stock_code(stock_code):
    loc_stock_code = stock_code
    if len(stock_code) != 0:
        if stock_code[0] == "6":
            loc_stock_code = "sh" + stock_code
        elif stock_code[0] in ["0", "3", "2"]:
            loc_stock_code = "sz" + stock_code
    
    if stock_code == "000001":
        return "sh000001"
        
    return loc_stock_code


def get_stock_alpha_code(hanzi):
    full_width_A = u"\uff21"
    full_width_Z = u"\uff3a"
    result = lazy_pinyin(hanzi.decode("utf-8"), style=pypinyin.FIRST_LETTER)
    alpha_code = ""
    for pinyin in result:
        if pinyin >= full_width_A and pinyin <= full_width_Z:
            alpha_code += chr(ord("A") + ord(pinyin) - ord(full_width_A))
        else:
            alpha_code += pinyin
    
    return alpha_code


def read_wanted_stock(file_path):
    del g_loc_stock_code_list[:]
    with open(file_path, "r") as input_file:
        for line in input_file.readlines():
            if "end" in line:
                break

            stock_code = line.split("\t")[0].strip()
            loc_stock_code = format_loc_stock_code(stock_code)
            if len(loc_stock_code) > 0:
                g_loc_stock_code_list.append(format_loc_stock_code(stock_code))


def refresh_stock_data():
    read_wanted_stock(g_wanted_stock_file_name)
    
    stock_info_map = {}
    stock_info_list = []
    query_str = ",".join(g_loc_stock_code_list)
    request_url = "http://qt.gtimg.cn/q=%s" % query_str
    res_list = requests.get(request_url).text.split(";")
    if "\n" in res_list:
        res_list.remove("\n")

    for res in res_list:
        stock = StockItemInfo()
        info_item_list = res.split("~")
        stock.code = info_item_list[0][info_item_list[0].find("_")+1:info_item_list[0].find("=")]
        stock.name = info_item_list[1].encode("utf-8")
        stock.price = info_item_list[3]
        stock.increase = info_item_list[32] 
        stock.turnover = info_item_list[38]
        stock_info_map.update({stock.code:stock})
        stock_info_list.append(stock)
    
    if g_show_main_flow or g_show_retail_flow:
        temp_list = map(lambda x:"ff_"+x, g_loc_stock_code_list)
        query_str = ",".join(temp_list)
        request_url = "http://qt.gtimg.cn/q=%s" % query_str
        res_list = requests.get(request_url).text.split(";")
        if "\n" in res_list:
            res_list.remove("\n")
        
        for idx,res in enumerate(res_list):
            info_item_list = res.split("~")
            stock = StockItemInfo()
            stock.code = info_item_list[0][info_item_list[0].rfind("_")+1:info_item_list[0].find("=")]
            stock = stock_info_map[stock.code]
            stock.main_flow_rate = info_item_list[4]
            stock.retail_flow_rate = info_item_list[8]
            for idx,stock_item in enumerate(stock_info_list):
                if stock_item.code == stock.code:
                    stock_info_list[idx] = stock
    
    for stock in stock_info_list:
        print stock
    
        
def init_config():
    parser = OptionParser()
    # -c 显示中文名
    parser.add_option("-c", "--chinese",
                  action="store_true", dest="show_chinese", default=False,
                  help="show stock chinese name")   
    
    # -t 显示换手率
    parser.add_option("-t", "--turnover",
                  action="store_true", dest="show_turnover", default=False,
                  help="show stock turnover rate")
    
    # -m 显示主力资金流入率
    parser.add_option("-m", "--mainflow",
                  action="store_true", dest="show_main_flow", default=False,
                  help="show main money flow")
    
    # -r 现在散户资金流入率
    parser.add_option("-r", "--retailflow",
                  action="store_true", dest="show_retail_flow", default=False,
                  help="show retail money flow")
                                                                                                                                                             
    (options, args) = parser.parse_args()
    global g_show_chinese_name, g_show_turnover, g_show_main_flow, g_show_main_flow, g_show_retail_flow
    g_show_chinese_name = options.show_chinese
    g_show_turnover = options.show_turnover
    g_show_main_flow = options.show_main_flow
    g_show_retail_flow = options.show_retail_flow


def run():
    while True:
        try:
            refresh_stock_data()
            print "\n"
        except Exception,e:
            print e 
            time.sleep(1)
        
        time.sleep(3)


if __name__ == '__main__':
    init_config()
    run()
