import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إعدادات البوت
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

# تعطيل ميزات الصوت
discord.VoiceClient = None

bot = commands.Bot(command_prefix='!', intents=intents)

# إنشاء ملف products.json إذا لم يكن موجوداً
if not os.path.exists('products.json'):
    with open('products.json', 'w') as f:
        json.dump({}, f)

# تخزين المنتجات في قاموس
products = {}

# معرف نظام الكريديت بروبوت للتحويل له
TRANSFER_ID = None

# معرف البروبوت الحقيقي لمراقبة الرسائل
PROBOT_ID = 282859044593598464

# تخزين عمليات الشراء الجارية
ongoing_purchases = {}

@bot.event
async def on_ready():
    print(f'البوت جاهز! تم تسجيل الدخول باسم {bot.user.name}')
    # تحميل المنتجات من الملف إذا كان موجوداً
    if os.path.exists('products.json'):
        with open('products.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            products.update(data.get('products', {}))
            global TRANSFER_ID
            TRANSFER_ID = data.get('transfer_id')

def save_products():
    with open('products.json', 'w', encoding='utf-8') as f:
        data = {
            'products': products,
            'transfer_id': TRANSFER_ID
        }
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.command()
@commands.has_permissions(administrator=True)
async def addproduct(ctx, name: str, price: int, quantity: int, details: str, transfer_id: int):
    """إضافة منتج جديد للمخزون"""
    try:
        global TRANSFER_ID
        
        # التحقق من صحة المدخلات
        if quantity <= 0:
            await ctx.send("❌ يجب أن يكون العدد أكبر من صفر.")
            return
            
        if price <= 0:
            await ctx.send("❌ يجب أن يكون السعر أكبر من صفر.")
            return
        
        # حساب العمولة
        fee = (price * 5) // 100
        amount_after_fee = price - fee
        
        # إضافة المنتج للمخزون
        products[name.lower()] = {
            'price': price,
            'name': name,
            'quantity': quantity,
            'details': details.strip('"'),  # إزالة علامات التنصيص
            'fee': fee,
            'amount_after_fee': amount_after_fee
        }
        TRANSFER_ID = transfer_id
        save_products()
        
        # رسالة التأكيد
        await ctx.send(f'✅ تم إضافة المنتج "{name}" بنجاح!\n'
                      f'💰 السعر: {price} كريديت\n'
                      f'📦 الكمية: {quantity} قطعة\n'
                      f'💸 العمولة: {fee} كريديت\n'
                      f'💵 المبلغ بعد العمولة: {amount_after_fee} كريديت')
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command()
async def stock(ctx):
    """عرض جميع المنتجات المتوفرة"""
    if not products:
        await ctx.send('لا توجد منتجات متوفرة في المخزون.')
        return
    
    embed = discord.Embed(title='📦 المنتجات المتوفرة', color=discord.Color.blue())
    
    for name, product in products.items():
        # حساب العمولة والمبلغ بعد العمولة إذا لم تكن موجودة
        if 'fee' not in product:
            fee = (product['price'] * 5) // 100
            amount_after_fee = product['price'] - fee
            product['fee'] = fee
            product['amount_after_fee'] = amount_after_fee
            save_products()  # حفظ التحديثات
        
        embed.add_field(
            name=product['name'],
            value=f'💰 السعر: {product["price"]} كريديت\n'
                  f'📦 الكمية: {product["quantity"]} قطعة\n'
                  f'💸 العمولة: {product["fee"]} كريديت\n'
                  f'💵 المبلغ بعد العمولة: {product["amount_after_fee"]} كريديت',
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, product_name):
    """شراء منتج من المتجر"""
    if product_name not in products:
        await ctx.send('هذا المنتج غير موجود في المتجر.')
        return
    
    product = products[product_name]
    if product['quantity'] <= 0:
        await ctx.send('عذراً، هذا المنتج غير متوفر حالياً.')
        return
    
    # حساب العمولة والمبلغ النهائي
    fee = (product['price'] * 5) // 100
    amount_after_fee = product['price'] - fee
    
    # إرسال تفاصيل المنتج في نفس الروم
    embed = discord.Embed(title=f'📦 تفاصيل المنتج "{product_name}"', color=discord.Color.blue())
    embed.add_field(name='💰 السعر:', value=f'{product["price"]} كريديت', inline=False)
    embed.add_field(name='✂️ العمولة:', value=f'{fee} كريديت', inline=False)
    embed.add_field(name='💵 المبلغ بعد العمولة:', value=f'{amount_after_fee} كريديت', inline=False)
    embed.add_field(name='📝 التفاصيل:', value=f'{product["details"]}', inline=False)
    
    # إضافة أمر التحويل للبروبوت
    transfer_command = f'c {TRANSFER_ID} {product["price"]}'
    embed.add_field(name='🔄 أمر التحويل:', value=f'`{transfer_command}`', inline=False)
    embed.add_field(name='📢 للشراء:', value=f'قم بتنفيذ أمر التحويل أعلاه', inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def send(ctx, member: discord.Member, product_name: str):
    """إرسال المنتج للمشتري (للأدمن فقط)"""
    try:
        product_name = product_name.lower()
        if product_name not in products:
            await ctx.send('❌ المنتج غير موجود!')
            return
        
        product = products[product_name]
        if product['quantity'] <= 0:
            await ctx.send('❌ عذراً، هذا المنتج غير متوفر حالياً.')
            return
        
        # تحديث الكمية
        product['quantity'] -= 1
        save_products()
        
        # إرسال تفاصيل المنتج للمشتري في الخاص
        try:
            await member.send(f'✅ مبروك! تم شراء المنتج "{product["name"]}" بنجاح!\n\n'
                            f'📝 تفاصيل المنتج:\n{product["details"]}')
            
            # إرسال تأكيد في الروم
            await ctx.send(f'✅ تم إرسال المنتج "{product["name"]}" إلى {member.mention} بنجاح!')
        except discord.Forbidden:
            await ctx.send(f'❌ لا يمكنني إرسال رسالة خاصة إلى {member.mention}. الرجاء فتح الرسائل الخاصة.')
            
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.event
async def on_message(message):
    # تجاهل الرسائل من البوت نفسه
    if message.author == bot.user:
        return
        
    # معالجة الأوامر
    await bot.process_commands(message)
    
    # التحقق من رسائل البروبوت للتحويل
    if message.author.id == PROBOT_ID and "قام بتحويل" in message.content:
        print(f"تم اكتشاف رسالة تحويل: {message.content}")  # للتشخيص
        
        try:
            # البحث عن آخر عملية شراء في نفس الروم
            async for msg in message.channel.history(limit=5):
                if msg.author == bot.user and msg.embeds:
                    embed = msg.embeds[0]
                    if "تفاصيل المنتج" in embed.title:
                        product_name = embed.title.split('"')[1]  # استخراج اسم المنتج
                        print(f"تم العثور على المنتج: {product_name}")  # للتشخيص
                        
                        if product_name in products:
                            product = products[product_name]
                            
                            # تحديث الكمية
                            product['quantity'] -= 1
                            save_products()
                            
                            # البحث عن المشتري (آخر شخص استخدم أمر !buy)
                            async for buy_msg in message.channel.history(limit=10):
                                if buy_msg.content.lower().startswith('!buy') and buy_msg.content.lower().endswith(product_name.lower()):
                                    buyer = buy_msg.author
                                    try:
                                        # إرسال تفاصيل المنتج في الخاص
                                        await buyer.send(f'تم شراء "{product["name"]}" بنجاح 🎉\n\n'
                                                     f'{product["details"]}')
                                        # إرسال تأكيد في الروم
                                        await message.channel.send(f'تم شراء "{product["name"]}" بنجاح 🎉')
                                        print(f"تم إرسال التفاصيل إلى {buyer.name}")  # للتشخيص
                                    except discord.Forbidden:
                                        await message.channel.send(f'❌ لا يمكنني إرسال رسالة خاصة إلى {buyer.mention}. الرجاء فتح الرسائل الخاصة.')
                                        print(f"خطأ في إرسال الرسالة الخاصة إلى {buyer.name}")  # للتشخيص
                                    break
                        break
        except Exception as e:
            print(f"حدث خطأ: {str(e)}")  # للتشخيص

# تشغيل البوت
bot.run(os.getenv('DISCORD_TOKEN')) 