import requests
import re
import os
import pymysql
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

api = os.environ["EMBY_API_TOKEN"].strip()
url_external = os.environ["EMBY_URL_EXTERNAL"]
url_internal = os.environ.get("EMBY_URL_INTERNAL", url_external)
if url_internal.endswith("\\"):
    url_internal = url_internal[:-1]
bot_api = os.environ["TG_BOT_API_TOKEN"].strip()
group_chat_id = os.environ["TG_GROUP_CHAT_ID"].strip()

host=os.environ["DB_HOST"]
user=os.environ["DB_USER"]
password=os.environ["DB_PASS"]
name=os.environ["DB_NAME"]

cursor = pymysql.connect(host=host, user=user, password=password, charset='utf8').cursor()
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {name}")
cursor.close()

connect = pymysql.connect(host=host, user=user, password=password, db=name, charset='utf8')
db = connect.cursor()
db.execute("CREATE TABLE if not exists user (chatid VARCHAR(255), emby_userid VARCHAR(255))")

def start(update: Update, context: CallbackContext):
    update.message.reply_text('请输入：/create + 用户名 来注册\n\n'
                              '例如通过发送"/create helloworld"来注册一个用户名为helloworld的账号')

def help_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    update.message.reply_text(f'chatid: {chat_id}\n\n'
                                '创建账号：/create + 用户名\n'
                                'e.g：/create helloworld\n\n'
                                '重置密码：/reset\n需要先绑定账号\n\n'
                                '绑定账号：/bind + 用户名 + 密码\n'
                                'e.g：/bind helloworld 123456\n\n'
                                '查询账号信息：/info')

def info(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    db.connection.ping()
    check = judge(chat_id)
    if(check == 1):
        check1 = judgebind(chat_id)
        if(check1 == 1):
                update.message.reply_text('你还未绑定Emby账号，请先绑定！')
        elif(check1 == 2):
            try:
                create_sqli = "SELECT * FROM user WHERE chatid = "+ str(chat_id)
                db.execute(create_sqli)
                result = db.fetchall()
            except Exception as e:
                update.message.reply_text("失败:", e)
            else:
                userid=result[0][1]
            headers = {
            'accept': 'application/json',
            }

            params = {
                'api_key': api,
            }
            response = requests.get(url_internal + '/emby/Users/' + userid, params=params, headers=headers)
            try:
                responsejson = response.json()
            except:
                update.message.reply_text(f"出现问题: {str(response)}, 请联系管理员")
        
            name = responsejson['Name']
            createdate = responsejson['DateCreated']
            lastlogin = responsejson.get('LastLoginDate', '从未')
            update.message.reply_text('Emby用户名：' + name + '\n\n注册时间：' + createdate + '\n\n上一次登录时间：' + lastlogin)
        else:
            update.message.reply_text('未知错误，请联系管理员！')
    elif(check == 0):
        update.message.reply_text('您还未创建账号！')
    

def create(update: Update, context: CallbackContext) -> None:
    db.connection.ping()
    text = update.message.text
    names = text.split(' ')
    name = names[1]
    chat_id = update.message.chat_id
    judge_back = judge(chat_id)
    check_groups = check_user_in_the_group(update,context)
    if(check_groups == 1):
        if(judge_back == 1):
            update.message.reply_text('你的账号已经注册过Emby了！')
        elif(judge_back == 0):
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
            }

            params = (
                        ('api_key', api),
                    )

            data = '{"Name":"'+name+'","HasPassword":true}'

            response = requests.post(url_internal + '/emby/Users/New', headers=headers, params=params, data=data)

            status1 = response.status_code
            if(response != '' and status1 == 200):

                id1=re.findall(r'\"(.*?)\"',response.text)
                id=id1[9]

                headers1 = {
                                'accept': '*/*',
                                'Content-Type': 'application/json',
                            }

                params1 = (
                            ('api_key', api),
                        )

                data1 = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":false,"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":false,"EnableSubtitleDownloading":false,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'

                requests.post(url_internal + '/emby/Users/'+id+'/Policy', headers=headers1, params=params1, data=data1)

                try: 
                    sql = "insert into user (chatid,emby_userid) values ("+str(chat_id)+","+'"'+str(id)+'"'+")"
                    db.execute(sql)
                    connect.commit()
                except Exception as e:
                    update.message.reply_text("失败:", e)
                else:
                    update.message.reply_text(f'注册用户名：{name} \n无初始密码，请尽快登录，点击右上角设置图标设置密码！\n公益服直连网址：{url_external} \n更多线路进群获取！\n\n更新通知频道： {group_chat_id}\n聊天吹水群： {group_chat_id}\n\n推荐使用客户端播放，下载地址：http://t.me/EmbyNoisyX')
            elif(status1 == 400):
                update.message.reply_text(response.text)
            else:
                update.message.reply_text('未知错误，请联系TG频道管理员！')
    elif(check_groups == 0):
        update.message.reply_text(f'请先加入聊天群组和通知频道！\n\n更新通知频道： {group_chat_id} \n聊天吹水群：{group_chat_id}')


def reset(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    db.connection.ping()
    check = judge(chat_id)
    if(check == 0):
        update.message.reply_text('你还未注册过Emby公益服，请先注册！')
    elif(check == 1):
        check2 = judgebind(chat_id)
        if(check2 == 1):
            update.message.reply_text('你的TG账号还未绑定Emby公益服账号，请先绑定！')
        elif(check2 == 2):
            check3 = passwd(chat_id)
            if(check3 == 1):
                update.message.reply_text('密码移除成功，现密码为空！')
            else:
                update.message.reply_text('未知错误，请联系管理人员解决！')


def bind(update: Update, context: CallbackContext) -> None:
    db.connection.ping()
    text = update.message.text
    chatid = update.message.chat_id
    check = judgebind(chatid)
    if(check == 1):
        names = text.split(' ')
        name = names[1]
        password = names[2]
        userid = nametoid(name)
        check2 = verify(name,password)
        if(check2 == 1):
            try:
                sql = "UPDATE user SET emby_userid="+'"'+str(userid)+'"'+" WHERE chatid ="+str(chatid)
                db.execute(sql)
                connect.commit()
            except Exception as e:
                update.message.reply_text('验证成功！绑定失败！请联系管理员处理！')
            else:
                update.message.reply_text('验证成功！绑定成功！')
        elif(check2 == 0):
            update.message.reply_text('验证失败，请检查账号密码！')
    elif(check == 2):
        update.message.reply_text('你已经绑定过Emby账号了！')


def nametoid(name):
    headers = {
    'accept': 'application/json',
    }

    params = {
        'IsHidden': 'true',
        'IsDisabled': 'false',
        'Limit': '1',
        'NameStartsWithOrGreater': name,
        'api_key': api,
    }

    response = requests.get(url_internal + '/emby/Users/Query', params=params, headers=headers)
    responsejson = response.json()
    id = responsejson['Items'][0]['Id']
    return id

def idtoname(chatid):
    db.connection.ping()
    try:
        create_sqli = "SELECT * FROM user WHERE chatid = "+ str(chatid)
        db.execute(create_sqli)
        result = db.fetchall()
    except Exception as e:
        print("失败:", e)
    else:
        userid=result[0][1]
    headers = {
    'accept': 'application/json',
    }

    params = {
        'api_key': api,
    }
    response = requests.get(url_internal + '/emby/Users/' + userid, params=params, headers=headers)
    responsejson = response.json()
    name = responsejson['Name']
    return name


def judge(chat_id):
    kk = 0
    try:
        create_sqli = "SELECT chatid FROM user "
        db.execute(create_sqli)
        result = db.fetchall()
    except Exception as e:
        print("失败:", e)
    else:
        length = len(result)
        for i in range(0,length):
            if(str(chat_id) == result[i][0]):
                kk=1
    return kk

def judgebind(chat_id):
    db.connection.ping()
    kk = 1
    try:
        create_sqli = "SELECT * FROM user WHERE chatid ="+str(chat_id)
        db.execute(create_sqli)
        result = db.fetchall()
    except Exception as e:
        print("失败:", e)
    else:
        if(result[0][1]):
            kk=2
    return kk

#检测是否在群组中
def check_user_in_the_group(update: Update, context: CallbackContext):
    user_id = update.message.chat_id 
    check = context.bot.getChatMember(group_chat_id,user_id) 
    if check.status in ['administrator', 'creator', 'member']: 
        return 1
    else:
        return 0

#检测账号密码是否正确，此子函数若想正常使用，需要自己抓包params中的内容。
#此子函数只会被bind绑定功能调用，若你一开始就使用本脚本，则无需开启bind功能，也无需抓包使本函数可用。
def verify(username,password):
    headers = {
        'accept': 'application/json',

    }

    json_data = {
        'Username': username,
        'Pw': password,
    }

    params = {
        
    }

    response = requests.post(url_internal + '/emby/Users/AuthenticateByName', headers=headers, json=json_data,params=params)

    if(response.status_code == 200):
        return 1
    else:
        return 0

def passwd(chatid):
    check = 0
    db.connection.ping()    
    try:
        create_sqli = "SELECT * FROM user WHERE chatid = "+ str(chatid)
        db.execute(create_sqli)
        result = db.fetchall()
    except Exception as e:
        print("失败:", e)
    else:
        userid=result[0][1]
    headers = {
        'accept': '*/*',
    }

    params = {
        'api_key': api,
    }

    json_data = {
        'ResetPassword': True,
    }

    response = requests.post(url_internal + '/emby/Users/'+userid+'/Password', params=params, headers=headers, json=json_data)
    status2 = response.status_code
    if(status2 == 204):
        check = 1
    return check



def main() -> None:
    updater = Updater(bot_api)
    
    dispatcher = updater.dispatcher

    # 机器人命令
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("create", create))
    dispatcher.add_handler(CommandHandler("reset", reset))
    dispatcher.add_handler(CommandHandler("bind", bind))
    dispatcher.add_handler(CommandHandler("info", info))

    # 启动机器人，勿删
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()