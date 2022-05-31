import asyncio
import os
import random
import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
import discord.voice_client
from yt_dlp import YoutubeDL
from random import choice

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.08):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


def is_connected(ctx):
    voice_client = ctx.message.guild.voice_client
    return voice_client and voice_client.is_connected()

prefix = '-'
client = commands.Bot(command_prefix=prefix)

status = ['{}:"_"{}', '}"_"{','{-_-}']
queue = []
isLoop = False
isShake = False


@client.event
async def on_ready():
    change_status.start()
    print('Bot is online!')


@client.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='general')
    await channel.send(f'Welcome {member.mention}! See `{prefix}help` command for details!')


@client.command(name='ping', help='This command returns the latency')
async def ping(ctx):
    await ctx.send(f'**Pong!** Latency: {round(client.latency * 1000)}ms')


@client.command(name='hello', help='This command returns a random welcome message')
async def hello(ctx):
    responses = ['***grumble*** Why did you wake me up?', 'Top of the morning to you lad!', 'Hello, how are you?', 'Hi',
                 '**Wasssuup!**']
    await ctx.send(choice(responses))


@client.command(name='die', help='This command returns a random last words')
async def die(ctx):
    responses = ['why have you brought my short life to an end', 'i could have done so much more',
                 'i have a family, kill them instead']
    await ctx.send(choice(responses))


@client.command(name='join', help='This command makes the bot join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return

    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()


@client.command(name='leave', help='This command stops the music and makes the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()


@client.command(name='loop', help='This command toggles loop mode')
async def loop_(ctx):
    global isLoop

    if isLoop:
        await ctx.send('Loop mode is now `False!`')
        isLoop = False

    else:
        await ctx.send('Loop mode is now `True!`')
        isLoop = True


@client.command(name='play', help='This command plays music')
async def play(ctx, *, url=''):
    global queue
    if url != '':
        queue.append(url)
        await ctx.send(f'`{url}` added to queue!')

    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return

    elif len(queue) == 0 and not isLoop:
        await ctx.send(f'Nothing in your queue! Use `{prefix}queue` to add a song!')

    else:
        try:
            channel = ctx.message.author.voice.channel
            await channel.connect()
        except:
            pass

    server = ctx.message.guild
    voice_channel = server.voice_client
    isEnd = False
    while not isEnd:
        try:
            while voice_channel.is_playing() or voice_channel.is_paused():
                await asyncio.sleep(2)
                pass

        except AttributeError:
            pass

        if len(queue) == 0 and not isLoop:
            await leave(ctx)
            isEnd = True
        else:
            try:
                async with ctx.typing():
                    player = await YTDLSource.from_url(queue[0], loop=client.loop)
                    voice_channel.play(player)

                    if isLoop:
                        queue.append(queue[0])

                    del (queue[0])

                await ctx.send('**Now playing:** {}'.format(player.title))

            except Exception as e:
                print(e)
                await ctx.send(f'Sorry, something went wrong with `{queue[0]}`')
                del (queue[0])


@client.command(name='volume', help='This command changes the bots volume')
async def volume(ctx, volume: int):
    if ctx.voice_client is None:
        return await ctx.send("Not connected to a voice channel.")

    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f"Changed volume to {volume}%")


@client.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.pause()


@client.command(name='resume', help='This command resumes the song!')
async def resume(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.resume()


@client.command(name='clear', help='This command stops the song!')
async def clear(ctx):
    global queue
    queue = []

@client.command(name='skip')
async def skip(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.stop()

@client.command(name='remove')
async def remove(ctx, number):
    global queue

    try:
        del (queue[int(number)+1])
        await ctx.send(f'Your queue is now `{queue}!`')

    except:
        await ctx.send('Your queue is either **empty** or the index is **out of range**')


@client.command(name='queue', help='This command shows the queue')
async def queue(ctx):
    await ctx.send(f'Your queue is now `{queue}!`')


@tasks.loop(seconds=20)
async def change_status():
    await client.change_presence(activity=discord.Game(choice(status)))


@client.command(name='roll')
async def roll(ctx, *, max=100):
    global queue
    rand = random.randrange(max)
    await ctx.send(f' `{ctx.message.author.name}` roll: `{rand}`')

@client.command(name='shake')
@has_permissions(manage_roles=True)
async def shake(ctx, member: discord.Member, count = 3):
    global isShake
    isShake = True
    channel_1 = client.get_channel(981343756294971403)
    channel_2 = client.get_channel(981343795306176593)
    cur_channel = member.voice.channel #return to channel
    if count > 15:
        count = 3
    while count > 0 and isShake:
        await asyncio.sleep(0.35)
        await member.move_to(channel_1)
        await member.move_to(channel_2)
        count -= 1
    await member.move_to(cur_channel)

@client.command(name='stop_shake')
async def stop_shake(ctx):
    global isShake

    if isShake:
        await ctx.send('Shake mode is now `False!`')
        isShake = False

    else:
        await ctx.send('Shake mode is now `True!`')
        isShake = True

client.run(os.environ.get('BOT_TOKEN'))

