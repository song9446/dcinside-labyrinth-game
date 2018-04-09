#!/usr/bin/python3
import dc_api
import os
import re
import time
import datetime
import korean
import atexit


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + str(key) + '}'

SCENE_TEMPLATE_PATH = "scenes/template_bgcolor_fontcolor_floor_description_problem_hint.html"
SCENES_PATH = "scenes"
SCENES_COMPONENT_PATH_FORMAT = SCENES_PATH + "/{floor}/{component}.html"
COMPONENTS = ["description", "problem", "hint", "answer"]
#NAME="미궁"
#PASSWORD="1234"
TITLE_FORMAT_ATTRACT="지하{floor}층에 갇혔다ㅠㅠ 나좀 도와줘"
TITLE_FORMAT_GENERAL = "지하 {floor}층에 갇혔다ㅠㅠ ({name}이(가) 문열어줌ㅎㅎ)"
FLOOR_ALIVE_TIME = datetime.timedelta(hours=1)
ANSWER_COMMENT="{name} 암호를 입력하자 문이 열렸다. 방에 갇혀있던 사람들은 일말의 불안감을 느끼며 천천히 계단을 내려가기 시작했다..."

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
def compareAnswer(answer1, answer2):
    return answer1.upper().replace(' ', '').startswith(answer2.upper().replace(' ', '')) or answer2.upper().replace(' ', '').startswith(answer1.upper().replace(' ', ''))

def createScene(floor):
    scene_text_template = ""
    components = {}
    with open(SCENE_TEMPLATE_PATH, "rt") as scene_file:
        scene_text_template = re.sub(r'\n\s*', '', scene_file.read())
    for comp in COMPONENTS:
        with open(SCENES_COMPONENT_PATH_FORMAT.format(floor=floor, component=comp), "rt") as scene_file:
            components[comp] = re.sub(r'\n\s*', '', scene_file.read())
    bgcolor = max(0xddddff66 - (floor-1)*0x11111100, 0x00000066)
    fontcolor = 0xf3f3f3ff#contrastFontColor(bgcolor)
    scene = scene_text_template.format(
        bgcolor="#%08x" % bgcolor,
        fontcolor="#%08x" % fontcolor,
        floor=floor,
        description=components["description"],
        problem=components["problem"],
        hint=components["hint"])
    return scene, components["answer"].upper().replace(' ', '')

def run(board, is_miner, userid, secret):
    sess = dc_api.login(userid, secret)
    max_floor = sum(1 for i in os.listdir(SCENES_PATH) if os.path.isdir(os.path.join(SCENES_PATH, i)))
    answerer = ""
    doc_no = ""
    atexit.register(lambda: dc_api.removeDoc(board, is_miner, doc_no, password=None, sess=sess))
    for floor in range(1, max_floor+1):
        try:
            scene, answer = createScene(floor)
            title_format = TITLE_FORMAT_GENERAL
            if floor==1:
                recent_fun_article = max(dc_api.iterableBoard(board=board, is_miner=is_miner, num=50, sess=sess), key=lambda doc: doc["views"] + doc["votes"]*10)
                scene = scene.format_map(SafeDict(recent_fun_article=("%s [%d]" % (recent_fun_article["title"], recent_fun_article["comments"])), name=answerer))
                title_format = TITLE_FORMAT_ATTRACT
            else:
                scene = scene.format_map(SafeDict(name=answerer))
            scene = korean.l10n.proofread(scene)
            doc_no = dc_api.writeDoc(board=board, is_miner=is_miner, name=None, password=None, title=korean.l10n.proofread(title_format.format_map(SafeDict(floor=floor, name=answerer))), contents=scene, sess=sess)
            solved = False
            answerer = ""
            while not solved:
                for comment in dc_api.iterableComments(board=board, is_miner=is_miner, doc_no=doc_no, num=20, sess=sess):
                    if compareAnswer(answer, comment["contents"]):
                        #dc_api.writeComment(board=board, is_miner=is_miner, doc_no=doc_no, name=None, password=None, contents=ANSWER_COMMENT.format(name=Noun(comment["name"])), sess=sess)
                        answerer = comment["name"]
                        print(answerer)
                        solved = True
                        floor += 1
                        dc_api.removeDoc(board=board, is_miner=is_miner, doc_no=doc_no, password=None, sess=sess)
                        print("floor: %d" % floor)
                #for doc in dc_api.iterableBoard(board=board, is_miner=is_miner, num=20, sess=sess):
                #    if compareAnswer(answer, doc["title"]):
                #        dc_api.writeComment(board=board, is_miner=is_miner, doc_no=doc["doc_no"], name=None, password=None, contents=ANSWER_COMMENT.format(name=Noun(doc["name"])), sess=sess)
                #        solved = True
                time.sleep(1)
        except KeyboardInterrupt:
            try: dc_api.removeDoc(board=board, is_miner=is_miner, doc_no=doc_no, password=None, sess=sess)
            except: pass
            exit(1)
        except:
            floor -= 1
            dc_api.removeDoc(board=board, is_miner=is_miner, doc_no=doc_no, password=None, sess=sess)
            continue
        

if __name__ == '__main__':
    run("alphago", True, "sech9446", "song4627")
