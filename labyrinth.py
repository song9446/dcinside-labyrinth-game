#!/usr/bin/python3
import sys
sys.path.append("dcinside-python3-api")
import dc_api
import os
import re
import time
import datetime
import korean
import atexit
import traceback


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + str(key) + '}'

COLLAPSED_THRESHOLD = 2*60*60
COLLAPSED_THRESHOLD = 30
BREAK_TIME = 5*60

SCENE_TEMPLATE_PATH = "scenes/template_bgcolor_fontcolor_floor_description_problem_hint.html"
SCENES_PATH = "scenes"
SCENES_COMPONENT_PATH_FORMAT = SCENES_PATH + "/{floor}/{component}.html"
COMPONENTS = ["description", "problem", "hint", "answer"]
BOARD="alphago"
ID="bot123"
SECRET="1q2w3e4r!"
NAME=None
PASSWORD=None
TITLE_FORMAT_ATTRACT="[미궁] 지하{floor}층에 갇혔다.."
TITLE_FORMAT_GENERAL = "[미궁] 지하{floor}층에 갇혔다..({name}이(가) 문을 열었음)"
TITLE_FORMAT_COLLAPSED = "[미궁] 시간이 지나 모두들 죽고 말았습니다.."
FLOOR_ALIVE_TIME = datetime.timedelta(hours=1)
ANSWER_COMMENT="{name}이(가) 암호를 입력하자 문이 열렸다. 방에 갇혀있던 사람들은 일말의 불안감을 느끼며 천천히 계단을 내려가기 시작했다..."

def contrastFontColor(bgcolor):
    r = bgcolor // 0x010000
    g = (bgcolor-r*0x010000) // 0x000100
    b = bgcolor-r*0x010000-g*0x000100
    yiq = (r*299 + g*587 + b*114)/1000
    return 0x000000 if yiq >= 128 else 0xffffff

def hex2rgba(color):
    r = color // 0x01000000
    g = (color-r*0x01000000) // 0x00010000
    b = (color-r*0x01000000-g*0x00010000) // 0x00000100
    a = color-r*0x01000000-g*0x00010000-b*0x00000100
    return "rgba(%d, %d, %d, %f)" % (r, g ,b, a/256.)

def compareAnswer(answers, candidate):
    for answer in answers:
        if answer in candidate.upper().replace(' ', ''):
            return True
    return False

def createScene(floor):
    scene_text_template = ""
    components = {}
    with open(SCENE_TEMPLATE_PATH, "rt") as scene_file:
        scene_text_template = re.sub(r'\n\s*', '', scene_file.read())
    for comp in COMPONENTS:
        with open(SCENES_COMPONENT_PATH_FORMAT.format(floor=floor, component=comp), "rt") as scene_file:
            components[comp] = scene_file.read().strip() if comp is "answer" else re.sub(r'\n\s*', '', scene_file.read())
    bgcolor = max(0xddddff66 - (floor-1)*0x11111100, 0x00000066)
    fontcolor = 0xf3f3f3ff#contrastFontColor(bgcolor)
    scene = scene_text_template.format(
        bgcolor="#%08x" % bgcolor,
        fontcolor="#%08x" % fontcolor,
        floor=floor,
        description=components["description"],
        problem=components["problem"],
        hint=components["hint"])
    return scene, components["answer"].upper().replace(' ', '').split("\n")

def run(board, userid=None, secret=None):
    if userid: 
        sess = dc_api.login(userid, secret)
    else:
        sess = dc_api.gen_session()
    max_floor = sum(1 for i in os.listdir(SCENES_PATH) if os.path.isdir(os.path.join(SCENES_PATH, i)) and i.isdigit() and int(i)>0)
    print(max_floor)
    commenters = []
    answerers = []
    last_answerer = ""
    doc_id = ""
    start_time = time.time()
    for floor in range(1, max_floor+1):
        try:
            scene, answers = createScene(floor)
            title_format = TITLE_FORMAT_GENERAL
            if floor==1:
                recent_fun_article = max(dc_api.board(board_id=board, num=50, sess=sess), key=lambda doc: doc["view_num"] + doc["voteup_num"]*10)
                scene = scene.format_map(SafeDict(recent_fun_article=("%s [%d]" % (recent_fun_article["title"], recent_fun_article["comment_num"])), name=last_answerer))
                title_format = TITLE_FORMAT_ATTRACT
            elif floor<0:
                for i in range(10):
                    commenter.append("누군가")
                answerers += ["베리나", "국주", "김제동", "박근혜"]
                scene = scene.format_map(SafeDict([("commenter%d"%i, com) for i, com in enumerate(commenters)] + [("answerer%d"%i, ans) for i, ans in enumerate(answerer)]))
                title_format = TITLE_FORMAT_COLLAPSED
            else:
                scene = scene.format_map(SafeDict(name=last_answerer))
            scene = korean.l10n.proofread(scene)
            if floor==1:
                doc_id = dc_api.write_document(board_id=board, name=NAME, pw=PASSWORD, title=korean.l10n.proofread(title_format.format_map(SafeDict(floor=floor, name=last_answerer))), contents=scene, sess=sess)
                time.sleep(2)
                dc_api.write_comment(board_id=board, doc_id=doc_id, name=NAME, pw=PASSWORD, contents="-- 현제 층: 지하 1층 --", sess=sess)
            elif floor<0:
                doc_id = dc_api.write_document(board_id=board, name=NAME, pw=PASSWORD, title=korean.l10n.proofread(title_format.format_map(SafeDict(floor=floor, name=last_answerer))), contents=scene, sess=sess)
                time.sleep(BREAK_TIME)
                return
            else:
                doc_id = dc_api.write_document(board_id=board, name=NAME, pw=PASSWORD, title=korean.l10n.proofread(title_format.format_map(SafeDict(floor=floor, name=last_answerer))), contents=scene, sess=sess)
                #time.sleep(2)
                #dc_api.write_comment(board_id=board, doc_id=doc_id, name=NAME, pw=PASSWORD, contents=korean.l10n.proofread(ANSWER_COMMENT.format(name=last_answerer)), sess=sess)
                time.sleep(2)
                dc_api.write_comment(board_id=board, doc_id=doc_id, name=NAME, pw=PASSWORD, contents="-- 현제 층: 지하 %d층 -- / 문을 연사람: %s / 갇힌 사람: %s" % (floor, ", ".join(answerers), ", ".join(commenters)), sess=sess)
            solved = False
            last_answerer = ""
            while not solved:
                if time.time() - start_time > COLLAPSED_THRESHOLD:
                    dc_api.remove_document(board_id=board, doc_id=doc_id, pw=PASSWORD)
                    floor = -1
                    break
                for comment in dc_api.comments(board_id=board, doc_id=doc_id, num=20, sess=sess):
                    if comment["author"] not in commenters: commenters.append(comment["author"])
                    if compareAnswer(answers, comment["contents"]):
                        dc_api.remove_document(board_id=board, doc_id=doc_id, pw=PASSWORD)
                        last_answerer = comment["author"]
                        print(last_answerer)
                        if last_answerer not in answerers: answerers.append(last_answerer)
                        solved = True
                        floor += 1
                        print("floor: %d" % floor)
                        break
                time.sleep(5)
        except KeyboardInterrupt:
            try: dc_api.remove_document(board_id=board, doc_id=doc_id, pw=PASSWORD, sess=sess)
            except: pass
            exit(1)
        except Exception as e:
            print(e)
            traceback.print_exc()
            '''
            print("repeat until success")
            time.sleep(5)
            floor -= 1
            continue
            '''
            exit(1)
        

if __name__ == '__main__':
    while True:
        run(BOARD, ID, SECRET)
