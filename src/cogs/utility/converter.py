"""
File conversion utilities - Now with GIF support!
"""
import discord
from discord.ext import commands
from utils.decorators import guild_setting_enabled  # ← ADDED IMPORT
import aiohttp
import io
import sys

class Converter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @guild_setting_enabled("convert")  # ← ADDED DECORATOR
    async def convert(self, ctx, to_format: str = None):
        """Convert attached file to specified format"""

        if not to_format:
            embed = discord.Embed(
                title='🔄 File Converter - Fully Working!',
                description='**Upload a file and specify target format**',
                color=0x00ff00
            )
            embed.add_field(name='🖼️ Images', value='png, jpg, webp, gif', inline=True)
            embed.add_field(name='📊 Data', value='csv ↔ json', inline=True)
            embed.add_field(name='📝 Text', value='txt ↔ md', inline=True)
            embed.add_field(name='📋 Usage', value=f'Attach file + `{ctx.prefix}convert gif`', inline=False)
            embed.add_field(name='✅ Supported', value='• PNG/JPG/WEBP → GIF\n• Any image → PNG/JPG/WEBP\n• CSV ↔ JSON\n• TXT ↔ MD', inline=False)
            await ctx.send(embed=embed)
            return

        if not ctx.message.attachments:
            await ctx.send('❌ Please attach a file!')
            return

        attachment = ctx.message.attachments[0]
        filename = attachment.filename
        file_ext = filename.split('.')[-1].lower()
        to_format = to_format.lower()

        # Check file size (8MB limit)
        if attachment.size > 8 * 1024 * 1024:
            await ctx.send('❌ File too large! Max 8MB.')
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        await ctx.send('❌ Could not download file')
                        return
                    file_data = await resp.read()

            msg = await ctx.send('🔄 Converting...')

            # Image conversions
            if to_format in ['png', 'jpg', 'jpeg', 'webp', 'gif'] and file_ext in ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp']:
                try:
                    from PIL import Image
                    image = Image.open(io.BytesIO(file_data))

                    # Handle different format requirements
                    if to_format in ['jpg', 'jpeg']:
                        if image.mode in ['RGBA', 'LA', 'P']:
                            # Convert to RGB for JPEG
                            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                            if image.mode == 'P':
                                image = image.convert('RGBA')
                            if image.mode == 'RGBA':
                                rgb_image.paste(image, mask=image.split()[-1])
                            else:
                                rgb_image.paste(image)
                            image = rgb_image
                        save_format = 'JPEG'

                    elif to_format == 'png':
                        save_format = 'PNG'

                    elif to_format == 'webp':
                        save_format = 'WEBP'

                    elif to_format == 'gif':
                        # Convert to palette mode for GIF
                        if image.mode != 'P':
                            image = image.convert('P', palette=Image.ADAPTIVE)
                        save_format = 'GIF'

                    output = io.BytesIO()

                    if save_format == 'JPEG':
                        image.save(output, format=save_format, quality=95, optimize=True)
                    elif save_format == 'WEBP':
                        image.save(output, format=save_format, quality=95, optimize=True)
                    elif save_format == 'GIF':
                        image.save(output, format=save_format, optimize=True)
                    else:
                        image.save(output, format=save_format, optimize=True)

                    output.seek(0)

                    new_name = f"{filename.rsplit('.', 1)[0]}.{to_format}"
                    await msg.delete()

                    embed = discord.Embed(title='✅ Conversion Complete!', color=0x00ff00)
                    embed.add_field(name='From', value=f'{file_ext.upper()}', inline=True)
                    embed.add_field(name='To', value=f'{to_format.upper()}', inline=True)
                    embed.add_field(name='Size', value=f'{len(output.getvalue())} bytes', inline=True)

                    await ctx.send(embed=embed, file=discord.File(output, new_name))

                except ImportError:
                    await msg.edit(content='❌ Install Pillow: `pip install Pillow`')
                except Exception as e:
                    await msg.edit(content=f'❌ Image conversion failed: {str(e)[:50]}')

            # Text conversions
            elif file_ext in ['txt', 'md'] and to_format in ['txt', 'md']:
                text = file_data.decode('utf-8')

                if file_ext == 'md' and to_format == 'txt':
                    # Basic markdown to text
                    import re
                    text = re.sub(r'[*_`#]', '', text)
                    text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove links
                    text = re.sub(r'\n+', '\n', text)
                elif file_ext == 'txt' and to_format == 'md':
                    # Add basic markdown formatting
                    lines = text.split('\n')
                    md_lines = []
                    for line in lines:
                        if line.strip() and not line.startswith(' '):
                            md_lines.append(f'## {line}')
                        else:
                            md_lines.append(line)
                    text = '\n'.join(md_lines)

                output = io.BytesIO(text.encode('utf-8'))
                new_name = f"{filename.rsplit('.', 1)[0]}.{to_format}"
                await msg.delete()
                await ctx.send('✅ Text converted!', file=discord.File(output, new_name))

            # Data conversions
            elif file_ext == 'csv' and to_format == 'json':
                import csv, json
                text = file_data.decode('utf-8')
                reader = csv.DictReader(text.strip().split('\n'))
                data = json.dumps(list(reader), indent=2)
                output = io.BytesIO(data.encode())
                new_name = f"{filename.rsplit('.', 1)[0]}.json"
                await msg.delete()
                await ctx.send('✅ CSV → JSON converted!', file=discord.File(output, new_name))

            elif file_ext == 'json' and to_format == 'csv':
                import json, csv, io as text_io
                text = file_data.decode('utf-8')
                data = json.loads(text)

                if isinstance(data, list) and data and isinstance(data[0], dict):
                    string_output = text_io.StringIO()
                    writer = csv.DictWriter(string_output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)

                    output = io.BytesIO(string_output.getvalue().encode())
                    new_name = f"{filename.rsplit('.', 1)[0]}.csv"
                    await msg.delete()
                    await ctx.send('✅ JSON → CSV converted!', file=discord.File(output, new_name))
                else:
                    await msg.edit(content='❌ JSON must be array of objects for CSV')

            else:
                supported = {
                    'png': 'jpg, webp, gif',
                    'jpg': 'png, webp, gif',
                    'jpeg': 'png, webp, gif',
                    'webp': 'png, jpg, gif',
                    'gif': 'png, jpg, webp',
                    'csv': 'json',
                    'json': 'csv',
                    'txt': 'md',
                    'md': 'txt'
                }

                if file_ext in supported:
                    await msg.edit(content=f'❌ Can convert {file_ext.upper()} to: {supported[file_ext]}')
                else:
                    await msg.edit(content=f'❌ {file_ext.upper()} files not supported yet')

        except Exception as e:
            await ctx.send(f'❌ Error: {str(e)[:100]}')

async def setup(bot):
    await bot.add_cog(Converter(bot))