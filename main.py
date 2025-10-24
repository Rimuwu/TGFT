import json
import asyncio
from twitchio.ext import commands
from database import Database

class TwitchBot(commands.Bot):
    def __init__(self):
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        super().__init__(
            token=self.config['twitch']['oauth_token'],
            client_id=self.config['twitch']['client_id'],
            nick='bot',
            prefix='!',
            initial_channels=[self.config['twitch']['channel']]
        )
        
        self.db = Database()
        self.current_giveaway = None
        self.user_tracking_task = None
    
    async def event_ready(self):
        await self.db.init_db()
        print(f'Bot готов | {self.nick}')
        self.user_tracking_task = asyncio.create_task(self.track_users())
    
    async def track_users(self):
        while True:
            try:
                channel = self.get_channel(self.config['twitch']['channel'])
                if channel:
                    chatters = await channel.chatters()
                    for chatter in chatters.all:
                        await self.db.update_user_time(str(chatter.id), chatter.name)
                await asyncio.sleep(60)
            except Exception as e:
                print(f'Ошибка отслеживания: {e}')
                await asyncio.sleep(60)

    @commands.command(name='newstream')
    async def new_stream(self, ctx):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        await self.db.start_new_stream()
        await ctx.send("🔴 Новый стрим начался! Время просмотра сброшено")

    @commands.command(name='giveaway')
    async def start_giveaway(self, ctx, key_name: str = None):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not key_name:
            await ctx.send("Использование: !giveaway <ключ>")
            return
        
        if self.current_giveaway:
            await ctx.send(f"Уже активен розыгрыш '{self.current_giveaway}'. Завершите его командой !endgiveaway")
            return
        
        self.current_giveaway = key_name
        await self.db.clear_giveaway(key_name)
        await ctx.send(f"🎉 Розыгрыш '{key_name}' начался! Участвуйте командой {self.config['commands']['giveaway_join']}")
    
    @commands.command(name='endgiveaway')
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
    
    @commands.command(name='join')
    async def join_giveaway(self, ctx):
        if not self.current_giveaway:
            await ctx.send("Нет активного розыгрыша")
            return
        
        user_time = await self.db.get_user_watch_time(str(ctx.author.id))
        min_time = self.config['giveaway']['min_watch_time_minutes']
        
        if user_time < min_time:
            await ctx.send(f"@{ctx.author.name}, недостаточно времени просмотра. Нужно: {min_time} мин, у вас: {user_time} мин")
            return
        
        if await self.db.add_to_giveaway(self.current_giveaway, str(ctx.author.id), ctx.author.name):
            await ctx.send(f"@{ctx.author.name}, вы участвуете в розыгрыше '{self.current_giveaway}'!")
        else:
            await ctx.send(f"@{ctx.author.name}, вы уже участвуете в розыгрыше '{self.current_giveaway}'")
    
    @commands.command(name='pick')
    async def pick_winner(self, ctx, key_name: str = None):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not key_name:
            await ctx.send("Использование: !pick <ключ>")
            return
        
        winner = await self.db.pick_random_winner(key_name)
        if winner:
            user_id, username = winner
            await ctx.send(f"🏆 Победитель розыгрыша '{key_name}': @{username}!")
        else:
            await ctx.send(f"Нет участников в розыгрыше '{key_name}'")
    
    @commands.command(name='time')
    async def check_time(self, ctx):
        user_time = await self.db.get_user_watch_time(str(ctx.author.id))
        await ctx.send(f"@{ctx.author.name}, время просмотра этого стрима: {user_time} минут")
    
    @commands.command(name='participants')
    async def show_participants(self, ctx, key_name: str = None):
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        
        if not key_name:
            if not self.current_giveaway:
                await ctx.send("Нет активного розыгрыша. Использование: !participants <ключ>")
                return
            key_name = self.current_giveaway
        
        count = await self.db.get_participants_count(key_name)
        await ctx.send(f"Участников в розыгрыше '{key_name}': {count}")
    
    @commands.command(name='current')
    async def current_giveaway(self, ctx):
        if self.current_giveaway:
            count = await self.db.get_participants_count(self.current_giveaway)
            await ctx.send(f"Активный розыгрыш: '{self.current_giveaway}' (участников: {count})")
        else:
            await ctx.send("Нет активного розыгрыша")

if __name__ == '__main__':
    bot = TwitchBot()
    bot.run()