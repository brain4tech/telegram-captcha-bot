# This is the main script of the main Telegrambot of the Captcha-Bot, originally created for a Rheinhessen Telegramgroup Initiative
# Published on GitHub for transparency and progress-showing purposes
# Author: (c) Brain4Tech

# --- IMPORT STATEMENTS ---
# packages
import os
from telegram_bot import TelegramBot, BotCommand, BotCommandList, InlineButton, ButtonList, ChatPermissions
from time import sleep
import traceback
from dotenv import load_dotenv

# libaries
import path_setup as setup
from lib.misc import debug_print

# classes
from classes.user_id_list import UserIdList, UserIdTimestampList


# --- CONSTANTS ---
DEBUG = True

# --- FUNCTIONS ---

def newChatMember(chat_id, user_id, user_name, time):
    
    # save time of joining, send welcome message
    usertimestamplist.register(chat_id, user_id, time)
    welcome_message = f"Willkommen im Chat, {user_name}!"
    response = bot.sendMessage(chat_id, welcome_message).json()

    # get message-id of this message and use it as payload for inlinekeyboard
    message_id = response['result']['message_id']
    debug_print (f"New chat member {user_id} in {chat_id} at {time}. Id of welcome-message: {message_id}", DEBUG)
    userwelcomemessagelist.register(chat_id, user_id, message_id)
    welcome_message = f"Willkommen im Chat {user_name}!\nBitte drücke auf den untenstehenden Knopf um der Konversation beitreten zu können:"
    button_dict = ButtonList (InlineButton, [InlineButton("Der Konversation beitreten", url_ = f"{tg_bot_link}?start={chat_id}_{message_id}")]).toBotDict()
    bot.editMessage(chat_id, message_id, welcome_message, button_dict)

    response_restrict = bot.restrictChatMember(update.message.chat.id, user_id, no_chat_permissions).json()
    debug_print(f"\tRestricted new member <{user_id}>: [{response_restrict['description' if 'description' in response_restrict else 'result']}]", DEBUG)

    return response

def createNeededFileStructure():
    pass

# --- START OF SCRIPT ---
setup.enable()
createNeededFileStructure()

load_dotenv("credentials")
group_invite_link = os.environ.get("GROUP_INVITE_LINK")
tg_bot_link = os.environ.get("TG_BOT_LINK")

with open('data/help_text.txt') as file:
    help_text = file.read().strip()

bot = TelegramBot(os.environ.get("BOT_TOKEN"), return_on_update_only=False)
    
bot.deleteBotCommands()
bot.setBotCommands(BotCommandList([BotCommand("sim", "Simulation einer Aktion [event] [parameter]"), BotCommand("help", "Erzeugt Hilfetext und weitere Infos")]))

default_chat_permissions = ChatPermissions(True, True, False, True, True, False, False, False)
no_chat_permissions = ChatPermissions()

# create lists
usertimestamplist = UserIdTimestampList("user_id_timestamp.json", time_interval_=30)
userwelcomemessagelist = UserIdList("user_welcome_message.json")
triggersimlist = UserIdList("sim_trigger_message.json")

print ("--- Started Captchabot ---")

while True:

    for user in usertimestamplist.getExpiredUsers():
        chat_id, user_id = user[0], user[1]
        # kick user from chat
        response_ban, response_unban = bot.kickChatMember(chat_id, user_id)
        debug_print (f"kicked user {user_id} in {chat_id}: [{response_ban.json()[list(response_ban.json())[-1]]}, {response_unban.json()[list(response_unban.json())[-1]]}]", DEBUG)

        # delete sim-command
        simlist = triggersimlist.getList(chat_id)
        if simlist:
            if user_id in simlist:
                bot.deleteMessage(chat_id, simlist[user_id])
                triggersimlist.unregister(chat_id, user_id)

        # delete welcome_message
        bot.deleteMessage(chat_id, userwelcomemessagelist.getList()[chat_id][user_id])
        userwelcomemessagelist.unregister(chat_id, user_id)

        # only unregister if everything was successfull
        usertimestamplist.unregister(chat_id, user_id)

    update, response = bot.poll()
    # debug_print(response, DEBUG)
    if not update:
        sleep(1)
        continue

    command_entity = update.isBotCommand()

    if command_entity:
        command = update.message.text[command_entity.offset:command_entity.length]
        command_params = update.message.text[command_entity.offset + command_entity.length:].strip()
        
        # a user has started conversation with bot
        # if conversation initianted from a group, then payload of command matches group-id
        if "/start" in command:
            payload = command_params.replace(" ", "")
            payload_data = payload.split("_")   # 0: chat_id, 1: message_id

            try:
                
                if payload:
                    # debug_print (f"payload exists: {payload_data}", DEBUG)
                    # usage of paylod
                    if len(payload_data) == 2:
                        # payload has correct structure

                        sender_id = str(update.message.sender.id)

                        pl_chat = payload_data[0]
                        pl_message = payload_data[1]
                        timestamps = usertimestamplist.getList()
                        
                        # debug_print (f"payload has correct structure: {pl_chat} {pl_message}", DEBUG)

                        if pl_chat in timestamps:
                            # payload-groupchat is correct
                            # debug_print ("correct group", DEBUG)

                            if sender_id in timestamps[pl_chat]:
                                # sender is listed as new member in group
                                # debug_print ("sender is listed as new member", DEBUG)

                                welcome_message = userwelcomemessagelist.getList()
                                welcome_message_id = str(welcome_message[pl_chat][sender_id])

                                if pl_message == welcome_message_id:
                                    # sender has used his own welcome-message and can be authorized
                                    # debug_print ("correct welcome_message, verify user", DEBUG)
                                    # welcome user
                                    bot.sendMessage(sender_id, "Willkommen in der Gang!\nHier geht's bald weiter mit einer Captcha. UUUUH, Spannend!")
                                    welcome_string = f"Willkommen in der Gruppe, {update.message.sender.first_name}!"
                        
                                    # delete sim-command
                                    simlist = triggersimlist.getList(pl_chat)
                                    if simlist:
                                        if sender_id in simlist:
                                            bot.deleteMessage(pl_chat, simlist[sender_id])
                                            triggersimlist.unregister(pl_chat, sender_id)
                                    
                                    bot.editMessage(pl_chat, welcome_message_id, welcome_string, {})

                                    #unregister user from lists
                                    usertimestamplist.unregister(pl_chat, sender_id)
                                    userwelcomemessagelist.unregister (pl_chat, sender_id)
                                    
                                    response_unrestrict = bot.restrictChatMember(pl_chat, sender_id, default_chat_permissions).json()
                                    debug_print(f"\tGave default permission to <{sender_id}>: [{response_unrestrict['description' if 'description' in response_unrestrict else 'result']}]", DEBUG)

                                else:
                                    # debug_print (f"payload_message_id and listed id do not match -> wrong button: {pl_message} {welcome_message_id}", DEBUG)
                                    # sender has used wrong button
                                    bot.sendMessage(update.message.chat.id, "Bitte nutze den Knopf unter deiner eigenen Willkommensnachricht.")
                            else:
                                # check if sender already in group
                                chat_member = bot.getChatMember(pl_chat, sender_id)
                                if chat_member:
                                    # debug_print ("User already in group", DEBUG)
                                    bot.sendMessage(update.message.chat.id, "Du bist schon in der Gruppe drin. Du brauchst dich nicht mehr zu verifizieren!")
                                else:
                                    # unauthorized
                                    pass
                        else:
                            # unauthorized
                            pass
                    else:
                        #unauthorized 
                        pass
                else:
                    # unauthorized
                    pass

            except Exception as e:
                print (traceback.format_exc())

        # --- SIMULATION OF GROUP-JOINING ---
        if "/sim" in command:
            # simulate different states of script

            if "join" in command_params:
                # simulate first join in group

                user_id = command_params.replace("join", "").replace(" ", "")

                final_user_id = user_id if user_id else update.message.sender.id

                triggersimlist.register(update.message.chat.id, final_user_id, update.message.id)

                chat_member = bot.getChatMember(update.message.chat.id, final_user_id)
                newChatMember(update.message.chat.id, final_user_id, chat_member.user.first_name if chat_member else "Unbekannter", update.message.date)
            
            """
            # simulation registration is not neccessary as it is integrated in "/sim join"
            if command_params == "reg":
                # simlate registering of user
                usertimestamplist.register(update.message.chat.id, update.message.sender.id, update.message.date)
            
            if command_params == "unreg":
                # simlate unregistering of user
                usertimestamplist.unregister(update.message.chat.id, update.message.sender.id)
            """

        if "/help" in command:
            # show help text and more
            # temporary there is nothing to show

            help_start = f"Hi {update.message.sender.first_name}!"
            back_button = ButtonList (InlineButton, [InlineButton("➔ Zurück zur Gruppe", url_ = group_invite_link)]).toBotDict()

            # delete message in group chat
            bot.deleteMessage(update.message.chat.id, update.message.id)

            # send help-statement in private chat
            bot.sendMessage(update.message.sender.id, f"{help_start}\n{help_text.strip()}", back_button)
        
        # added for testing purposes
        if "/quit" in command:
            # quit application
            break
            

        continue


    # --- REAL LIFE ACTION ---

    """
    # left out to prevent spamming in console output
    if update.isMessage():
        debug_print (f"{update.message.text} from {update.message.sender.id} in {update.message.chat.id}")
        pass
    """

    if update.isnewChatMember():
        for new_member in update.message.new_chat_members:
            newChatMember (update.message.chat.id, new_member.id, new_member.first_name, update.message.date)
    
    # temporarily store user with connected message-id and check with:
    if update.isCallback():
        callback_id = update.callback.id
        callback_message_id = update.callback.message.id
        callback_chat_id = update.callback.message.chat.id
        callback_user_id = update.callback.sender.id

        print (usertimestamplist.getList(), callback_user_id, callback_message_id, callback_chat_id)

        if callback_user_id in usertimestamplist.getList()[callback_chat_id]:
            if userwelcomemessagelist.getList()[callback_chat_id][callback_user_id] != callback_message_id:
                bot.sendMessage(callback_chat_id, f"Bitte drücke auf den Knopf unter deiner eigenen Willkommensnachricht, {update.callback.sender.first_name}")
                bot.answerCallbackQuery(callback_id, "Bitte drücke auf den Knopf unter deiner eigenen Willkommensnachricht")
        else:
            bot.answerCallbackQuery(callback_id, "Du brauchst diesen Knopf nicht zu drücken da du schon in der Gruppe bist!")

    # check frequently to not overuse capacities
    sleep(1)

setup.disable()
