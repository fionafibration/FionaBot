#!/usr/bin/python3
# encoding: utf-8

"""
A discord bot for general gaming purposes. Currently contains dice rolling and chess, among other commands.
"""

import random
import asyncio
import aiohttp
import datetime
import json
import io
import regex
import inspect
import chessgame
import initiative
import rolldice
import trueskill
import sys
import markovify
import bs4
import hashlib
import randomart
import copy
import astar
import zlib
import itertools
from fuzzywuzzy import fuzz
from discord import *
from discord.ext.commands import *
from discord import utils

default_config = '''
prefix = ('f?', 'f!', 'F?', 'F!')
token ='DISCORD TOKEN HERE'
clever_api_user = 'CLEVERBOT USER HERE'
clever_api_key = 'CLEVERBOT KEY HERE'
'''

UCI_REGEX = '([a-h][1-8]){2}(qrknb)?'


class TIOSerializer:
    def __init__(self):
        self.bytes = b''

    def add_variable(self, name, contents: list):
        self.bytes += b'V' + name.encode('utf-8') + b'\0' + str(len(contents)).encode('utf-8') + b'\0'

        for var in contents:
            self.bytes += var.encode('utf-8') + b'\0'

    def add_file(self, name, contents: str):
        self.bytes += b'F' + name.encode('utf-8') + b'\0' + str(len(contents.encode('utf-8'))).encode('utf-8') \
                      + b'\0' + contents.encode('utf-8')

    def add_run(self):
        self.bytes += b'R'

    def add_lang(self, language):
        self.add_variable('lang', [language])

    def add_code(self, code):
        self.add_file('.code.tio', code)

    def add_input(self, contents):
        self.add_file('.input.tio', contents)

    def add_args(self, args):
        self.add_variable('args', args)

    def dump(self):
        return self.bytes


try:
    import config
except ImportError:
    with open('config.py', 'w') as f:
        f.write(default_config)
    sys.exit()


class ReplacementHelpCommand(HelpCommand):

    def __init__(self, **options):
        self.width = options.pop('width', 80)
        self.indent = options.pop('indent', 2)
        self.sort_commands = options.pop('sort_commands', True)
        self.dm_help = options.pop('dm_help', False)
        self.dm_help_threshold = options.pop('dm_help_threshold', 1000)
        self.commands_heading = options.pop('commands_heading', "Commands:")
        self.no_category = options.pop('no_category', 'No Category')
        self.paginator = options.pop('paginator', None)

        if self.paginator is None:
            self.paginator = Paginator()

        super().__init__(**options)

    def shorten_text(self, text):
        """Shortens text to fit into the :attr:`width`."""
        if len(text) > self.width:
            return text[:self.width - 3] + '...'
        return text

    def get_ending_note(self):
        """Returns help command's ending note. This is mainly useful to override for i18n purposes."""
        command_name = self.invoked_with
        return "Type {0}{1} command for more info on a command.\n" \
               "You can also type {0}{1} category for more info on a category.".format(self.clean_prefix, command_name)

    def add_indented_commands(self, commands, *, heading, max_size=None):
        """Indents a list of commands after the specified heading.
        The formatting is added to the :attr:`paginator`.
        The default implementation is the command name indented by
        :attr:`indent` spaces, padded to ``max_size`` followed by
        the command's :attr:`Command.short_doc` and then shortened
        to fit into the :attr:`width`.
        Parameters
        -----------
        commands: Sequence[:class:`Command`]
            A list of commands to indent for output.
        heading: :class:`str`
            The heading to add to the output. This is only added
            if the list of commands is greater than 0.
        max_size: Optional[:class:`int`]
            The max size to use for the gap between indents.
            If unspecified, calls :meth:`get_max_size` on the
            commands parameter.
        """

        if not commands:
            return

        self.paginator.add_line(heading)
        max_size = max_size or self.get_max_size(commands)

        get_width = utils._string_width
        for command in commands:
            name = command.name
            width = max_size - (get_width(name) - len(name))
            entry = '{0}{1:<{width}} {2}'.format(self.indent * ' ', name, command.short_doc, width=width)
            self.paginator.add_line(self.shorten_text(entry))

    async def send_pages(self):
        """A helper utility to send the page output from :attr:`paginator` to the destination."""
        destination = self.get_destination()
        for page in self.paginator.pages:
            await destination.send(page)

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = '[%s|%s]' % (command.name, aliases)
            if parent:
                fmt = parent + ' ' + fmt
            alias = fmt
        else:
            alias = command.name if not parent else parent + ' ' + command.name

        return '%s%s %s' % (self.clean_prefix, alias, command.signature)

    def add_command_formatting(self, command):
        """A utility function to format the non-indented block of commands and groups.
        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """

        signature = self.get_command_signature(command)
        self.paginator.add_line(signature, empty=True)

    def get_destination(self):
        ctx = self.context
        if self.dm_help is True:
            return ctx.author
        elif self.dm_help is None and len(self.paginator) > self.dm_help_threshold:
            return ctx.author
        else:
            return ctx.channel

    async def prepare_help_command(self, ctx, command):
        self.paginator.clear()
        await super().prepare_help_command(ctx, command)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            # <description> portion
            self.paginator.add_line(bot.description, empty=True)

        no_category = '\u200b{0.no_category}:'.format(self)

        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name + ':' if cog is not None else no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_indented_commands(commands, heading=category, max_size=max_size)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    async def send_command_help(self, command):
        self.add_command_formatting(command)
        self.paginator.close_page()
        await self.send_pages()

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=self.commands_heading)

        if filtered:
            note = self.get_ending_note()
            if note:
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    async def send_cog_help(self, cog):
        if cog.description:
            self.paginator.add_line(cog.description, empty=True)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=self.commands_heading)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()


client = Bot(command_prefix=config.prefix,
             description='''A bot written by fiona#1729 for use in various discord servers.
              Can play chess, roll dice, and track initiative, among other things.''')

client.help_command = ReplacementHelpCommand()


def format_large(number):
    """"
    Formats a number in scientific notation without trailing 0s

    :param number: Number to format in scientific notation
    :return: String of number formatted in scientific notation
    """

    a = '%E' % number
    return a.split('E')[0].rstrip('0').rstrip('.') + 'E' + a.split('E')[1]


def inflate(data):
    decompress = zlib.decompressobj(
        -zlib.MAX_WBITS  # see above
    )
    inflated = decompress.decompress(data)
    inflated += decompress.flush()
    return inflated


async def update_data(users, user):
    """
    Used in the leveling system. If a user is not already included in the users file, add them.

    :param users: JSON object containing users data
    :param user: discord.User to add
    :return:
    """
    users_rating = trueskill.Rating()
    if str(user.id) not in users and not user.bot:
        users[str(user.id)] = {}
        users[str(user.id)]['experience'] = 0
        users[str(user.id)]['level'] = 1
        users[str(user.id)]['trueskill'] = {'mu': users_rating.mu, 'sigma': users_rating.sigma}


async def add_xp(users, user, amount):
    """
    Adds experience to a user in the leveling system

    :param users: JSON object containing users data
    :param user: discord.User to add experience to
    :param amount: Amount of experience to add
    :return:
    """
    if not user.bot:
        users[str(user.id)]['experience'] += amount


async def level_up(users, user, channel):
    """
    Handles user leveling up. Checks if users level has increased and if so displays a message.

    :param users: JSON object containing users data
    :param user: User to check if leveled up
    :param channel: Channel to send message in
    :return:
    """
    if not user.bot:
        experience = users[str(user.id)]['experience']
        lvl_start = users[str(user.id)]['level']
        lvl_end = int(experience ** (1 / 4))

        if lvl_end > lvl_start and lvl_end % 5 == 0 and lvl_end // 5 <= 10:
            await channel.send('%s leveled up to level %s and gained a skill rank! They now have %s skill ranks!' %
                               (user.mention, lvl_end, lvl_end // 5))
            users[str(user.id)]['level'] = lvl_end
        elif lvl_end > lvl_start:
            await channel.send('%s leveled up to level %s!' % (user.display_name, lvl_end))
            users[str(user.id)]['level'] = lvl_end


@client.event
async def on_ready():
    """
    Changes presence and says name

    :return:
    """
    async with aiohttp.ClientSession() as session:
        raw_response = await session.post('https://cleverbot.io/1.0/create',
                                          json={'user': config.clever_api_user, 'key': config.clever_api_key,
                                                'nick': 'Fin'})
        await raw_response.text()
        await session.close()
    link = utils.oauth_url('464543446187769867', permissions=Permissions.all())
    await client.change_presence(activity=Game(name='f?help for help'))
    sys.stdout.write('Logged in as ' + client.user.display_name + '\n')
    sys.stdout.write(('Invite URL:\n%s' % link) + '\n')


@client.event
async def on_member_join(member):
    """
    Adds users to the leveling system file

    :param member: Member that joined.
    :return:
    """
    with open('users.json', 'r') as f:
        users = json.load(f)

    await update_data(users, member)

    with open('users.json', 'w') as f:
        json.dump(users, f)


@client.event
async def on_message(message):
    """
    Handles adding xp on each message and leveling up

    :param message: Message that was sent
    :return:

    """
    if message.author.bot:
        return

    if 'seduce' in message.content.lower():
        await message.channel.send('Seduce me!', file=File('seduce.png'))

    if message.content.lower() == 'mirage':
        await message.channel.send(
            'now dont get me started on the mirage 2000 hahah its so bad like wtf french the best plane they ever made was a flag blown away by the wind it works great actualy but the mirage is so ugly i dont enven now how it can even fly i know a friend is part of the raf he flew three (yes, 3) mirage and the worst was the deux mille i mean its a flying pankace and really how can a french plane work anyway they dont even now how cars work look at renault its so bad right so yes the mirage is pretty shitty right yeah')

    if message.content.lower() == 'thatsthejoke.jpg':
        await message.channel.send('THATS THE JOKE', file=File('thatsthejoke.gif'))
	
    if message.content.lower() in ['it\'s fine', 'its fine', 'i\'m fine', 'im fine', 'i am fine']:
        await message.channel.send('Everything is Fine!', file=File('Z.png'))

    if message.content.lower() == '@someone':
        server = message.guild
        member = random.choice(server.members)
        await message.channel.send(member.mention)

    with open('users.json', 'r') as f:
        users = json.load(f)

    await update_data(users, message.author)
    await add_xp(users, message.author, 7)
    await level_up(users, message.author, message.channel)

    with open('users.json', 'w') as f:
        json.dump(users, f)

    # Do this so we can still use commands
    await client.process_commands(message)


@client.command(description='Grab an invite. Permissions will be all.',
                brief='Get the bot invite link')
async def invitelink(context):
    link = utils.oauth_url('464543446187769867', permissions=Permissions.all())
    await context.send(f"Invite Link:\n`{link}`")


@client.command(description='Query cleverbot. ',
                brief='Query cleverbot.')
async def clever(context, *message):
    message = ' '.join(message)

    async with aiohttp.ClientSession() as session:  # Async HTTP request
        raw_response = await session.post('https://cleverbot.io/1.0/ask',
                                          json={'user': config.clever_api_user, 'key': config.clever_api_key,
                                                'nick': 'Fin', 'text': message})
        response = await raw_response.text()  # Take only the data
        response = json.loads(response)  # Parse the JSON into a format we can use
        # This is the JSON path for the price data in USD
    if response['status'] == 'success':
        await context.send(response['response'])
    else:
        await context.send('Error accessing cleverbot.')


@client.command(description='Check a user\'s level. This command takes one mention. ',
                brief='Check a user\'s level.')
async def level(context, mention: Member):
    if mention.bot:
        await context.send('Bots do not participate in the leveling system!')
        return
    """
    Command to check a user's level

    :param context: Command context
    :param mention: User mentioned in command
    :return:
    """
    with open('users.json', 'r') as f:
        users = json.load(f)

    await context.send('%s is level %s!' % (mention.display_name, users[str(mention.id)]['level']))


@client.command(description='Check a user\'s XP. This command takes one mention. ',
                brief='Check a user\'s XP.')
async def xp(context, mention: Member):
    if mention.bot:
        await context.send('Bots do not participate in the leveling system!')
        return
    """
    Command to check a user's experience

    :param context: Command context
    :param mention: User mentioned in command
    :return:
    """
    with open('users.json', 'r') as f:
        users = json.load(f)

    await context.send('%s has %s experience!' % (mention.display_name, users[str(mention.id)]['experience']))


@client.command(description='List the top 5 users in the server by XP.',
                brief='List top users by XP')
async def top(context):
    with open('users.json', 'r') as f:
        users = json.load(f)

    def get_xp(user):
        try:
            return users[str(user.id)]['experience']
        except:
            return 0

    def get_level(user):
        try:
            return users[str(user.id)]['level']
        except:
            return 0

    if len(context.guild.members) >= 1:
        userList = copy.copy(context.guild.members)
        userList.sort(key=get_xp, reverse=True)
        ranking = ''
        for i in range(10):
            if len(userList[i].display_name) > 20:
                ranking += '%s. %s...: %s levels, %s xp\n' % (
                    i + 1, userList[i].display_name[:17], get_level(userList[i]), get_xp(userList[i]))
            else:
                ranking += '%s. %s: %s levels, %s xp\n' % (
                    i + 1, userList[i].display_name, get_level(userList[i]), get_xp(userList[i]))
        await context.send('Rankings for this server:\n```%s```' % ranking)


@client.command(name='8ball',
                description='Answers a yes/no question. ',
                brief='Answers from the beyond.',
                aliases=['eight_ball', 'eightball', '8-ball'], )
async def eight_ball(context):
    """
    Command to answer a yes or no question.
    Has a chance of answering with a very rude rant.

    :param context: Command context
    :return:
    """
    possible_responses = [  # Classic 8 ball responses without any indecisive ones
        'It is certain',
        'It is decidedly so',
        'Without a doubt',
        'Yes, definitely',
        'You may rely on it',
        'As I see it, yes',
        'Most likely',
        'Outlook good',
        'Yes',
        'Signs point to yes',
        "Don't count on it",
        'My reply is no',
        'My sources say no',
        'Outlook not so good',
        'Very doubtful',
    ]
    rare = random.randint(0, 100)  # One in 100 chance of saying a long rant instead of an actual answer
    if rare != 0:
        await context.send(random.choice(possible_responses) + ', ' + context.message.author.mention)

    else:
        await context.send('God %s that was such a stupid question. Back in my day asking something as monumentally '
                           'moronic as that would get met by a beating. Shame on you and your entire family.' %
                           context.message.author.mention)


# Evaluates a dice roll in critdice format. See https://www.critdice.com/how-to-roll-dice/
@client.command(description='Roll dice using syntax as explained at https://tinyurl.com/pydice ',
                brief='Roll dice.',
                aliases=['die'])
async def dice(context, *roll):
    """
    Command to roll dice in dice notation.
    See tinyurl.com/pydice

    :param context: Command context
    :param roll: Array of parts of the arguments passed to the command. Joined.
    :return:
    """
    try:
        result, explanation = rolldice.roll_dice(''.join(roll))
    except rolldice.DiceGroupException as e:
        await context.send(str(e))
    except rolldice.DiceOperatorException as e:
        await context.send(str(e))
    else:
        if len(explanation) > 300:
            await context.send('Result: %s\n```Explanation too long to display!```' % result)
        else:
            await context.send('Result: %s.\n```%s```' % (result, explanation))


@client.command(
    description='Begin dice rolling mode. Until you type \'end\', all messages you type will be interpreted as dice rolls. All malformed dice rolls will be ignored. ',
    brief='Begin dice rolling mode. ',
    aliases=['diemode'])
async def dicemode(context):
    timed_out = False
    await context.send('Beginning dice rolling mode...')
    while True:
        try:
            msg = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=6000)
        except asyncio.TimeoutError:
            break
        else:
            try:
                result, explanation = rolldice.roll_dice(msg.content)
            except:
                if msg.content.lower() == 'end':
                    await context.send('Exiting dice mode.')
                    return
                continue
            else:
                if len(explanation) > 300:
                    await context.send('Result: %s\n```Explanation too long to display!```' % result)
                else:
                    await context.send('Result: %s.\n```%s```' % (result, explanation))


@client.group()
async def chess(context):
    """
    Chess command group

    :param context: Command context
    :return:
    """
    if context.invoked_subcommand is None:
        await context.send('Invalid chess command.')


@chess.group(description='Starts a game of chess with the bot. To end a game of chess, type \'end\' instead of '
                         'entering your move. You must enter your move within 5 minutes or the game will time out. ',
             brief='Start a game of chess.')
async def new(context):
    """
    New game command group

    :param context: Command context
    :return:
    """
    if context.invoked_subcommand is None:
        await context.send('Invalid new game. Please use the subcommand white or black.')


@cooldown(2, 60, BucketType.user)
@new.command(description='Starts a game of chess with the bot. To end a game of chess, type \'end\' instead of '
                         'entering your move. You must enter your move within 5 minutes or the game will time out. ',
             brief='Start a game of chess as white. ')
async def white(context, easymode: bool = False):
    """
    Command to start a new game of chess vs AI as white

    todo:: Allow for selecting different difficulty levels

    :param context: Command context
    :return:
    """
    timed_out = False

    user = context.message.author

    chess_game = chessgame.ChessGame(difficulty=not easymode)

    await context.send('Starting new game as white.')

    file = chess_game.get_png(chessgame.chess.WHITE)
    file = io.BytesIO(file)
    file = File(file, filename='board.png')
    await context.send('Board:', file=file)
    while True:
        end = False
        if chess_game.check():
            await context.send('White is in check!')
        while True:
            await context.send('Please enter your move in UCI format (eg. e2e4)')
            try:
                movestr = await client.wait_for('message', check=lambda m: (
                    m.author == context.author and m.channel == context.channel), timeout=300)
            except asyncio.TimeoutError:
                end = True
                timed_out = True
                break

            match = regex.search(UCI_REGEX, movestr.content.lower())

            if movestr.content.lower() == 'end':
                end = True
                break

            elif match != None:
                try:
                    chess_game.player_move(movestr.content.lower())
                    break

                except chessgame.InvalidMoveException as e:
                    await context.send(str(e))

        if end:
            break
        await context.send(chess_game.generate_move_digest(user.display_name))
        file = chess_game.get_png(chessgame.chess.WHITE)
        file = io.BytesIO(file)
        file = File(file, filename='board.png')
        await context.send('Board:', file=file)
        if chess_game.is_finished():
            break
        if chess_game.check():
            await context.send('Black is in check!')
        chess_game.ai_move()
        await context.send(chess_game.generate_move_digest('Fin Bot'))
        file = chess_game.get_png(chessgame.chess.WHITE)
        file = io.BytesIO(file)
        file = File(file, filename='board.png')
        await context.send('Board:', file=file)
        if chess_game.is_finished():
            break

    if timed_out:
        await context.send('Game timed out. Next time please make a move within 5 minutes.')

    date_string = f"{datetime.date.today():%Y.%m.%d}"
    pgn = chess_game.get_pgn('Chess Game', 'Discord', date_string, user.display_name, "Fin Bot")

    embed = Embed(title="Chess Game Results", colour=Colour(0xff00), description="```%s```" % pgn)

    embed.set_author(name="Fin Bot", icon_url="https://tinyurl.com/y8p7a8px")

    embed.add_field(name="Human Player: White", value=context.author.display_name)
    embed.add_field(name="Bot Player: Black", value="Fin Bot")
    embed.add_field(name="Final Score", value=chess_game.result())

    await context.send(embed=embed)

    chess_game.engine.close()


@cooldown(2, 60, BucketType.user)
@new.command(description='Starts a game of chess with the bot. To end a game of chess, type \'end\' instead of '
                         'entering your move. You must enter your move within 5 minutes or the game will time out. ',
             brief='Start a game of chess as white.')
async def black(context, easymode: bool = False):
    """
    Command to start a new game of chess vs AI as black

    :param context: Command context
    :return:
    """
    timed_out = False

    user = context.message.author

    chess_game = chessgame.ChessGame(difficulty=not easymode)

    await context.send('Starting new game as black.')

    file = chess_game.get_png(chessgame.chess.BLACK)
    file = io.BytesIO(file)
    file = File(file, filename='board.png')
    await context.send('Board:', file=file)
    while True:
        end = False
        if chess_game.check():
            await context.send('White is in check!')
        chess_game.ai_move()
        await context.send(chess_game.generate_move_digest('Fin Bot'))
        file = chess_game.get_png(chessgame.chess.BLACK)
        file = io.BytesIO(file)
        file = File(file, filename='board.png')
        await context.send('Board:', file=file)
        if chess_game.is_finished():
            break
        if chess_game.check():
            await context.send('Black is in check!')
        while True:
            await context.send('Please enter your move in UCI format (eg. e2e4)')
            try:
                movestr = await client.wait_for('message', check=lambda m: (
                    m.author == context.author and m.channel == context.channel), timeout=300)
            except asyncio.TimeoutError:
                end = True
                timed_out = True
                break

            match = regex.search(UCI_REGEX, movestr.content.lower())

            if movestr.content.lower() == 'end':
                end = True
                break

            elif match != None:
                try:
                    chess_game.player_move(movestr.content.lower())
                    break

                except chessgame.InvalidMoveException as e:
                    await context.send(str(e))
        if end:
            break
        await context.send(chess_game.generate_move_digest(user.display_name))
        file = chess_game.get_png(chessgame.chess.BLACK)
        file = io.BytesIO(file)
        file = File(file, filename='board.png')
        await context.send('Board:', file=file)
        if chess_game.is_finished():
            break

    if timed_out:
        await context.send('Game timed out. Next time please make a move within 5 minutes.')

    date_string = f"{datetime.date.today():%Y.%m.%d}"
    pgn = chess_game.get_pgn('Chess Game', 'Discord', date_string, user.display_name, "Fin Bot")

    embed = Embed(title="Chess Game Results", colour=Colour(0xff00), description="```%s```" % pgn)

    embed.set_author(name="Fin Bot", icon_url="https://tinyurl.com/y8p7a8px")

    embed.add_field(name="Human Player: Black", value=context.author.display_name)
    embed.add_field(name="Bot Player: White", value="Fin Bot")
    embed.add_field(name="Final Score", value=chess_game.result())

    await context.send(embed=embed)

    chess_game.engine.close()


@cooldown(2, 60, BucketType.user)
@new.command(description='Challenge the mentioned user to a game of chess. To end the game, type \'end\'. ',
             brief='Challenge a person to a game of chess')
async def challenge(context, white: Member):
    timed_out = False

    black = context.author

    await context.send('%s, %s has challenged you to a chess game!' % (white.mention, black.mention))

    with open('users.json') as f:
        users = json.load(f)

    if str(white.id) not in users:
        await update_data(users, white)
    elif str(black.id) not in users:
        await update_data(users, black)

    white_rating = trueskill.Rating(**users[str(white.id)]['trueskill'])

    black_rating = trueskill.Rating(**users[str(black.id)]['trueskill'])

    chess_game = chessgame.ChessGame()

    file = chess_game.get_png(chessgame.chess.WHITE)
    file = io.BytesIO(file)
    file = File(file, filename='board.png')
    await context.send('Board:', file=file)

    while True:
        end = False

        # White's move
        while True:
            await context.send('%s, please enter your move in UCI format (eg. e2e4)' % white.mention)
            try:
                move_str = await client.wait_for('message',
                                                 check=lambda m: (m.author == white and m.channel == context.channel),
                                                 timeout=300)
            except asyncio.TimeoutError:
                end = True
                timed_out = True
                break
            if move_str.content.lower() == 'end':
                end = True
                break
            try:
                chess_game.player_move(move_str.content.lower())
                break
            except chessgame.InvalidMoveException as e:
                await context.send(str(e))
        if end:
            white_ended = True
            break
        await context.send(chess_game.generate_move_digest(white.display_name))
        if chess_game.is_finished():
            break

        # Black's move
        file = chess_game.get_png(chessgame.chess.BLACK)
        file = io.BytesIO(file)
        file = File(file, filename='board.png')
        await context.send('Board:', file=file)
        if chess_game.check():
            await context.send('Black is in check!')
        while True:
            await context.send('%s, please enter your move in UCI format (eg. e2e4)' % black.mention)
            try:
                move_str = await client.wait_for('message',
                                                 check=lambda m: (m.author == black and m.channel == context.channel),
                                                 timeout=300)
            except asyncio.TimeoutError:
                end = True
                timed_out = True
                break
            if move_str.content.lower() == 'end':
                end = True
                break
            try:
                chess_game.player_move(move_str.content.lower())
                break
            except chessgame.InvalidMoveException as e:
                await context.send(str(e))
        if end:
            black_ended = True
            break
        await context.send(chess_game.generate_move_digest(black.display_name))
        if chess_game.is_finished():
            break

        file = chess_game.get_png(chessgame.chess.WHITE)
        file = io.BytesIO(file)
        file = File(file, filename='board.png')
        await context.send('Board:', file=file)

    if chess_game.result() == '1-0' or black_ended:
        white_rating, black_rating = trueskill.rate_1vs1(white_rating, black_rating)
    elif chess_game.result() == '0-1' or white_ended:
        black_rating, white_rating = trueskill.rate_1vs1(black_rating, white_rating)

    with open('users.json') as f:
        users = json.load(f)
        users[str(white.id)]['trueskill'] = {'mu': white_rating.mu, 'sigma': white_rating.sigma}
        users[str(black.id)]['trueskill'] = {'mu': black_rating.mu, 'sigma': black_rating.sigma}

    if timed_out:
        await context.send('Game timed out. Next time please make a move within 5 minutes.')

    date_string = f"{datetime.date.today():%Y.%m.%d}"
    pgn = chess_game.get_pgn('Chess Game', 'Discord', date_string, white.display_name, black.display_name)

    embed = Embed(title="Chess Game Results", colour=Colour(0xff00), description="```%s```" % pgn)

    embed.set_author(name="Fin Bot", icon_url="https://tinyurl.com/y8p7a8px")

    embed.add_field(name="White", value='%s\nRating: %0.3f' % (white.display_name, white_rating.mu))
    embed.add_field(name="Black", value='%s\nRating: %0.3f' % (black.display_name, black_rating.mu))
    embed.add_field(name="Final Score", value=chess_game.result())

    await context.send(embed=embed)

    chess_game.engine.close()


@client.command(
    description="Start a new initiative tracker session. Initiative tracking uses three commands: 'next', 'add', and 'remove.'\n"
                "All commands will use the number ID for creatures.\n"
                "Next simply increments the turn to move and deals with any effects that may need to expire.\n"
                "Add takes four arguments: The creature to apply the effect to, the creature who's applying the effect, the length in rounds, and the effect name.\n"
                "E.G. 'add 2 3 4 Stun' adds Stun to creature 2 for 4 rounds, and the effect will deplete on creature 3's turn.\n"
                "Remove takes the number of the creature and the number of the effect.\n"
                "Type 'end' to end the session",
    brief='Initiative tracking',
    name='initiative',
    aliases=['init'])
async def initiative_command(context, *args):
    try:
        assert len(args) % 2 == 0
        assert len(args) > 0
        player_dict = {}
        for i in range(0, len(args), 2):
            player_dict[args[i]] = int(args[i + 1])
    except Exception:
        await context.send('Error parsing list of creatures. Please try again.')
        return
    else:
        await context.send('Starting new initiative tracking session...')
        should_continue = True
        timed_out = False
        init = initiative.InitTracker(player_dict)
        await context.send('```%s```' % init.get_players())
        while should_continue:
            try:
                command = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=6000)
            except asyncio.TimeoutError:
                should_continue = False
                timed_out = True
                continue
            else:
                if command.content.startswith('add'):
                    try:
                        creature = int(command.content.split()[1])
                        creator = int(command.content.split()[2])
                        length = int(command.content.split()[3])
                        description = ' '.join(command.content.split()[4:])
                        await context.send('```%s```' % init.add_cond(creature, creator, length, description))
                    except Exception:
                        await context.send('Malformed add command, please try again.')
                elif command.content.startswith('next'):
                    await context.send('```%s```' % init())
                elif command.content.startswith('remove'):
                    try:
                        creature = int(command.content.split()[1])
                        cond = int(command.content.split()[2])
                        await context.send('```%s```' % init.remove_cond(creature, cond))
                    except Exception:
                        await context.send('Malformed remove commmand, please try again.')
                elif command.content.startswith('end'):
                    await context.send('Ending initiative tracking session.')
                    return
        if timed_out:
            await context.send('Initiative tracking session timed out.')


@client.command(
    description="Attach a text file containing the markov text to be ingested. Takes 1 argument, the number of sentences to generate. ",
    brief="Markov chain text generation.")
async def markov(context, num_sentences: int = 8):
    file = context.message.attachments[0]
    if file.size > 8000000:
        await context.send('The file was too large.')
        return

    f_obj = io.BytesIO(b'')

    await file.save(f_obj, seek_begin=True)

    text = f_obj.read()

    text = text.decode('utf-8')

    text = regex.sub('^[a-zA-Z .,]', '', text)

    print(text)
    print(type(text))

    model = markovify.Text(text)

    sentences = ''

    for i in range(min(num_sentences, 20)):
        sentences += model.make_sentence(tries=100) + " "

    await context.send('Output:\n```%s```' % sentences)


@client.command(description="Fetch a random joke. ",
                brief="Fetch a random joke. ")
async def jokes(context):
    async with aiohttp.ClientSession() as session:  # Async HTTP request
        raw_response = await session.post(
            'http://api.icndb.com/jokes/random?firstName=Fin&lastName=Bot&escape=javascript')
        response = await raw_response.text()  # Take only the data
        response = json.loads(response)  # Parse the JSON into a format we can use
    joke = response['value']['joke']
    joke.replace('\\\'', '\'')
    joke.replace('\\\"', '\"')
    await context.send(joke)


@client.command(description="Send a random pickup line. ",
                brief="Send a random pickup line. ")
async def pickmeup(context):
    async with aiohttp.ClientSession() as session:  # Async HTTP request
        raw_response = await session.get('http://pebble-pickup.herokuapp.com/tweets/random')
        response = await raw_response.text()  # Take only the data
        response = json.loads(response)  # Parse the JSON into a format we can use
    joke = response['tweet']
    await context.send(joke)


@client.command(description="Prune last N messages from a channel ",
                brief="Prune messages. ")
@has_permissions(manage_messages=True)
async def prune(context, amount: int = 1):
    await context.message.channel.purge(limit=amount)


@client.command(description="Inspects the source code for a command. E.G. 'f?source challenge' ",
                brief="Inspect the source code for a command. ")
async def source(context, *command):
    """
    Inspects the source code of a command
    Thanks to https://github.com/shadeyg56/Darkness/
    
    :param context: Command
    :param command: Command to inspect
    """
    source = str(inspect.getsource(client.get_command(' '.join(command)).callback))
    source_formatted = '```py\n' + source.replace('`', '\u200b`') + '\n```'
    if len(source_formatted) > 2000:
        async with aiohttp.ClientSession() as session:
            raw_response = await session.post("https://hastebin.com/documents", data=source)
            response = await raw_response.text()
            response = json.loads(response)
        uid = response['key']
        await context.send('Command source: <https://hastebin.com/%s.py>' % uid)
    else:
        await context.send(source_formatted)


@client.command(description="Search an image link or image attachment for a source from saucenao, "
                            "Optionally add a similarity percentage threshold ",
                brief="Search an image for a source on saucenao.")
async def sauce(context, link=None, similarity: int = 80):
    """
    Reverse image search using saucenao
    Thanks to https://github.com/tailoric/image-search-cog/blob/master/image_search.py for source

    :param context: Command context
    :param link: Link. Leave as none for an attachment search
    :param similarity: Minimum similarity
    """
    file = context.message.attachments
    if link is None and not file:
        await context.send('Message didn\'t contain Image')
    else:
        if file:
            url = file[0]['proxy_url']
            similarity = link
        else:
            url = link
        async with aiohttp.ClientSession() as session:
            response = await session.get('http://saucenao.com/search.php?url={}'.format(url))
            source = None
            if response.status == 200:
                soup = bs4.BeautifulSoup(await response.text(), 'html.parser')
                for result in soup.select('.resulttablecontent'):
                    if int(similarity) > float(result.select('.resultsimilarityinfo')[0].contents[0][:-1]):
                        break
                    else:
                        if result.select('a'):
                            source = result.select('a')[0]['href']
                            await context.send('<{}>'.format(source))
                            return
                if source is None:
                    await context.send('No source over the similarity threshold')


@client.command(description='Gets a computer-generated waifu from the database\n'
                            'Can either get a random ID, or a user-provided one\n'
                            'between 0 and 11999.',
                brief='Waifu generation')
async def animegrill(context, id: int = None):
    if id is None:
        id = random.randint(0, 11999)
    elif id < 0 or id > 11999:
        await context.send('Invalid Waifu ID!')
        return

    with open('waifugen/results-fionabot/finbot-waifu-%s.jpg' % id, 'rb') as f:
        waifu = f.read()
        waifu = io.BytesIO(waifu)
        file = File(waifu, filename='finbot-waifu-%s.jpg' % id)
        await context.send('FionaBot Waifu #%s' % id, file=file)


@client.command(description="Creates an ascii art 'randomart' out of a given string. "
                            "Simply send the command and then type your text once prompted. "
                            "Text will be sanitized of all non-word characters, uppercased, "
                            "and then will be used to generate a unique randomart for that "
                            "phrase."
                            "This is an example of a commitment scheme.",
                brief="Creates a randomart out of text.")
async def art(context):
    await context.send('Waiting for text input.')

    text = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=6000)

    text = text.content.strip('` ').upper()
    text = regex.sub(r'[^\w ]', ' ', text)
    text = regex.sub(r'[ \t]{2,}', ' ', text)

    hex = hashlib.sha3_256(text.encode('utf-8')).hexdigest()

    randomart_str = randomart.randomart(hex, 'FIONABOT')

    await context.send('Your art is:\n```%s```' % randomart_str)


@client.command(description="""Make a board with the following rules:
                            1. Boards must be rectangular
                            2. Board must contain one start tile (S) and one end tile(X)
                            3. Board can contain any number of walls (B)
                            4. Empty spaces are denoted by periods (.)
                            
                            Example:
                            .X.......
                            BBBB.....
                            .....BBBB
                            ........S
                            """,
                brief="AI Pathfinding")
async def pathfind(context):
    await context.send('Please send your board:')

    board = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=6000)
    board = board.content.strip('`"\' \t\n')
    try:
        gif = astar.draw_path(board)
    except Exception as e:
        await context.send(str(e))
    else:
        file = File(gif, filename='pathfinding.gif')
        await context.send('Path:', file=file)


@client.group(description="Command group for running code in over 600 languages.",
              brief="Run code in various languages.")
async def code(context):
    """
    Code command group

    :param context: Command context
    :return:
    """
    if context.invoked_subcommand is None:
        await context.send('Invalid code command.')


@code.command(description="Search the language database for a certain language.",
              brief="Search the language DB for a language")
async def search(context, *langname):
    if not langname:
        await context.send('Need a language name to search!')
        return

    results = {}
    async with aiohttp.ClientSession() as session:
        response = await session.get('https://tio.run/languages.json')

        if response.status == 200:
            body = json.loads(await response.text())

            for lang in body.keys():
                if fuzz.partial_ratio(body[lang]['name'], ' '.join(langname)) > 75:
                    results[lang] = body[lang]['name']
    if results:
        await context.send('Languages results: ```%s```' % '\n'.join([
            '%s: %s' % (id, name) for id, name in results.items()
        ]))
    else:
        await context.send('No results!')


@code.command(description="Run code in a given language.\n"
                          "Please specify the language, and 'true' if you'd like to provide input, "
                          "otherwise false.\n"
                          "You can specify a list of command line arguments you'd like to be provided to the "
                          "language's interpreter",
              brief="Run code in a language.")
async def run(context, language, ask_input: bool = False, *args):
    async with aiohttp.ClientSession() as session:
        response = await session.get('https://tio.run/languages.json')

        if response.status == 200:
            body = json.loads(await response.text())

            if language not in body:
                await context.send('Unknown language!')
                return

    await context.send('Please send your code wrapped in triple backticks!')

    message = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=6000)

    if ask_input:
        await context.send('Please send your code\'s input')

        input_message = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=6000)

        input_message = input_message.content
    else:
        input_message = ''

    message = regex.match(r'^```([\S\s]+)```$', message.content.strip())

    if message is None:
        await context.send('Code was improperly formatted!')
        return

    try:
        code = message[1]

        tio = TIOSerializer()

        tio.add_lang(language)

        tio.add_code(code)

        tio.add_input(input_message)

        tio.add_args(args if args else [])

        tio.add_run()

        byte_data = tio.dump()

        async with aiohttp.ClientSession() as session:
            response = await session.post('https://tio.run/cgi-bin/static/fb67788fd3d1ebf92e66b295525335af-run',
                                          data=zlib.compress(byte_data, 9)[2:-4])

            response_data = zlib.decompress((await response.read())[10:], wbits=-15)

        split = response_data[:16]

        split_data = regex.split(regex.escape(split), response_data)

        await context.send('\n'.join(['```%s```' % piece.decode('utf-8', errors='replace') for piece in split_data if
                                      piece.decode('utf-8', errors='replace')]))

    except:
        await context.send('Error running program!')


sys.stdout.write('Starting...\n')
client.run(config.token)
