# This is the main script of the main Telegrambot of the Rheinhessen Telegramgroup Initiative
# Published on GitHub for transparency and showing progress
# Author: (c) Brain4Tech

# --- IMPORT STATEMENTS ---
# packages
import os
from telegram_bot import TelegramBot, BotCommand, BotCommandList, InlineButton, ButtonList
from time import sleep
import traceback

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
    # TODO: restrict user
    usertimestamplist.register(chat_id, user_id, time)
    welcome_message = f"Willkommen im Chat, {user_name}!"
    response = bot.sendMessage(chat_id, welcome_message)

    # get message-id of this message and use it as payload for inlinekeyboard
    message_id = response['result']['message_id']
    debug_print (f"New chat member {user_id} in {chat_id} at {time}. Id of welcome-message: {message_id}", DEBUG)
    userwelcomemessagelist.register(chat_id, user_id, message_id)
    welcome_message = f"Willkommen im Chat {user_name}!\nBitte drücke auf den untenstehenden Knopf um der Konversation beitreten zu können:"
    button_dict = ButtonList (InlineButton, [InlineButton("Der Konversation beitreten", url_ = f"https://t.me/rheinhessen_test_group_bot?start={chat_id}_{message_id}")]).toBotDict()
    bot.editMessage(chat_id, message_id, welcome_message, button_dict)

    return response

def createNeededFileStructure():
    # credentials
    os.makedirs("bot_credentials", exist_ok = True)
    if not os.path.exists("bot_credentials/token.txt"):
        open("bot_credentials/token.txt", "w+").close()
    
    if not os.path.exists("bot_credentials/chat_id.txt"):
        open("bot_credentials/chat_id.txt", "w+").close()
    
    # data
    os.makedirs("data", exist_ok = True)

# --- START OF SCRIPT ---

# TODO: create paths and files if not existent

setup.enable()
createNeededFileStructure()

with open('bot_credentials/chat_id.txt', 'r') as file:
    chat_id = file.read()

with open('bot_credentials/token.txt', 'r') as file:
    bot = TelegramBot(file.read(), return_on_update_only=False)
    
bot.deleteBotCommands()
bot.setBotCommands(BotCommandList([BotCommand("sim", "Simulation einer Aktion [event] [parameter]")]))

# create lists
usertimestamplist = UserIdTimestampList("user_id_timestamp.json", time_interval_=10)
userwelcomemessagelist = UserIdList("user_welcome_message.json")

print ("--- Started Rheinhessen TelegramBot ---")

while True:

    for user in usertimestamplist.getExpiredUsers():
        # kick user from chat
        response_ban, _ = bot.kickChatMember(user[0], user[1])
        debug_print (f"kicked user {user[1]} in {user[0]}: [{response_ban[list(response_ban)[-1]]}]", DEBUG)
        usertimestamplist.unregister(user[0], user[1])

        # delete welcome_message
        bot.deleteMessage(user[0], userwelcomemessagelist.getList()[user[0]][user[1]])
        userwelcomemessagelist.unregister(user[0], user[1])

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
            try:
                payload_data = payload.split("_")   # 0: chat_id, 1: message_id

                if payload_data[0] in usertimestamplist:
                    if payload_data[1] in usertimestamplist.getList()[payload_data[0]]:
                        bot.sendMessage(update.message.chat.id, "Willkommen in der Gang! Es geht weiter!")
                        usertimestamplist.unregister (payload_data[0], update.message.sender.id)
                        welcome_string = f"Willkommen in der Gruppe, {update.message.sender.first_name}!"
                        bot.editMessage(payload_data[0], userwelcomemessagelist.getList()[payload_data[0]][str(update.message.sender.id)], welcome_string, {})
                        userwelcomemessagelist.unregister (payload_data[0], update.message.sender.id)
                    else:
                        bot.sendMessage(update.message.chat.id, "Du bist schon in der Gruppe drin!")
                    
                    # TODO: update user permissions
            except Exception as e:
                print (traceback.format_exc())

        # --- SIMULATION OF GROUP-JOINING ---
        if "/sim" in command:
            # simulate different states of script

            if "join" in command_params:
                # simulate first join in group

                user_id = command_params.replace("join", "").replace(" ", "")

                #TODO: get user_name from group if user_param is given
                chat_member = bot.getChatMember(update.message.chat.id, user_id if user_id else update.message.sender.id)
                newChatMember(update.message.chat.id, user_id if user_id else update.message.sender.id, chat_member.user.first_name if chat_member else "None", update.message.date)
            
            """
            # simulation registration is not neccessary as it is integrated in "/sim join"
            if command_params == "reg":
                # simlate registering of user
                usertimestamplist.register(update.message.chat.id, update.message.sender.id, update.message.date)
            
            if command_params == "unreg":
                # simlate unregistering of user
                usertimestamplist.unregister(update.message.chat.id, update.message.sender.id)
            """

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
    
    # security issue: check if correct user has pressed correct button for his message
    # temporarily store user with connected message-id and check with:

    if update.isCallback():
        print ("Callback!")
        # TODO: see above
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

