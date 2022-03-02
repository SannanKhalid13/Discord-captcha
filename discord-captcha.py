import discord
from captcha.image import ImageCaptcha
import numpy as np
from PIL import Image
import random
import os
from discord.ext import commands
from discord.utils import get
import sqlite3
import string


TOKEN = ''
client = discord.Client()
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
conn = sqlite3.connect('records.db')

conn.execute("CREATE TABLE IF NOT EXISTS verification (user TEXT, user_id TEXT,code TEXT, status INT)")
conn.commit()
conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_user ON verification (user_id)")
conn.commit()

@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))

@bot.event
async def on_member_join(member):

    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = False
    overwrite.send_messages = True
    for channel in member.guild.text_channels:
        if channel.name !="verify-yourself": #make a seperate channel for verification
            await channel.set_permissions(member, overwrite=overwrite)
    Roler="Notverified" #assign a role to the user before verification. This role won't have access to any other channels
    role = get(member.guild.roles, name=Roler)
    
    #enter the user in the database with status 0
    conn.execute("INSERT INTO verification VALUES (?,?,?,?)",(member.name,member.id,None,0))
    conn.commit()
    #create 
    await member.add_roles(role)

@bot.event
async def on_member_remove(member):

    conn.execute("DELETE FROM verification WHERE user_id=?",(member.id,))
    conn.commit()
   

def generate_captcha(author_id):
    
    captcha_text = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    WIDTH=200
    HEIGHT=120
    image = ImageCaptcha(width=WIDTH, height=HEIGHT, font_sizes=[40])
    conn.execute("UPDATE verification SET code=? WHERE user_id=?",(captcha_text,author_id))
    conn.commit()
    captcha= image.generate(captcha_text)
    captcha_image = Image.open(captcha)
    captcha_image = np.array(captcha_image)
    image.write(captcha_text, captcha_text + '.png') 
   
    return captcha_text


@bot.command()
async def verify(ctx):

    conn=sqlite3.connect('records.db')
    cursor=conn.execute("SELECT * FROM verification WHERE user_id=?",(ctx.author.id,))

    for row in cursor:
        check=row[3]

    if check==1:
        await ctx.send("You have already verified your account. You can now use the commands in the server.")

    else:
        if isinstance(ctx.channel, discord.channel.DMChannel):
            pass

        else:
            while True:
                png_names=generate_captcha(ctx.author.id)
                await ctx.message.author.send('Enter the Captcha to verify yourself ', file=discord.File(png_names+'.png', 'test.png'))
                os.remove(png_names+'.png') #remove png file after it is sent to the user
                msg=await bot.wait_for('message', check=lambda message: message.author == ctx.author and not message.guild)
                conn=sqlite3.connect('records.db')
                cursor=conn.execute("SELECT * FROM verification WHERE user_id=?",(ctx.author.id,))

                for row in cursor:
                    match_code=row[2]

                if msg.author==bot.user:
                      return

                elif msg.content==match_code and isinstance(msg.channel, discord.channel.DMChannel):
                     
                     guilds=bot.get_guild(ctx.guild.id)
                     member=await guilds.fetch_member(ctx.author.id)
                     Roler="verified_role"
                     role = get(member.guild.roles, name=Roler)
                     await member.add_roles(role)
                     Roler="Notverified"
                     role = get(member.guild.roles, name=Roler)
                     await member.remove_roles(role) 

                     for channel in ctx.author.guild.text_channels:
                        await channel.set_permissions(ctx.author, overwrite=None)     
                        overwrite = discord.PermissionOverwrite()
                        overwrite.send_messages = True
                        overwrite.read_messages = True

                     for channel in ctx.author.guild.text_channels:    
                        if channel.name =="verify-yourself":

                            await channel.set_permissions(ctx.author, overwrite=overwrite)
                
                     await ctx.author.send('You are now verified')
                     #update status in the database to 1
                     conn.execute("UPDATE verification SET status=? WHERE user_id=?",(1,ctx.author.id))
                     conn.commit()
                     
                     return

                elif msg.content!=match_code and isinstance(msg.channel, discord.channel.DMChannel):
                    await ctx.message.author.send('Sorry try again wrong captcha')


bot.run(TOKEN)