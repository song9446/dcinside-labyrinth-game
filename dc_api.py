#!/usr/bin/python3

import sys
import requests
import re
from datetime import timedelta, date, datetime
import json
import time
import urllib
import urllib.parse
import vpn
import random
#from collections import OrderedDict
#import logging
#logging.basicConfig(level=logging.DEBUG)

from pprint import pprint

GET_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Mobile Safari/537.36",
    "Upgrade-Insecure-Requests": "1",
    "Host": "m.dcinside.com",
    "Connection": "keep-alive",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }

POST_HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Host": "m.dcinside.com",
    "Origin": "http://m.dcinside.com",
    "Referer": "http://m.dcinside.com/write.php?id=alphago&mode=write",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Mobile Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    }

def _post(sess, url, data=None, json=None, **kwargs):
    res = None
    while not res:
        try:
            res = sess.post(url, data=data, json=json, **kwargs)
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.TooManyRedirects:
            pass
        except Exception as e:
            raise(e)
    return res

def _get(sess, url, **kwargs):
    res = None
    while not res:
        try:
            res = sess.get(url, **kwargs)
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.TooManyRedirects:
            pass
        except Exception as e:
            raise(e)
    return res

def upvote(board, is_miner, doc_no, num=1, sess=None):
    if num>1:
        def f():
            f.n += upvote(board, is_miner, doc_no)
        f.n = 0
        #vpn.do(lambda: n += upvote(board, is_miner, doc_no), num)
        vpn.do(f, num)
        return f.n
    else:
        if sess is None:
            sess = requests.session()
        url = "http://m.dcinside.com/view.php?id=%s&no=%s" % (board, doc_no)
        res = _get(sess, url, headers=GET_HEADERS, timeout=3)
        _, s = raw_parse(res.text, "function join_recommend()", "{")
        _, e = raw_parse(res.text, "$.ajax", "{", s)
        cookie_name, _ = raw_parse(res.text, 'setCookie_hk_hour("', '"', s)
        sess.cookies[cookie_name] = "done"
        data = {}
        while s < e:
            nv, s = raw_parse(res.text, '= "', '"', s)
            if s >= e: break
            nv= nv.split("=")
            data[nv[0] if nv[0][0] != "&" else nv[0][1:]] = nv[1] or "undefined"
        headers = POST_HEADERS.copy()
        headers["Referer"] = url
        headers["Accept-Language"] = "en-US,en;q=0.9"
        url = "http://m.dcinside.com/_recommend_join.php"
        res = _post(sess, url, headers=headers, data=data, timeout=3)
        return ':"1"' in res.text

def iterableBoard(board, is_miner=False, num=-1, start_page=1, sess=None):
    # create session
    if sess is None:
        sess = requests.session()
    url = "http://m.dcinside.com/list.php"
    params = { "id": board, "page": str(start_page) }
    i = 0
    last_doc_no = 0
    doc_in_page = 0
    page = start_page
    header = GET_HEADERS.copy()
    header["Referer"] = url
    while num != 0:
        params["page"] = str(page)
        res = _get(sess, url, headers=header, params=params, timeout=3)
        t, start = raw_parse(res.text, '"list_best">', "<", i)
        t, end = raw_parse(res.text, "</ul", ">", start)
        i = start
        while num != 0 and i < end and i >= start:
            doc_no, i = raw_parse(res.text, 'no=', '&', i)
            if i >= end or i == 0:
                break
            doc_no = int(doc_no)
            if last_doc_no != 0 and doc_no >= last_doc_no:
                continue
            last_doc_no = doc_no
            t, i = raw_parse(res.text, 'ico_pic ', '"', i)
            has_image = (t == "ico_p_y")
            title, i = raw_parse(res.text, 'txt">', '<', i)
            t, i = raw_parse(res.text, 'txt_num">', "<", i)
            comments = int(t[1:-1]) if len(t)>0 else 0
            name, i = raw_parse(res.text, 'name">', "<", i)
            t, i = raw_parse(res.text, 'class="', '"', i)
            ip = None
            if t == "userip":
                ip, i = raw_parse(res.text, '>', '<', i) 
            date, i = raw_parse(res.text, "<span>", "<", i)
            t, i = raw_parse(res.text, '조회', "<", i)
            views, i = raw_parse(res.text, '>', '<', i)
            t, i = raw_parse(res.text, '추천', "<", i)
            votes, i = raw_parse(res.text, '>', '<', i)
            yield {
                "doc_no": doc_no, "title": title, "name": name, "ip": ip, "date": date, "views": int(views), "votes": int(votes), "comments": int(comments)
                }
            num -= 1
        page += 1
        
def iterableComments(board, is_miner, doc_no, num=-1, sess=None):
    if sess is None:
        sess = requests.session()
    referer = "http://m.dcinside.com/view.php?id=%s&no=%s" % (board, doc_no)
    url = "http://m.dcinside.com/%s/comment_more_new.php" % ("m" if is_miner else "")
    page = 1
    params = {"id": board, "no": str(doc_no), "com_page": str(page)}
    headers = GET_HEADERS.copy()
    headers["Referer"] = referer
    num_comments, i, count = 999999999,0,0
    
    while num != 0:
        params["com_page"] = str(page)
        res = _get(sess, url, headers=headers, params=params, timeout=3)
        t, i = raw_parse(res.text, 'txt_total">(', ')', i)
        if i==0: break
        num_comments = min(num_comments, int(t))
        i = -1
        while num != 0:
            date, i = rraw_parse(res.text, '"date">', '<', i)
            if i==0: break
            contents, i = rraw_parse(res.text, '"txt">', '="info">', i)
            ip, i = rraw_parse(res.text, '"ip">', '<', i)
            name, i = rraw_parse(res.text, '>[', ']<', i)
            name = name.replace('<span class="nick_comm flow"></span>', "")
            name = name.replace('<span class="nick_comm fixed"></span>', "")
            name = name.replace('<span class="nick_mnr_comm ic_gc_df"></span>', "")
            yield {
                "name": name.strip(), "ip": ip.strip(), "contents": contents[:-66].strip(), "date": date.strip()
                }
            num -= 1
            count += 1
        if count >= num_comments:
            break
        else:
            page += 1

def writeDoc(board, is_miner, name, password, title, contents, sess=None):
    # create session
    if sess is None:
        sess = requests.Session()
    url = "http://m.dcinside.com/write.php?id=%s&mode=write" % board
    res = _get(sess, url, headers=GET_HEADERS)
    # get secret input
    data = extractKeys(res.text, 'g_write.php"')
    if name: data['name'] = name
    if password: data['password'] = password
    data['subject'] = title
    data['memo'] = contents
    # get new block key
    headers = POST_HEADERS.copy()
    headers["Referer"] = url
    url = "http://m.dcinside.com/_option_write.php"
    
    verify_data = {
        "id": data["id"],
        "w_subject": title,
        "w_memo": contents,
        "w_filter": "",
        "mode": "write_verify",
    }
    new_block_key = _post(sess, url, data=verify_data, headers=headers).json()
    if new_block_key["msg"] != "5":
        print("Error wile write doc(block_key)")
        print(result)
        raise Exception(repr(new_block_key))
    data["Block_key"] = new_block_key["data"]
    url = "http://upload.dcinside.com/g_write.php"
    result = _post(sess, url, data=urllib.parse.urlencode(data, True), headers=headers).text
    doc_no, i = raw_parse(result, "no=", '"')
    return doc_no

def removeDoc(board, is_miner, doc_no, password, sess=None):
    # create session
    if sess is None:
        sess = requests.Session()
    headers = POST_HEADERS.copy()
    data = {"no": doc_no, "id": board, "page": "", "mode": "board_del"}
    if password:
        url = "http://m.dcinside.com/_access_token.php"
        headers["Referer"] = "http://m.dcinside.com/password.php?id=%s&no=%s&mode=board_del2&flag=" % (board, doc_no)
        result = _post(sess, url, data={"token_verify": "nonuser_del"}, headers=headers).json()
        if result["msg"] != "5":
            print("Error wile write doc(block_key)")
            print(result)
            raise Exception(repr(result))
        data["mode"] = "board_del2"
        data["write_pw"] = password
        data["con_key"] = result["data"]
    else:
        url = "http://m.dcinside.com/view.php?id=%s&no=%s" % (board, doc_no)
        res = _get(sess, url, headers=GET_HEADERS)
        user_no = raw_parse(res.text, '"user_no" value="', '"')[0]
        headers["Referer"] = url
        data["mode"] = "board_del"
        data["user_no"] = user_no
    url = "http://m.dcinside.com/_option_write.php"
    result = _post(sess, url, data=data, headers=headers).json()
    if (type(result)==int and result != 1) or (type(result)==dict and result["msg"] != "1"):
        print("Error while remove doc: ", result)
        raise Exception(repr(result))
    return sess


def writeComment(board, is_miner, doc_no, name, password, contents, sess=None):
    # create session
    if sess is None:
        sess = requests.Session()
    url = "http://m.dcinside.com/view.php?id=%s&no=%s" % (board, doc_no)
    res = _get(sess, url, headers=GET_HEADERS, timeout=3)
    data = extractKeys(res.text, '"comment_write"')
    if name: data["comment_nick"] = name
    if password: data["comment_pw"] = password
    data["comment_memo"] = contents
    headers = POST_HEADERS.copy()
    headers["Referer"] = url
    url = "http://m.dcinside.com/_access_token.php"
    block_key = _post(sess, url, headers=headers, data={"token_verify": "com_submit"}, timeout=3).json()
    if block_key["msg"] != "5":
        print("Error wile write comment(block key)")
        raise Exception(repr(block_key))
    url = "http://m.dcinside.com/_option_write.php"
    data["con_key"] = block_key["data"]
    result = _post(sess, url, headers=headers, data=data, timeout=3)
    result = result.json()
    if result["msg"] != "1":
        print("Error wile write comment", result)
        raise Exception(repr(result))
    return doc_no
    

def login(userid, password, sess=None):
    if sess is None:
        sess = requests.Session()
    url = "http://m.dcinside.com/login.php?r_url=m.dcinside.com%2Findex.php"
    headers = GET_HEADERS.copy()
    headers["Referer"] = "http://m.dcinside.com/index.php"
    res = _get(sess, url, headers=headers, timeout=3)
    data = extractKeys(res.text, '"login_process')
    headers = POST_HEADERS.copy()
    headers["Referer"] = url
    url = "http://m.dcinside.com/_access_token.php"
    res = _post(sess, url, headers=headers, data={"token_verify": "login", "con_key": data["con_key"]}, timeout=3)
    data["con_key"] = res.json()["data"]
    url = "https://dcid.dcinside.com/join/mobile_login_ok.php"
    headers["Host"] = "dcid.dcinside.com"
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    headers["Accept-Encoding"] = "gzip, deflate, br"
    headers["Cache-Control"] = "max-age=0"
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    del(headers["X-Requested-With"])
    data["user_id"] = userid
    data["user_pw"] = password
    data["id_chk"] = ""
    #data["mode"] = ""
    if "form_ipin" in data: del(data["form_ipin"])
    res = _post(sess, url, headers=headers, data=data, timeout=3)
    print(data)
    while 0 <= res.text.find("rucode"):
        print("login fail!")
        print(res.text)
        print(res.headers)
        time.sleep(5)
        res = _post(sess, url, headers=headers, data=data, timeout=3)
    return sess
    
def logout(sess):
    url = "http://m.dcinside.com/logout.php?r_url=m.dcinside.com%2Findex.php"
    headers = GET_HEADERS.copy()
    headers["Referer"] = "http://m.dcinside.com/index.php"
    res = _get(sess, url, headers=headers, timeout=3)
    return sess
    
def extractKeys(html, start_form_keyword):
    p = ""
    start, end, i = 0, 0, 0
    #result = []#OrderedDict()
    result = {}
    (p, start) = raw_parse(html, start_form_keyword, '', i)
    (p, end) = raw_parse(html, '</form>', '', start)
    i = start
    while True:
        (p, i) = raw_parse(html, '<input type="hidde', '"', i)
        if not p or i >= end: break
        (name, i) = raw_parse(html, 'name="', '"', i)
        if not name or i >= end: break
        (value, i_max) = raw_parse(html, '', '>', i)
        (value, i) = raw_parse(html, 'value="', '"', i)
        if i_max > i:
            result[name] = value
            #result.append((i, name, value))
        else:
            i = i_max
            result[name] = ""
            #result.append((i, name, ""))
    i = start
    while True:
        (p, i) = raw_parse(html, "<input type='hidde", "'", i)
        if not p or i >= end: break
        (name, i) = raw_parse(html, "name='", "'", i)
        if not name or i >= end: break
        (value, i_max) = raw_parse(html, '', '>', i)
        (value, i) = raw_parse(html, "value='", "'", i)
        if i_max > i:
            #result.append((i, name, value))
            result[name] = value
        else:
            i = i_max
            #result.append((i, name, ""))
            result[name] = ""
    while True:
        (p, i) = raw_parse(html, '<input type="hidde', '"', i)
        if not p or i >= end: break
        (name, i) = raw_parse(html, 'NAME="', '"', i)
        if not name or i >= end: break
        (value, i_max) = raw_parse(html, '', '>', i)
        (value, i) = raw_parse(html, 'value="', '"', i)
        if i_max > i:
            result[name] = value
            #result.append((i, name, value))
        else:
            i = i_max
            result[name] = ""
            #result.append((i, name, ""))
    return result
    #return [i[1:] for i in sorted(result, key=lambda x: x[0])]

def rraw_parse(text, start, end, offset=0):
    s = text.rfind(start, 0, offset)
    if s == -1: return None, 0
    s += len(start)
    e = text.find(end, s)
    if e == -1: return None, 0
    return text[s:e], s - len(start)

def raw_parse(text, start, end, offset=0):
    s = text.find(start, offset)
    if s == -1: return None, 0
    s += len(start)
    e = text.find(end, s)
    if e == -1: return None, 0
    return text[s:e], e


if __name__ == '__main__':
    print("login and get session..")
    #sess = login("sech9446", "song4627")
    #doc_no = writeDoc("alphago", True, None, None, "알파고님 동물원 언제만드시냐2", "거기2 들어가면 알파고님이 교배시켜주시겠지? ㅎㅎㅎㅎ", sess=sess)
    #doc_no = writeComment("alphago", True, doc_no, None, None, "거기 들어가면 알파고님이 교배시켜주시겠지? ㅎㅎㅎㅎ", sess=sess)
    #removeDoc("alphago", True, "276", None, sess)
    #logout(sess=sess)
    #removeDoc("alphago", True, "279", "1234")
    board= "programming"
    is_miner = False
    print("writing doc..")
    doc_no = writeDoc(board, is_miner, "주작기", "qwer1234!", "주작기 테스트%d" % random.randint(1, 100000) , "test")
    for i in range(4):
        print("writing comments..")
        try:
            writeComment(board, is_miner, doc_no, "주작기", "1234", "주작기 테스트|%d" % random.randint(1, 100000))
        except Exception as e:
            print(e)
        time.sleep(1)
    print("upvoting..")
    print(upvote(board, is_miner, doc_no, 1000))
    exit(1)
    #res = writeDoc("얄파고", "1234", "alphago", "알파고님 동물원 언제만드시냐", "거기 들어가면 알파고님이 교배시켜주시겠지? ㅎㅎㅎㅎ")
    #[print(i) for i in iterableBoard(board="programming", num=100)]
    #exit(1)
    #res = writeDoc("얄파고", "1234", "programming", "지잡대 1학년 python수업 조교하는데", "<p>애들 진짜 개멍청함 파이썬을 어려워할줄은 상상도 못했는데. 내가볼때 고딩이랑 대딩사이에 1년정도 강제 휴식기간 있어야함 어차피 1학년때 애들 진짜 공부 절대 안함 밤새 술마시고 꼴아가지고 오는애들도 종종 보임</p>")
    #res = writeDoc("test", "1234", "programming", False, "test", "test")
    prininitialt(res)
