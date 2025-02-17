import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# Конфигурация:
# Замените MY_GUILD_ID на ID вашего сервера, если хотите мгновенную синхронизацию команд.
MY_GUILD_ID = 1139578692159414382  # <-- Замените на ваш ID сервера

# ID каналов логирования:
log_moderation_id = 1149990513026531379  # Бан/Кик/Таймаут/Вход-Выход
log_voice_id = 1149990591476805762  # Войс-события
log_messages_id = 1149990659793633311  # Удаление/Редактирование сообщений
log_nick_role_id = 1149990708254617603  # Смена ников, ролей, реакции

# ID канала приветствия:
WELCOME_CHANNEL_ID = 1139591852119576596

logs_enabled = True  # Флаг логирования
roles_enabled = True  # Флаг автовыдачи ролей

# ID роли для автовыдачи:
AUTO_ROLE_ID = 1139591830405656707

# Хранилище для настроек выдачи ролей по реакции:
role_message_map = {}


# ------------------------------------------------------------------------------
# Вспомогательная функция для отправки Embed-логов
# ------------------------------------------------------------------------------
async def log_embed(channel_id: int, embed: discord.Embed):
    if logs_enabled:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)
        print(f"[LOG] {embed.title}: {embed.description}")


# ------------------------------------------------------------------------------
# Событие: бот запущен
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    # Глобальная синхронизация команд:
    await bot.tree.sync()
    # Если хотите мгновенную синхронизацию для конкретного сервера, раскомментируйте:
    # await bot.tree.sync(guild=discord.Object(id=MY_GUILD_ID))
    await bot.change_presence(status=discord.Status.invisible)
    print(f"Бот {bot.user} запущен и слэш-команды синхронизированы!")


# ------------------------------------------------------------------------------
# Модерационные команды
# ------------------------------------------------------------------------------
@bot.tree.command(name="ban", description="Забанить пользователя на время (в минутах)")
async def ban(interaction: discord.Interaction, user: discord.Member, time: int, reason: str):
    await user.ban(reason=reason)
    embed = discord.Embed(
        title="User Banned",
        description=f"{user.mention} забанен на {time} минут.\n**Причина:** {reason}",
        color=0xFF0000
    )
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    await log_embed(log_moderation_id, embed)

    async def unban_after_delay():
        await asyncio.sleep(time * 60)
        await interaction.guild.unban(user)
        embed_unban = discord.Embed(
            title="User Unbanned",
            description=f"{user.mention} разбанен автоматически.",
            color=0x00FF00
        )
        await log_embed(log_moderation_id, embed_unban)

    asyncio.create_task(unban_after_delay())
    await interaction.response.send_message(f"{user.mention} забанен на {time} минут.")


@bot.tree.command(name="kick", description="Кикнуть пользователя")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str):
    await user.kick(reason=reason)
    embed = discord.Embed(
        title="User Kicked",
        description=f"{user.mention} кикнут.\n**Причина:** {reason}",
        color=0xFF0000
    )
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    await log_embed(log_moderation_id, embed)
    await interaction.response.send_message(f"{user.mention} кикнут.")


@bot.tree.command(name="unban", description="Разбанить пользователя по ID")
async def unban(interaction: discord.Interaction, user_id: int):
    user = await bot.fetch_user(user_id)
    await interaction.guild.unban(user)
    embed = discord.Embed(
        title="User Unbanned",
        description=f"{user.mention} разбанен.",
        color=0x00FF00
    )
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    await log_embed(log_moderation_id, embed)
    await interaction.response.send_message(f"{user.mention} разбанен.")


# ------------------------------------------------------------------------------
# Команды управления логами и автовыдачей ролей
# ------------------------------------------------------------------------------
@bot.tree.command(name="logs", description="Включить/выключить логи (on/off)")
async def logs(interaction: discord.Interaction, input: str):
    global logs_enabled
    logs_enabled = input.lower() == "on"
    status = "включены" if logs_enabled else "выключены"
    await interaction.response.send_message(f"Логи {status}.")


@bot.tree.command(name="autoroles", description="Включить/выключить автовыдачу ролей (on/off)")
async def autoroles(interaction: discord.Interaction, input: str):
    global roles_enabled
    roles_enabled = input.lower() == "on"
    status = "включена" if roles_enabled else "выключена"
    await interaction.response.send_message(f"Автовыдача ролей {status}.")


# ------------------------------------------------------------------------------
# Команда для настройки выдачи ролей по реакции (использует ID ролей)
# ------------------------------------------------------------------------------
@bot.tree.command(name="roles", description="Создать сообщение для выдачи ролей по реакциям")
async def roles_cmd(interaction: discord.Interaction, message_id: str, roles: str, emoji: str):
    """
    Пример использования:
    /roles message_id:1341190070908092418 roles:1311608369324490793,123456789012345678 emoji:👍
    В данном примере бот свяжет сообщение с ID 1341190070908092418 с выдачей ролей по реакциям,
    где роли задаются их ID (разделены запятыми) и эмодзи — 👍.
    """
    channel = interaction.channel
    try:
        # Преобразуем message_id в int
        msg_id = int(message_id)
        message = await channel.fetch_message(msg_id)
        # Теперь обрабатываем роли как список ID
        role_list = []
        for role_id in roles.split(","):
            role_id = role_id.strip()
            try:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    role_list.append(role)
            except Exception as e:
                continue
        if not role_list:
            await interaction.response.send_message(
                "Ни одна из указанных ролей не найдена. Убедитесь, что вы ввели корректные ID ролей.")
            return
        role_message_map[message.id] = {emoji: role_list}
        await message.add_reaction(emoji)
        embed = discord.Embed(
            title="Reaction Roles Setup",
            description=(
                f"Настроена выдача ролей по реакции {emoji}.\n"
                f"Роли: {', '.join(r.mention for r in role_list)}\n\n"
                f"Сообщение: [Jump to message]({message.jump_url})"
            ),
            color=0x2F3136
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Ошибка: {e}")


# ------------------------------------------------------------------------------
# Новая команда /clear для очистки сообщений
# ------------------------------------------------------------------------------
@bot.tree.command(name="clear", description="Удаляет указанное количество сообщений в канале")
async def clear(interaction: discord.Interaction, number_of_messages: int):
    try:
        deleted = await interaction.channel.purge(limit=number_of_messages)
        await interaction.response.send_message(f"Удалено сообщений: {len(deleted)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Ошибка при удалении сообщений: {e}", ephemeral=True)


# ------------------------------------------------------------------------------
# События сервера: вход, выход, приветствие, войс, сообщения, ники, роли
# ------------------------------------------------------------------------------
@bot.event
async def on_member_join(member):
    # Приветственное сообщение:
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(
            f"Добро пожаловать, {member.mention}!\n"
            "Напиши свой никнейм и ожидай выдачи роли :)"
        )
    embed = discord.Embed(
        title="Member Joined",
        description=f"{member.mention} вошел на сервер.",
        color=0x2ECC71
    )
    await log_embed(log_moderation_id, embed)
    if roles_enabled:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            await member.add_roles(role)
            embed_role = discord.Embed(
                title="Auto Role Assigned",
                description=f"Роль {role.mention} выдана {member.mention}.",
                color=0x2ECC71
            )
            await log_embed(log_nick_role_id, embed_role)


@bot.event
async def on_member_remove(member):
    embed = discord.Embed(
        title="Member Left",
        description=f"{member.mention} покинул сервер.",
        color=0x3498DB
    )
    await log_embed(log_moderation_id, embed)


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if after.channel and not before.channel:
            embed = discord.Embed(
                title="Voice Channel Joined",
                description=f"{member.mention} зашел в {after.channel.name}.",
                color=0x5865F2
            )
            await log_embed(log_voice_id, embed)
        elif before.channel and not after.channel:
            embed = discord.Embed(
                title="Voice Channel Left",
                description=f"{member.mention} вышел из {before.channel.name}.",
                color=0x5865F2
            )
            await log_embed(log_voice_id, embed)
        else:
            embed = discord.Embed(
                title="Voice Channel Switched",
                description=f"{member.mention} перешел из {before.channel.name} в {after.channel.name}.",
                color=0x5865F2
            )
            await log_embed(log_voice_id, embed)
    if before.mute != after.mute:
        embed = discord.Embed(
            title="Voice Mute Updated",
            description=f"{member.mention} теперь {'замучен' if after.mute else 'размучен'}.",
            color=0x5865F2
        )
        await log_embed(log_voice_id, embed)
    if before.deaf != after.deaf:
        embed = discord.Embed(
            title="Voice Deaf Updated",
            description=f"{member.mention} теперь {'заглушен' if after.deaf else 'разглушен'}.",
            color=0x5865F2
        )
        await log_embed(log_voice_id, embed)


@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    embed = discord.Embed(
        title="Message Deleted",
        color=0xED4245
    )
    embed.add_field(name="Author", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Content", value=message.content or "Пусто", inline=False)
    await log_embed(log_messages_id, embed)


@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if before.content != after.content:
        embed = discord.Embed(
            title="Message Edited",
            color=0xFEE75C
        )
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Old", value=before.content or "Пусто", inline=False)
        embed.add_field(name="New", value=after.content or "Пусто", inline=False)
        await log_embed(log_messages_id, embed)


@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        embed = discord.Embed(
            title="Nickname Changed",
            color=0xF1C40F
        )
        embed.add_field(name="User", value=before.mention, inline=True)
        embed.add_field(name="Old Nickname", value=before.nick or "Нет", inline=False)
        embed.add_field(name="New Nickname", value=after.nick or "Нет", inline=False)
        await log_embed(log_nick_role_id, embed)
    if before.roles != after.roles:
        old_roles = set(before.roles)
        new_roles = set(after.roles)
        added = new_roles - old_roles
        removed = old_roles - new_roles
        if added or removed:
            desc = []
            if added:
                desc.append(f"**Добавлены роли:** {', '.join(r.mention for r in added)}")
            if removed:
                desc.append(f"**Убраны роли:** {', '.join(r.mention for r in removed)}")
            embed = discord.Embed(
                title="Roles Updated",
                description="\n".join(desc),
                color=0xF1C40F
            )
            embed.add_field(name="User", value=before.mention, inline=True)
            await log_embed(log_nick_role_id, embed)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id in role_message_map:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            roles_for_emoji = role_message_map[payload.message_id].get(str(payload.emoji), [])
            for role in roles_for_emoji:
                await member.add_roles(role)
            if roles_for_emoji:
                embed = discord.Embed(
                    title="Role Granted by Reaction",
                    description=(
                        f"{member.mention} получил роль(и): {', '.join(r.mention for r in roles_for_emoji)}\n"
                        f"Реакция: {payload.emoji}"
                    ),
                    color=0x2ECC71
                )
                await log_embed(log_nick_role_id, embed)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id in role_message_map:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            roles_for_emoji = role_message_map[payload.message_id].get(str(payload.emoji), [])
            for role in roles_for_emoji:
                await member.remove_roles(role)
            if roles_for_emoji:
                embed = discord.Embed(
                    title="Role Removed by Reaction",
                    description=(
                        f"{member.mention} потерял роль(и): {', '.join(r.mention for r in roles_for_emoji)}\n"
                        f"Реакция: {payload.emoji}"
                    ),
                    color=0xED4245
                )
                await log_embed(log_nick_role_id, embed)


bot.run("MTM0MTE4NDY4MjkwNTMwOTI5NQ.GKGLp6.FsO1-niUEGZmODLZOtTg02t_qPJ-_yOTGCFDII")
