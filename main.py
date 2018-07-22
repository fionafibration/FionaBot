#!/usr/bin/python
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
import itertools
import regex
import inspect
import sys
import chessgame
import initiative
import rolldice
from discord import *
from discord.ext.commands import *

defaultconfig = '''
prefix = ('f?', 'f!', 'F?', 'F!')
token ='DISCORD TOKEN HERE'
clever_api_user = 'CLEVERBOT USER HERE'
clever_api_key = 'CLEVERBOT KEY HERE'
'''


try:
    import config
except ImportError:
    with open('onfig.py', 'w') as f:
        f.write(defaultconfig)
    sys.exit()

class ProperHelp(HelpFormatter):
    async def format(self):
        """
        Handles the actual behaviour involved with formatting.
        To change the behaviour, this method should be overridden.

        :return: List: A paginated value of the help command
        """
        self._paginator = Paginator()

        # we need a padding of ~80 or so

        description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)

        if description:
            # <description> portion
            self._paginator.add_line(description, empty=True)

        if isinstance(self.command, Command):
            # <signature portion>
            signature = self.get_command_signature()
            self._paginator.add_line(signature, empty=True)

            # Don't want to include the docstring
            '''# <long doc> section
            if self.command.help:
                self._paginator.add_line(self.command.help, empty=True)
            '''

            # end it here if it's just a regular command
            if not self.has_subcommands():
                self._paginator.close_page()
                return self._paginator.pages

        max_width = self.max_name_size

        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'

        filtered = await self.filter_command_list()
        if self.is_bot():
            data = sorted(filtered, key=category)
            for category, commands in itertools.groupby(data, key=category):
                # there simply is no prettier way of doing this.
                commands = sorted(commands)
                if len(commands) > 0:
                    self._paginator.add_line(category)

                self._add_subcommands_to_page(max_width, commands)
        else:
            filtered = sorted(filtered)
            if filtered:
                self._paginator.add_line('Commands:')
                self._add_subcommands_to_page(max_width, filtered)

        # add the ending note
        self._paginator.add_line()
        ending_note = self.get_ending_note()
        self._paginator.add_line(ending_note)
        return self._paginator.pages


formatter = ProperHelp()

client = Bot(command_prefix=config.prefix,
             description='''A bot written by Finianb1 for use in various discord servers.
              Can play chess, roll dice, and track initiative, among other things.''', formatter=formatter)
# Change directory to script's directory. Used for opening chess engine and level file.


def format_large(number):
    """"
    Formats a number in scientific notation without trailing 0s

    :param number: Number to format in scientific notation
    :return: String of number formatted in scientific notation
    """

    a = '%E' % number
    return a.split('E')[0].rstrip('0').rstrip('.') + 'E' + a.split('E')[1]


async def update_data(users, user):
    """
    Used in the leveling system. If a user is not already included in the users file, add them.

    :param users: JSON object containing users data
    :param user: discord.User to add
    :return:
    """
    if str(user.id) not in users and not user.bot:
        users[str(user.id)] = {}
        users[str(user.id)]['experience'] = 0
        users[str(user.id)]['level'] = 1


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
        raw_response = await session.post('https://cleverbot.io/1.0/create', json={'user': config.clever_api_user, 'key': config.clever_api_key, 'nick': 'Fin'})
        await raw_response.text()
        await session.close()
    link = utils.oauth_url('464543446187769867', permissions=Permissions.all())
    await client.change_presence(activity=Game(name='f?help for help'))
    print('Logged in as ' + client.user.display_name)
    print('Invite URL:\n%s' % link)


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
    names = ['xX_PussyDestroyer_CoDKid_Xx',
             'XxX_Sp4Rt4nTA-k3r69_XxX',
             'crackmonkey69',
             'DrAgOnBlaDe69',
             'pimp.daddy.420@thotmail.com',
             'yonkerslady@yahoo.com',
             ]
    match = regex.match(r"([Ii]['\"`]*[Mm])([a-zA-Z0-9 \t'\".,]+)", message.content)
    if not match is None:
        await message.channel.send("Hi {0}, I'm {1}".format(match[2], random.choice(names)))

    if 'seduce' in message.content.lower():
        await message.channel.send('Seduce me!', file=File('seduce.png'))

    if message.content.lower() == 'mirage':
        await message.channel.send('now dont get me started on the mirage 2000 hahah its so bad like wtf french the best plane they ever made was a flag blown away by the wind it works great actualy but the mirage is so ugly i dont enven now how it can even fly i know a friend is part of the raf he flew three (yes, 3) mirage and the worst was the deux mille i mean its a flying pankace and really how can a french plane work anyway they dont even now how cars work look at renault its so bad right so yes the mirage is pretty shitty right yeah')
    with open('users.json', 'r') as f:
        users = json.load(f)

    await update_data(users, message.author)
    await add_xp(users, message.author, 7)
    await level_up(users, message.author, message.channel)

    with open('users.json', 'w') as f:
        json.dump(users, f)

    # Do this so we can still use commands
    await client.process_commands(message)


@client.command(description='Query cleverbot.',
                brief='Query cleverbot.')
async def clever(context, *message):
    message = ' '.join(message)

    async with aiohttp.ClientSession() as session:  # Async HTTP request
        raw_response = await session.post('https://cleverbot.io/1.0/ask', json={'user': config.clever_api_user, 'key': config.clever_api_key, 'nick': 'Fin', 'text': message})
        response = await raw_response.text()  # Take only the data
        response = json.loads(response)  # Parse the JSON into a format we can use
        # This is the JSON path for the price data in USD
    if response['status'] == 'success':
        await context.send(response['response'])
    else:
        await context.send('Error accessing cleverbot.')


@client.command(description='Check a user\'s level. This command takes one mention.',
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


@client.command(description='Check a user\'s XP. This command takes one mention.',
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


@client.command(name='8ball',
                description='Answers a yes/no question.',
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
@client.command(description='Roll dice using syntax as explained at https://tinyurl.com/pydice',
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
                         'entering your move. You must enter your move within 5 minutes or the game will time out.',
             brief='Start a game of chess.')
async def new(context):
    """
    New game command group

    :param context: Command context
    :return:
    """
    if context.invoked_subcommand is None:
        await context.send('Invalid new game. Please use the subcommand white or black')


@new.command(description='Starts a game of chess with the bot. To end a game of chess, type \'end\' instead of '
                         'entering your move. You must enter your move within 5 minutes or the game will time out.',
             brief='Start a game of chess as white.')
async def white(context):
    """
    Command to start a new game of chess vs AI as white

    todo:: Allow for selecting different difficulty levels

    :param context: Command context
    :return:
    """
    game_timed_out = False

    user = context.message.author

    chess_game = chessgame.ChessGame()

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
                movestr = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=300)
            except asyncio.TimeoutError:
                end = True
                game_timed_out = True
                break
            if movestr.content.lower() == 'end':
                end = True
                break
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

    if game_timed_out:
        await context.send('Game timed out. Next time please make a move within 5 minutes.')

    date_string = f"{datetime.date.today():%Y.%m.%d}"
    pgn = chess_game.get_pgn('Chess Game', 'Discord', date_string, user.display_name, "Fin Bot")

    embed = Embed(title="Chess Game Results", colour=Colour(0xff00), description="```%s```" % pgn)

    embed.set_author(name="Fin Bot", icon_url="https://tinyurl.com/y8p7a8px")

    embed.add_field(name="Human Player: White", value=context.author.display_name)
    embed.add_field(name="Bot Player: Black", value="Fin Bot")
    embed.add_field(name="Final Score", value=chess_game.result())

    await context.send(embed=embed)

    game_timed_out = False

    chess_game.engine.kill()


@new.command(description='Starts a game of chess with the bot. To end a game of chess, type \'end\' instead of '
                         'entering your move. You must enter your move within 5 minutes or the game will time out.',
             brief='Start a game of chess as white.')
async def black(context):
    """
    Command to start a new game of chess vs AI as black

    todo:: Allow for selecting different difficulty levels

    :param context: Command context
    :return:
    """
    game_timed_out = False

    user = context.message.author

    chess_game = chessgame.ChessGame()

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
                movestr = await client.wait_for('message', check=lambda m: m.author == context.author, timeout=300)
            except asyncio.TimeoutError:
                end = True
                game_timed_out = True
                break
            if movestr.content.lower() == 'end':
                end = True
                break
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

    if game_timed_out:
        await context.send('Game timed out. Next time please make a move within 5 minutes.')

    date_string = f"{datetime.date.today():%Y.%m.%d}"
    pgn = chess_game.get_pgn('Chess Game', 'Discord', date_string, user.display_name, "Fin Bot")

    embed = Embed(title="Chess Game Results", colour=Colour(0xff00), description="```%s```" % pgn)

    embed.set_author(name="Fin Bot", icon_url="https://tinyurl.com/y8p7a8px")

    embed.add_field(name="Human Player: Black", value=context.author.display_name)
    embed.add_field(name="Bot Player: White", value="Fin Bot")
    embed.add_field(name="Final Score", value=chess_game.result())

    await context.send(embed=embed)

    chess_game.engine.kill()

@client.command(description="Start a new initiative tracker session. Initiative tracking uses three commands: 'next', 'add', and 'remove.'\n"
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



print('Starting...')
client.run(config.token)
