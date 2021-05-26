import sqlite3
import os
import time
import asyncio
from threading import Thread
import json
from singleton_decorator import singleton
import discord
import tweepy

settings = {}
with open('settings.json', 'r') as f:
   settings = json.loads(f.read())

consumer_key = settings['consumer_key']
consumer_secret = settings['consumer_secret']
access_token = settings['access_token']
access_token_secret = settings['access_token_secret']
discord_token = settings['discord_token']

@singleton
class DiscordBot:
    client = discord.Client(intents=discord.Intents.all())
    ready = False
    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.client.start(discord_token))
        t = Thread(target=loop.run_forever)
        t.start()

    def post(self, twitter_id, msg, text_channel):
        function = asyncio.run_coroutine_threadsafe(self._post(twitter_id, msg, text_channel), self.client.loop)
        function.result()

    async def _post(self, twitter_id, msg, text_channel):
        channel = self.client.get_channel(text_channel)
        embed = discord.Embed(title=twitter_id, description=msg, color=0xff0000)
        await channel.send(embed=embed)

    @client.event 
    async def on_message(message):
        print(message)

    @client.event
    async def on_ready():
        DiscordBot().ready = True


def runDiscord():
    db = DiscordBot()
    db.run()

def main():
    # DiscordBotの起動
    db = DiscordBot()
    db.run()

    # Botの起動待ち
    while DiscordBot().ready == False:
        print('waiting DiscordBot')
        time.sleep(1)

    # 存在しなかったらDBを作成する
    if os.path.isfile('tweet.db') == False:
        con = sqlite3.connect('tweet.db')
        cur = con.cursor()
        cur.execute('''CREATE TABLE tweet(
                    id INTEGER PRIMARY KEY,
                    message TEXT
        )
        ''')
        con.commit()
        con.close()

    # TwitterのAPIを叩く準備
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    while True:
        for follow in settings['follow']:
            con = sqlite3.connect('tweet.db')
            cur = con.cursor()
            timeline = api.user_timeline(follow['twitter_id'])
            for status in reversed(timeline):
                query = 'SELECT * FROM tweet WHERE id = \'' + str(status.id) +'\''
                print(query)
                cur.execute(query)
                ret = cur.fetchall()
                if len(ret) == 0:
                    text = status.text.replace('\'', '\'\'')
                    query = 'INSERT INTO tweet values(' + str(status.id) + ', \'' + text + '\')'
                    print(query)
                    cur.execute(query)
                    # Discordにメッセージを投稿
                    db = DiscordBot()
                    db.post(follow['twitter_id'], status.text, follow['text_channel'])
            con.commit()
            con.close()
        time.sleep(60)

if __name__ == '__main__':
    main()
