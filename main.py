import json
import logging
from twitchio.ext import commands
from database import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

class TwitchBot(commands.Bot):
    def __init__(self):
        self.config = config

        super().__init__(
            token=self.config['twitch']['oauth_token'],
            client_id=self.config['twitch']['client_id'],
            nick=self.config['twitch']['channel'],  # Используем имя канала как ник
            prefix='!',
            initial_channels=[self.config['twitch']['channel']]
        )
        
        self.db = Database()
        self.current_giveaway = None
    
    async def event_ready(self):
        await self.db.init_db()
        logger.info(f'Bot готов | {self.nick}')
    
    async def event_message(self, message):
        """Обрабатываем сообщения в чате"""
        # Пропускаем сообщения от ботов
        if message.echo:
            return
        
        # Обрабатываем команды
        await self.handle_commands(message)

    @commands.command(
        name=config['commands']['giveaway_start'])
    async def start_giveaway(self, ctx, key_name: str = None):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not key_name:
            await ctx.send(f"Использование: !{config['commands']['giveaway_start']} <ключ>")
            return
        
        if self.current_giveaway:
            await ctx.send(f"Уже активен розыгрыш '{self.current_giveaway}'. Завершите его командой !{config['commands']['giveaway_end']}")
            return
        
        self.current_giveaway = key_name
        # await self.db.clear_giveaway(key_name)
        await ctx.send(f"🎉 Розыгрыш '{key_name}' начался! Участвуйте командой !{config['commands']['giveaway_join']}")
    
    @commands.command(
        name=config['commands']['giveaway_end'])
    async def end_giveaway(self, ctx):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not self.current_giveaway:
            await ctx.send("Нет активного розыгрыша")
            return
        
        count = await self.db.get_participants_count(self.current_giveaway)
        ended_giveaway = self.current_giveaway
        self.current_giveaway = None
        await ctx.send(f"📝 Прием заявок в '{ended_giveaway}' завершен! Участников: {count}")
    
    @commands.command(
        name=config['commands']['giveaway_join'])
    async def join_giveaway(self, ctx):
        if not self.current_giveaway:
            await ctx.send("Нет активного розыгрыша")
            return
        
        if await self.db.add_to_giveaway(self.current_giveaway, str(ctx.author.id), ctx.author.name):
            await ctx.send(f"@{ctx.author.name}, вы участвуете в розыгрыше '{self.current_giveaway}'!")
        else:
            await ctx.send(f"@{ctx.author.name}, вы уже участвуете в розыгрыше '{self.current_giveaway}'")
    
    @commands.command(
        name=config['commands']['pick_winner'])
    async def pick_winner(self, ctx, key_name: str = None):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not key_name:
            await ctx.send(f"Использование: !{config['commands']['pick_winner']} <ключ>")
            return
        
        winner = await self.db.pick_random_winner(key_name)
        if winner:
            user_id, username = winner
            await ctx.send(f"🏆 Победитель розыгрыша '{key_name}': @{username}!")
        else:
            await ctx.send(f"Нет участников в розыгрыше '{key_name}'")
    
    @commands.command(
        name=config['commands']['participants'])
    async def show_participants(self, ctx, key_name: str = None):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not key_name:
            if not self.current_giveaway:
                await ctx.send(f"Нет активного розыгрыша. Использование: !{config['commands']['participants']} <ключ>")
                return
            key_name = self.current_giveaway
        
        count = await self.db.get_participants_count(key_name)
        await ctx.send(f"Участников в розыгрыше '{key_name}': {count}")
    
    @commands.command(
        name=config['commands']['current_giveaway'])
    async def current_giveaway_info(self, ctx):
        if self.current_giveaway:
            count = await self.db.get_participants_count(self.current_giveaway)
            await ctx.send(f"Активный розыгрыш: '{self.current_giveaway}' (участников: {count})")
        else:
            await ctx.send("Нет активного розыгрыша")

if __name__ == '__main__':
    bot = TwitchBot()
    bot.run()