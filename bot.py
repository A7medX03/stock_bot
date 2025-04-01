import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store products in a dictionary
products = {}

# ProBot credit system ID
PROBOT_ID = 1156299517428248596

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name}')
    # Load products from file if exists
    if os.path.exists('products.json'):
        with open('products.json', 'r') as f:
            products.update(json.load(f))

def save_products():
    with open('products.json', 'w') as f:
        json.dump(products, f)

@bot.command()
@commands.has_permissions(administrator=True)
async def addproduct(ctx, name: str, price: int):
    """Add a new product to the stock"""
    products[name.lower()] = {
        'price': price,
        'name': name
    }
    save_products()
    await ctx.send(f'✅ Product "{name}" added with price {price} credits!')

@bot.command()
async def stock(ctx):
    """Display all available products"""
    if not products:
        await ctx.send('No products available in stock.')
        return
    
    embed = discord.Embed(title='📦 Available Products', color=discord.Color.blue())
    for product in products.values():
        embed.add_field(name=product['name'], value=f'Price: {product["price"]} credits', inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, product_name: str):
    """Buy a product"""
    product_name = product_name.lower()
    
    if product_name not in products:
        await ctx.send('❌ Product not found! Use !stock to see available products.')
        return
    
    product = products[product_name]
    price = product['price']
    
    # Create ProBot credit transfer command
    transfer_command = f'!transfer {PROBOT_ID} {price}'
    
    embed = discord.Embed(
        title='🛍️ Purchase Instructions',
        description=f'To purchase {product["name"]} for {price} credits:',
        color=discord.Color.green()
    )
    embed.add_field(name='Step 1', value=f'Use this command to transfer credits:\n`{transfer_command}`', inline=False)
    embed.add_field(name='Step 2', value='After successful transfer, the product will be sent to your DMs.', inline=False)
    
    await ctx.send(embed=embed)
    
    # Wait for credit transfer
    def check(m):
        return m.author.id == PROBOT_ID and m.channel.id == ctx.channel.id and 'transfer' in m.content.lower()
    
    try:
        await bot.wait_for('message', timeout=300.0, check=check)
        # If transfer successful, send product to user's DM
        try:
            await ctx.author.send(f'🎉 Congratulations! Here is your purchase:\n**{product["name"]}**')
        except discord.Forbidden:
            await ctx.send('❌ I couldn\'t send you a DM. Please enable DMs from server members.')
    except TimeoutError:
        await ctx.send('❌ Purchase timed out. Please try again.')

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 