#!/usr/bin/python3
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

SCENE_TEMPLATE_PATH = "scenes/template_bgcolor_fontcolor_floor_description_problem_hint.html"
SCENES_PATH = "scenes"
SCENES_COMPONENT_PATH_FORMAT = SCENES_PATH + "/{floor}/{component}.html"
COMPONENTS = ["description", "problem", "hint", "answer"]
BOARD="game_dev"
IS_MINER=True
ID="sech9446"
SECRET="song4627"
NAME=None
PASSWORD=None
TITLE_FORMAT_ATTRACT="지하{floor}층에 갇혔다.."
TITLE_FORMAT_GENERAL = "지하{floor}층에 갇혔다..(문연사람: {name})"
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

def run(board, is_miner, userid, secret):
    sess = dc_api.login(userid, secret)
    max_floor = sum(1 for i in os.listdir(SCENES_PATH) if os.path.isdir(os.path.join(SCENES_PATH, i)))
    answerers = []
    last_answerer = ""
    doc_no = ""
    last_answers = []
    for floor in range(1, max_floor+1):
        try:
            scene, answers = createScene(floor)
            title_format = TITLE_FORMAT_GENERAL
            if floor==1:
                recent_fun_article = max(dc_api.iterableBoard(board=board, is_miner=is_miner, num=50, sess=sess), key=lambda doc: doc["views"] + doc["votes"]*10)
                scene = scene.format_map(SafeDict(recent_fun_article=("%s [%d]" % (recent_fun_article["title"], recent_fun_article["comments"])), name=last_answerer))
                title_format = TITLE_FORMAT_ATTRACT
            else:
                scene = scene.format_map(SafeDict(name=last_answerer))
            scene = korean.l10n.proofread(scene)
            if floor==1:
                doc_no = dc_api.writeDoc(board=board, is_miner=is_miner, name=NAME, password=NAME, title=korean.l10n.proofread(title_format.format_map(SafeDict(floor=floor, name=last_answerer))), contents=scene, sess=sess)
                dc_api.writeComment(board=board, is_miner=is_miner, doc_no=doc_no, name=NAME, password=PASSWORD, contents="-- 현제 층: 지하 1층 --", sess=sess)
            else:
                doc_no = dc_api.modifyDoc(board=board, is_miner=is_miner, doc_no=doc_no, name=NAME, password=PASSWORD, title=korean.l10n.proofread(title_format.format_map(SafeDict(floor=floor, name=last_answerer))), contents=scene, sess=sess)
            solved = False
            last_answerer = ""
            while not solved:
                for comment in dc_api.iterableComments(board=board, is_miner=is_miner, doc_no=doc_no, num=20, sess=sess):
                    if compareAnswer(last_answers, comment["contents"]):
                        dc_api.removeComment(board=board, is_miner=is_miner, doc_no=doc_no, comment_no=comment["comment_no"], password=PASSWORD, sess=sess)
                        continue
                    if compareAnswer(answers, comment["contents"]):
                        last_answerer = comment["name"]
                        print(last_answerer)
                        if last_answerer not in answerers: answerers.append(last_answerer)
                        solved = True
                        floor += 1
                        last_answers += answers
                        for com in dc_api.iterableComments(board=board, is_miner=is_miner, doc_no=doc_no, num=20, sess=sess):
                            dc_api.removeComment(board=board, is_miner=is_miner, doc_no=doc_no, comment_no=com["comment_no"], password=PASSWORD, sess=sess)
                        dc_api.writeComment(board=board, is_miner=is_miner, doc_no=doc_no, name=NAME, password=PASSWORD, contents=korean.l10n.proofread(ANSWER_COMMENT.format(name=comment["name"])), sess=sess)
                        dc_api.writeComment(board=board, is_miner=is_miner, doc_no=doc_no, name=NAME, password=PASSWORD, contents="-- 현제 층: 지하 %d층 -- / 갇힌 사람: %s" % (floor, ", ".join(answerers)), sess=sess)
                        print("floor: %d" % floor)
                        break
                time.sleep(0.5)
        except KeyboardInterrupt:
            exit(1)
            try: dc_api.removeDoc(board=board, is_miner=is_miner, doc_no=doc_no, password=PASSWORD, sess=sess)
            except: pass
            exit(1)
        except Exception as e:
            print(e)
            traceback.print_exc()
            print("repeat until success")
            floor -= 1
            continue
        

if __name__ == '__main__':
    run(BOARD, IS_MINER, ID, SECRET)
