import os
import sys
import json
import math
import time
import asyncio
import requests
import threading
import numpy as np
from datetime import datetime
from twitchAPI.helper import first
from quart import Quart, redirect, request
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch, TwitchUser
from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.object.eventsub import ChannelFollowEvent
from twitchAPI.type import AuthScope, ChatEvent, TwitchAPIException, EventSubSubscriptionConflict, EventSubSubscriptionError, EventSubSubscriptionTimeout, TwitchBackendException
from twitchAPI.chat import Chat, EventData, ChatMessage, JoinEvent, JoinedEvent, ChatCommand, ChatUser

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
from twitch_config import TwitchConfig
from database_manager import DatabaseManager

init_login : bool
twitch: Twitch
auth: UserAuthenticator


async def shield_info_twitch(chat_command: ChatCommand):
     await chat_command.reply('StreamerShield is the AI ChatBot to rid twitch once and for all from scammers. More information here: https://linktr.ee/caesarlp')


class StreamerShieldTwitch:
    global twitch, auth
    chat : Chat
    commands : dict
    is_armed : bool
    
    def __init__(self, twitch_config : TwitchConfig) -> None:
        self.eventsub = None
        self.__app_id = twitch_config.app_id
        self.__app_secret = twitch_config.app_secret
        self.user_scopes = twitch_config.user_scopes
        self.user_name = twitch_config.user_name
        self.is_armed  = twitch_config.is_armed
        self.ban_reason = twitch_config.ban_reason
        self.l = twitch_config.logger
        self.await_login = True
        self.even_subs = []
        self.auth_url = twitch_config.auth_url
        self.shield_url = twitch_config.shield_url
        self.eventsub_url = twitch_config.eventsub_url
        self.collect_data = twitch_config.collect_data
        self.age_threshold = twitch_config.age_threshold
        self.admin = twitch_config.admin
        self.db_manager = DatabaseManager(twitch_config)

        self.commands = {
        "help":{
                "help": "!help: prints all commands",
                "value": False,
                "cli_func": self.help_cli,
                "twt_func": self.help_twitch,
                "permissions": 0
            },
        "stop":{
                "help": "!stop: stops the process (Not available for Twitch)",
                "value": False,
                "cli_func": self.stop_cli,
                "twt_func": self.stop_twitch,
                "permissions": 10
        },
        "arm":{
                "help": "!arm: enables StreamerShield to ban users",
                "value": False,
                "cli_func": self.arm_cli,
                "twt_func": self.arm_twitch,
                "permissions": 10
                },
        "disarm":{
                "help": "!disarm: stops StreamerShield from banning users",
                "value": False,
                "cli_func": self.disarm_cli,
                "twt_func": self.disarm_twitch,
                "permissions": 5
                },
        "leave_me":{
                "help": "!leave_me: leaves this chat",
                "value": False,
                "cli_func": self.leave_cli,
                "twt_func": self.leave_me_twitch,
                "permissions": 5
                },
        "leave":{
                "help": "!leave chat_name: leaves a chat",
                "value": True,
                "cli_func": self.leave_cli,
                "twt_func": self.leave_twitch,
                "permissions": 10
                },
        "whitelist":{
                "help": "!whitelist user_name: whitelist user",
                "value": True,
                "cli_func": self.whitelist_cli,
                "twt_func": self.whitelist_twitch,
                "permissions": 5
                },
        "unwhitelist":{
                "help": "!unwhitelist user_name: removes user from whitelist",
                "value": True,
                "cli_func": self.unwhitelist_cli,
                "twt_func": self.unwhitelist_twitch,
                "permissions": 5
                },
        "blacklist":{
                "help": "!blacklist user_name: blacklist user",
                "value": True,
                "cli_func": self.blacklist_cli,
                "twt_func": self.blacklist_twitch,
                "permissions": 5
                },
        "unblacklist":{
                "help": "!unblacklist user_name: removes user from blacklist",
                "value": True,
                "cli_func": self.unblacklist_cli,
                "twt_func": self.unblacklist_twitch,
                "permissions": 5
                }, 
        "streamershield":{
            "help": "!streamershield : prints info about the shield",
                "value": False,
                "cli_func": self.shield_info_cli,
                "twt_func": shield_info_twitch,
                "permissions": 0
                },
        "shield":{
            "help": "!shield : prints info about the shield",
                "value": False,
                "cli_func": self.shield_info_cli,
                "twt_func": shield_info_twitch,
                "permissions": 0
                },
        "pat":{
            "help": "!pat [user_name] : pats user",
                "value": True,
                "cli_func": self.pat_cli,
                "twt_func": self.pat_twitch,
                "permissions": 0
                }
        ,
        "scam":{
            "help": "!scam [user_name] : evaluates username, if given",
                "value": True,
                "cli_func": self.scam_cli,
                "twt_func": self.scam_twitch,
                "permissions": 0
                },
        "test":{
            
            "help": "!scam [user_name] : evaluates username, if given",
                "value": True,
                "cli_func": self.test_cli,
                "twt_func": self.test_twitch,
                "permissions": 10
        }
        }
          
    
    async def run(self):
        global twitch, auth, app, init_login
        
        self.l.info("Shield Starting up")
        
        # Initialize database connection
        await self.db_manager.initialize_pool()
        await self.db_manager.create_tables()

        twitch = await Twitch(self.__app_id, self.__app_secret)
        auth = UserAuthenticator(twitch, self.user_scopes, url=self.auth_url)

        while self.await_login:
            try:
                self.l.info("Shield awaiting initial login")
                await asyncio.sleep(3)
            except KeyboardInterrupt:
                self.l.fail("Keyboard Interrupt, exiting")
                await self.db_manager.close_pool()
                raise KeyboardInterrupt("User specified shutdown")
        self.l.passingblue("Shield initial login successful")
        self.l.passingblue("Welcome home Chief!")
        
        self.eventsub = EventSubWebhook(self.eventsub_url, 8080, twitch, revocation_handler=self.esub_revoked)
        await self.eventsub.unsubscribe_all() # unsub, otherwise stuff breaks
        self.eventsub.start()
        
        self.l.passingblue("Started EventSub")
        
        self.user = await first(twitch.get_users(logins=self.user_name))
        self.chat = await Chat(twitch)

        # register the handlers for the events you want
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.JOIN, self.on_join)
        self.chat.register_event(ChatEvent.JOINED, self.on_joined)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)

        for command, value in self.commands.items():
            self.chat.register_command(command, value['twt_func'])
        self.chat.start()
        
        self.running = True
        
        try:
            await self.cli_run()
        finally:
            await self.db_manager.close_pool()

    def esub_revoked(self, diction : dict):
        self.l.error(f"EventSub was revoked {diction}")
            
            
    ### CLI Command Handling
    async def command_handler(self, command :str):
        parts = command.split(" ")
        if parts[0] == '':
            return
        if parts[0] not in self.commands.keys():
            self.l.error(f'Command {parts[0]} unknown')
        if self.commands[parts[0]]['value']:
           await self.commands[parts[0]]['cli_func'](parts[0])
           return
        await self.commands[parts[0]]['cli_func']()
        
    async def cli_run(self):
        while self.running:
            try:
                com = input("type help for available commands\n")
                await self.command_handler(com)
            except Exception as e:
                self.l.error(f'Exeption in cli_run, exiting: {e}')
                exit(1)
    
    def shield_info_cli(self):
        self.l.info('''
                    StreamerShield is the AI ChatBot to rid twitch once and for all from scammers. More information here: https://linktr.ee/caesarlp
                    ''')
    
    def help_cli(self):
        for command, value in self.commands.items():
            self.l.passing(f'{value["help"]}')
            
    async def stop_cli(self):
        self.l.fail("Stopping!")
        try:
            self.chat.stop() #sometimes is already gone when stopped, so...
        except Exception:
            pass
        try:
            await twitch.close()
        except Exception:
            pass
        raise Exception("Stopped by User") #not the most elegant but works
    
    def arm_cli(self):
        self.l.warning("Armed StreamerShield")
        self.is_armed = True
        
    def disarm_cli(self):
        self.l.warning("Disarmed StreamerShield")
        self.is_armed = False
    
    def join_me_cli(self):
        self.l.error("Cannot invoke join_me from cli, please use join instead")
    
    async def join_chat(self, name:str):
        global twitch
        unable_to_join = await self.chat.join_room(name)

        if unable_to_join:
            self.l.error(f"Unable to join {name}: {unable_to_join}")
            return f"Unable to join {name}: {unable_to_join}"
        if self.chat.is_mod(name):
            self.l.passing(f"Successfully joined {name}")
            user = await first(twitch.get_users(logins=name))
            await self.db_manager.add_joinable_channel(name)
            try:
                await self.new_follow_esub(user.id)
            except Exception:
                return "Unable to init EventSub, contact Admin"
            return f"Successfully joined {name}"
        self.l.error(f"Successfully joined {name}, but no mod status")
        return f"Successfully joined {name}, but no mod status"

    async def new_follow_esub(self, id : str):
        try:
            self.l.info(f"Initializing Follow ESub")  
            await self.eventsub.listen_channel_follow_v2(id, self.user.id, self.on_follow) 
        except EventSubSubscriptionConflict as e:
            self.l.error(f'Error whilst subscribing to eventsub: EventSubSubscriptionConflict {e}')
        except EventSubSubscriptionTimeout as e:
            self.l.error(f'Error whilst subscribing to eventsub: EventSubSubscriptionTimeout {e}')
        except EventSubSubscriptionError as e:
            self.l.error(f'Error whilst subscribing to eventsub: EventSubSubscriptionError {e}')
        except TwitchBackendException as e:
            self.l.error(f'Error whilst subscribing to eventsub: TwitchBackendException {e}')
        
        
    async def leave_cli(self, name:str):
        await self.chat.leave_room(name)
        await self.db_manager.remove_joinable_channel(name)
        self.l.passing(f"Left {name}")
        
    async def whitelist_cli(self, name:str):
        await self.db_manager.add_to_whitelist(name)
        self.l.passing(f"Whitelisted {name}")

    async def unwhitelist_cli(self, name:str):
        await self.db_manager.remove_from_whitelist(name)
        self.l.passing(f"Unwhitelisted {name}")

    async def blacklist_cli(self, name:str):
        await self.db_manager.add_to_blacklist(name)
        self.l.passing(f"Blacklisted {name}")

    async def unblacklist_cli(self, name:str):
        await self.db_manager.remove_from_blacklist(name)
        self.l.passing(f"Unblacklisted {name}")

    async def scam_cli(self, name:str):
        conf = await self.request_prediction(name) #will come in *1000 for use in json
        self.l.info(f'User {name} returns conf {conf/1000}')
  
    def pat_cli(self, name:str):
        self.l.passingblue(f"You're a good boi!")
    
    async def test_cli(self, name:str):
        self.l.info(f'Restricting {name}')
        await self.chat.send_message('caesarlp', f'/restrict {name}')
    
    ### Twitch Command Handling

    async def help_twitch(self, chat_command : ChatCommand):
        permission = await self.generate_permissions(chat_command)
        reply = ''
        for command, value in self.commands.items():
            if permission < value['permissions']:
                continue
            if len(reply)+ len(f'{value["help"]}; ') > 255:
                await chat_command.reply(reply)
                reply = ''
            reply += f'{value["help"]}; '
        await chat_command.reply(reply)
        
    async def stop_twitch(self, chat_command:ChatCommand):
        if await self.verify_permission(chat_command, "disarm"):
            await chat_command.reply("StreamerShield can only be shutdown via cli")
           
    async def arm_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(chat_command, "arm"):
            await chat_command.reply("Armed StreamerShield")
            self.l.warning("Armed StreamerShield")
            self.is_armed = True
        
    async def disarm_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(chat_command, "disarm"):
            await chat_command.reply("Disarmed StreamerShield")
            self.l.warning("Disarmed StreamerShield")
            self.is_armed = False
    
    async def leave_me_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(
            chat_command, "leave_me") and (
                chat_command.parameter != chat_command.room.name):
            await chat_command.reply("Leaving... Bye!")
            await self.db_manager.remove_joinable_channel(chat_command.parameter)
            await self.chat.leave_room(chat_command.parameter)
            
    async def leave_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(
            chat_command, "leave") and (
                chat_command.parameter != chat_command.room.name):
            await chat_command.reply("Leaving... Bye!")
            await self.db_manager.remove_joinable_channel(chat_command.parameter)
            await self.chat.leave_room(chat_command.parameter)
        
    async def whitelist_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(chat_command, "whitelist"):
            name = chat_command.parameter.replace("@", "")
            await self.db_manager.add_to_whitelist(name)
            await chat_command.reply(f'User {name} is now whitelisted')
        
    async def unwhitelist_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(chat_command, "unwhitelist"):
            name = chat_command.parameter.replace("@", "")
            await self.db_manager.remove_from_whitelist(name)
            await chat_command.reply(f'User {name} is no longer whitelisted')
            
    async def blacklist_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(chat_command, "blacklist"):
            name = chat_command.parameter.replace("@", "")
            await self.db_manager.add_to_blacklist(name)
            await chat_command.reply(f'User {name} is now blacklisted')
        
    async def unblacklist_twitch(self, chat_command : ChatCommand):
        if await self.verify_permission(chat_command, "unblacklist"):
            name = chat_command.parameter.replace("@", "")
            await self.db_manager.remove_from_blacklist(name)
            await chat_command.reply(f'User {name} is no longer blacklisted')
    
    async def scam_twitch(self, chat_command : ChatCommand):
        name = None
        if chat_command.parameter:
           name = chat_command.parameter.replace("@", "")
        if not name:
            name = chat_command.user.name
            
        conf = await self.request_prediction(name) #will come in *1000 for use in json
            
        await chat_command.reply(f'@{name} is to {conf/10}% a scammer')
        
    async def pat_twitch(self, chat_command : ChatCommand):
        self_pat = False
        name = None
        if chat_command.parameter:
            name = chat_command.parameter.replace("@", "")
        if not name:
            self_pat = True
            name = chat_command.user.name

        pats = await self.db_manager.increment_pat_counter()

        if self_pat:
            await chat_command.reply(f"You just gave yourself a pat on the back! well deserved LoveYourself {pats} pats have been given")
            return
        await chat_command.reply(f'@{chat_command.user.name} gives @{name} a pat! peepoPat {pats} pats have been given')
    
    async def test_twitch(self,  chat_command : ChatCommand):
        name = chat_command.parameter.replace("@", "")
        await chat_command.reply(f'Trying to restrict user {name}')
        self.l.info(f'Restricting {name}')
        await self.chat.send_raw_irc_message(f'/restrict {name}')
    ###Event Subs and Chat events
    
    async def on_ready(self,ready_event: EventData):
        channels = await self.db_manager.get_joinable_channels()
        channels.append(self.chat.username)
        await ready_event.chat.join_room(channels)
        for channel in channels:
            user = await first(twitch.get_users(logins = [channel]))
            try:
                await self.new_follow_esub(user.id)
            except:
                self.l.error(f"Follow ESub for {user.login} not initialized")
            self.l.info(f"Follow Esub for {user.login} initialized")  
    
    async def on_joined(self, joined_event: JoinedEvent):
        await joined_event.chat.send_message(joined_event.room_name, "This Chat is now protected with StreamerShield! protecc")
        
    async def on_message(self, msg : ChatMessage):
        name = msg.user.name
        privilege = (msg.user.mod or msg.user.vip or msg.user.subscriber or msg.user.turbo)
        if(privilege):
            await self.db_manager.add_to_whitelist(name)
            return
        await self.check_user(name, msg.room.room_id)
        
    async def on_join(self, join_event : JoinEvent):
        name = join_event.user_name
        
        await self.check_user(name, join_event.room.room_id)
    
    
    # Onfollow will only work with headless webhook approach
       
    async def on_follow(self, data: ChannelFollowEvent):
        name = data.event.user_name
        self.l.passing(f"WE GOT A FOLLOW!!!!! {name}")
        await self.check_user(name, data.event.broadcaster_user_id)
    
    
    ### StreamerShield Main
    async def check_user(self, name :str, room_name_id):
        if await self.check_white_list(name): 
            self.l.info(f"{name} is found in whitelist")
            return
        if await self.check_black_list(name): 
            self.l.warning(f"{name} is found in blacklist")
            if self.is_armed:
                user = await first(twitch.get_users(logins=name))
                await self.chat.send_message(room_name_id, f'/restrict {name}')
                #await twitch.ban_user(room_name_id, room_name_id, user.id, self.ban_reason)
            return
        #get prediction from REST 
        conf = await self.request_prediction(name) #will come in *1000 for use in json
        
        #if datacollection is turned on, collect known users and their account age
        user = await first(twitch.get_users(logins=name))
        if self.collect_data and (not await self.check_known_users(name)):
            age = await self.calculate_account_age(user)
            await self.db_manager.add_known_user(
                name,
                confidence_score=math.floor(conf),
                account_age_years=age[0],
                account_age_months=age[1],
                account_age_days=age[2]
            )

        conf = conf/1000 #turn into actual conf 0...1
        #check for account age    
        if await self.check_account_age(user=user):
            self.l.passing(f'Found Account older than {self.age_threshold} Months, name : {name}, conf: {conf})')
            return
        
        
        if (bool(np.round(conf))):
            if self.is_armed:
                #TODO: Check either for account age or follow count if possible
                self.l.fail(f'Banned user {name}')
                await twitch.ban_user(room_name_id, self.user.id, user.id, self.ban_reason) #self.user to ban using the Streamershield account
            self.l.warning(f'User {name} was classified as a scammer with conf {conf}')
            return
        self.l.passing(f'User {name} was classified as a human with conf {conf}')
            
    
    async def calculate_account_age(self, user: TwitchUser):
        current_time = datetime.now()
        creation_time = user.created_at
        age_year = current_time.year - creation_time.year
        age_months = current_time.month - creation_time.month
        age_days = current_time.day - creation_time.day
        return(age_year, age_months, age_days)
    
    ### Utility functions    
    async def check_account_age(self, user: TwitchUser):
        age = await self.calculate_account_age(user)
        
        if age[0] > 0:
            return True
        elif age[1] > self.age_threshold:
            return True
        return False
            
    
    async def generate_permissions(self, chat_command : ChatCommand):
        if(chat_command.user.name == self.admin):
            permission = 10
        elif(chat_command.user.mod or chat_command.user.name == chat_command.room.name):
            permission = 5
        elif(not (chat_command.user.mod or chat_command.user.name == chat_command.room.name)):
            permission = 0
        return permission
    
    async def verify_permission(self, chat_command : ChatCommand, command : str):
        permission = await self.generate_permissions(chat_command)
        return self.commands[command]["permissions"] <= permission
    
    async def user_refresh(token: str, refresh_token: str):
        print(f'my new user token is: {token}')

    async def app_refresh(token: str):
        print(f'my new app token is: {token}')
        
    async def check_white_list(self, name):
        return await self.db_manager.is_whitelisted(name)

    async def check_black_list(self, name):
        return await self.db_manager.is_blacklisted(name)

    async def check_known_users(self, name: str):
        return await self.db_manager.is_known_user(name)

    def write_list(self, name_list, file_path):
        try:
            with open(os.path.join(file_path), "w") as f:
                f.write(json.dumps(name_list, indent=4))  # Use indent for pretty-printing
        except Exception as e:
            print(f"An error occurred while writing to {file_path}.json: {str(e)}")

    def check_for_privilege(self, user : ChatUser):
        if user.mod or user.vip or user.subscriber or user.turbo:
            # Note: This should be async but keeping it sync for compatibility
            # In production, you might want to refactor this
            return True
        return False

    # Remove the old load_list and list_update methods as they're replaced by database operations
    async def request_prediction(self, name : str):
        data = {"input_string": name}

        response = requests.post(self.shield_url, json=data)

        if response.status_code == 200:
            return response.json()["result"]
            
        else:
            self.l.error(response.json())


app = Quart(__name__)

chat_bot: StreamerShieldTwitch
TARGET_SCOPE : list
app.secret_key = 'your_secret_key'







@app.route('/login')
def login():
    return redirect(auth.return_auth_url())



@app.route('/login/confirm')
async def login_confirm():
    global session, chat_bot
    args = request.args
    state = request.args.get('state')
    if state != auth.state:
        return 'Bad state', 401
    code = request.args.get('code')
    if code is None:
        return 'Missing code', 400
    try:
        token, refresh = await auth.authenticate(user_token=code)
       
        if chat_bot.await_login:
            await twitch.set_user_authentication(token, TARGET_SCOPE, refresh)
            ret_val = "Welcome home chief!"
            
        user_info = await first(twitch.get_users())
        name = user_info.login
        
        if not chat_bot.await_login:
            ret_val =  await chat_bot.join_chat(name)
        
    except TwitchAPIException as e:
        return 'Failed to generate auth token', 400
    
    chat_bot.await_login = False
    return ret_val


    

 
def main():
    asyncio.run(chat_bot.run())


        
        
        



if __name__ == "__main__":
    config = TwitchConfig()
    TARGET_SCOPE = config.user_scopes

    chat_bot = StreamerShieldTwitch(config)
    
    process2 = threading.Thread(target=main)

    process2.start()
    app.run('0.0.0.0')

    process2.join()
