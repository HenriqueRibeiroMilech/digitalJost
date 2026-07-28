import random
import win32security
import win32api
from flask import Blueprint, render_template, request, redirect, send_file
from flask_login import login_required

from app.utils.constants import APP_PATH
from app.utils.db_utils import get_engine

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
@login_required
def landing_page_get():
    videos = [['des.mp4', 0], ['code.mp4', 0], ['net0.mp4', 0], ['net1.mp4', 0], ['net2.mov', 0], ['video.mp4', 0]]
    video_info = videos[random.randint(1, len(videos)) - 1]
    video = video_info[0]
    res = video_info[1]
    return render_template('home_content.html', video=video, res=res)

@main.route('/research', methods=['GET'])
def user_research_get():
    return render_template('jdt.userResearch/research_form_24_08_01.html')
    
@main.route('/research', methods=['POST'])
def user_research_post():

    if 'X-Iis-Windowsauthtoken' in request.headers.keys():
        handle_str = request.headers['X-Iis-Windowsauthtoken']
        handle = int(handle_str, 16)
        win32security.ImpersonateLoggedOnUser(handle)
        username = win32api.GetUserName()
        win32security.RevertToSelf()
        win32api.CloseHandle(handle)
    else:
        username = '00046094'

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""INSERT INTO JDT_USER_RESEARCH VALUES (
                    '{username}',
                    '2024-03-01',
                    '{request.form['1']}',
                    '{request.form['2']}',
                    '{request.form['3']}',
                    '{request.form['4']}',
                    '{request.form['5']}',
                    '{request.form['6']}',
                    '{request.form['7']}',
                    GETDATE())"""
        cnnx.execute(query)

        query = f"""UPDATE JDT_USER_DETAILS SET 
                        temp = 1 
                    WHERE id = '{username}'"""
        cnnx.execute(query)
        
        cnnx.commit()

    return redirect ('/login')

@main.route('/tutorial/download', methods=['GET'])
def tutorial_download_get():
    caminho = rf'{APP_PATH}\app\static\uploads\tutorial'
    return send_file(rf'{caminho}\{request.args['file']}.pptx', as_attachment=True)
