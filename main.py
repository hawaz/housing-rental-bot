from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup,InputMediaPhoto,BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    CallbackContext,
    ChatMemberHandler,
    MessageHandler,
    ConversationHandler,
    filters
    
)
import requests
import os
from dotenv import load_dotenv

# Safe key map for region and city names
REGION_MAP = {
    "addis": "አዲስ አበባ",
    "tigray": "ትግራይ",
    "amhara": "አማራ"
}

CITY_MAP = {
    "bole": "ቦለ",
    "kazanchis": "ካዛንቺስ",
    "cmc": "ሲ.ኤም.ሲ",
    "mekelle": "መቀሌ",
    "adigrat": "አዲግራት",
    "shire": "ሺሬ",
    "bahirdar": "ባህር ዳር",
    "gondar": "ጎንደር",
    "dese": "ደሴ"
}

REGIONS = {
    "addis": ["bole", "kazanchis", "cmc"],
    "tigray": ["mekelle", "adigrat", "shire"],
    "amhara": ["bahirdar", "gondar", "dese"]
}

# State constants for ConversationHandler
TITLE, PRICE, BEDROOMS, REGION, CITY, DESCRIPTION, IMAGES, CONTACT = range(8)
# Add new constant states for rental owner menu
RENTAL_MENU, SHOW_LISTINGS, HANDLE_ACTION = range(100, 103)
UPDATE_FIELD, UPDATE_VALUE = range(200, 202)


load_dotenv()

API_URI=os.getenv("API_URL")

SEARCH_URL = API_URI+ "/listings/search"
LISTINGS_URL = API_URI+ "/listings"

USERS_URL = API_URI+ "/users"


BOT_TOKEN = os.getenv("BOT_TOKEN")
print("API_URI:", API_URI)
# -------------------------------------------------------------------------------------------
# Search Functionality
# -------------------------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = {
        "telegram_id": user.id,
        "full_name": user.full_name,
        "username": user.username
    }

    try:
        response = requests.post(USERS_URL, json=user_data)
        if response.status_code == 201:
            print("✅ User registered successfully.")
        elif response.status_code == 409:
            print("ℹ️ User already exists.")
        else:
            print("⚠️ Registration failed.")
    except Exception as e:
        print(f"❌ Error registering user: {e}")

    keyboard = [
        [InlineKeyboardButton("🔍 የኪራይ ቤት ይፈልጉ", callback_data="search")],
        [InlineKeyboardButton("🏠 አከራይ / ወኪል", callback_data="rental_menu")]
    ]
    await update.message.reply_text("እንኳን ደህና መጡ!", reply_markup=InlineKeyboardMarkup(keyboard))


async def choose_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(REGION_MAP[rid], callback_data=f"region:{rid}")] for rid in REGIONS]
    await query.edit_message_text("ክልል ይምረጡ:", reply_markup=InlineKeyboardMarkup(keyboard))

async def region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    region_id = query.data.split(":")[1]
    context.user_data['region_id'] = region_id

    cities = REGIONS.get(region_id, [])
    keyboard = [[InlineKeyboardButton(CITY_MAP[cid], callback_data=f"city:{cid}")] for cid in cities]
    await query.edit_message_text(f"{REGION_MAP[region_id]} ከተማ ይምረጡ:", reply_markup=InlineKeyboardMarkup(keyboard))

async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    city_id = query.data.split(":")[1]
    context.user_data['city_id'] = city_id

    keyboard = [[InlineKeyboardButton(f"{i} መኝታ ቤት", callback_data=f"bed:{i}")] for i in range(1, 6)]
    await query.edit_message_text(f"{CITY_MAP[city_id]} የመኝታ ቤት ቁጥር ይምረጡ:", reply_markup=InlineKeyboardMarkup(keyboard))

async def bed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bedrooms = query.data.split(":")[1]
    region_id = context.user_data.get('region_id')
    city_id = context.user_data.get('city_id')

    try:
        res = requests.get(SEARCH_URL, params={
            "region": REGION_MAP[region_id],
            "city": CITY_MAP[city_id],
            "bedrooms": bedrooms
        })
       
        listings = res.json()

        if not listings:
            await query.edit_message_text(
                f"⚠️ በ {REGION_MAP[region_id]} - {CITY_MAP[city_id]} ውስጥ {bedrooms} መኝታ ቤት አልተገኙም።"
            )
        else:
            for l in listings:
                # Split and clean the image URLs
                image_list = l.get("image_urls", "").split(",")
                image_list = [url.strip() for url in image_list if url.strip()]
             
                # Construct the message
                caption = (
                    f" 🏠 *{l['title']}*\n"
                    f" 📍{l['region']} - {l['city']} \n"
                    f" ☎️ {l['contact']} \n"
                    f" 🛏 {l['bedrooms']} መኝታ \n"           
                    f" 💵 {l['price']} ብር/ወር \n"
                    
                    f" 📝 {l.get('description', '')}\n"
                    

                )
                
                # Send photo if available
                if image_list:
                   
                    try:
                       
                        media_group = []
                        media_group.append(InputMediaPhoto(media=image_list[0], caption=caption, parse_mode="Markdown"))

                        for url in image_list[1:]:
                            media_group.append(InputMediaPhoto(media=url))

                        await context.bot.send_media_group(
                            chat_id=update.effective_chat.id,
                            media=media_group
                        )
                    except Exception as e:
                        print("❌ Failed to send media group:", e)
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=caption + "\n⚠️ ምስሎች መላክ አልተቻለም።",
                            parse_mode="Markdown"
                        )


                else:
                    await query.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        text=caption,
                        parse_mode="Markdown"
                    )

    except Exception as e:
        await query.edit_message_text(f"⚠️ በእርስዎ መስፈርት መሰረት የኪራይ ቤት ማግኘት አልቻልንም።{e}\n")

async def search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await choose_region(update, context)

# -------------------------------------------------------------------------------------------
# Add new Functionality
# -------------------------------------------------------------------------------------------



async def post_city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    city_key = query.data.split(":")[1]
    context.user_data['city'] = CITY_MAP[city_key]
    await query.message.reply_text("📝 ስለ ቤቱ ዝርዝር መግለጫን ያስገቡ፥ (ምሳሌ፡ ባለ 2 መኝታ ክፍል፣ ምግብ ማብሰያ ቤት፣ መታጠቢያ እና ሳሎን አለው። ውሃ እና ኤሌክትሪክ የተሟላ።ጸጥታ ያለው አካባቢ ።ዋና መንገድ አቅራቢያ...)")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    context.user_data['image_urls'] = []
    await update.message.reply_text("🖼 ምስል ያስገቡ። ሁሉንም ከላኩ በኋላ '1' ይጻፉ:")
    return IMAGES

async def get_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'image_urls' not in context.user_data:
        context.user_data['image_urls'] = []

    count = len(context.user_data['image_urls'])
    if update.message.photo:
        if len(context.user_data['image_urls']) >= 4:
            await update.message.reply_text("⚠️ 4 ምስሎችን ብቻ ነው ማስገባት ሚፈቀደዉ።")
        else:
            file_id = update.message.photo[-1].file_id
            context.user_data['image_urls'].append(file_id)
            count = len(context.user_data['image_urls'])
            await update.message.reply_text(f"✅ {count}ኛው ምስል በተሳካ ሁኔታ ተቀምጧል፣ከጨረሱ ለመቀጠል 1 ይፃፋ፣ አለበለዚያ ቀጣዩን ምስል ያስገቡ።")
        return IMAGES
    elif update.message.text.lower() == "1" or count >= 4:
        if count == 0:
            context.user_data['image_urls'] = "AgACAgEAAxkBAAID22hN8PJ9sqEmVD0y_HN8CJZc-mYCAAJsrzEbpRdwRmFAXJN3jy8IAQADAgADeQADNgQ"
        else:
            context.user_data['image_urls'] = ",".join(context.user_data['image_urls'])
            
        await update.message.reply_text("☎️ ስልክ ቁጥርዎን ያስገቡ፥")
        return CONTACT
    else:
        await update.message.reply_text("🖼 የቤትዎን ምስል ያስገቡ ወይም '1' ይጻፉ ለመቀጠል:")
        return IMAGES

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contact'] = update.message.text
    user = update.effective_user
    context.user_data['posted_by'] = user.id

    try:
        response = requests.post(LISTINGS_URL, json=context.user_data)
        if response.status_code == 201:
            await update.message.reply_text("✅ የኪራይ ቤትዎ ዝርዝር በትክክል ተመዝግቧል።")
        else:
            print("Payload being sent:", context.user_data)
            print("response.text:", response.text)
            await update.message.reply_text("⚠️ የኪራይ ቤትዎ ዝርዝርዎ መመዝገብ አልተቻለም። እባክዎ ደግመው ይሞክሩ።")
            
    except Exception as e:
        await update.message.reply_text(f"⚠️ የኪራይ ቤትዎ ዝርዝርዎ መመዝገብ አልተቻለም። እባክዎ ደግመው ይሞክሩ። {e}")

    return ConversationHandler.END

async def post_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🏠 ለኪራይ ቤትዎ አጭር ርዕስ ይስጡ/ይጻፉ:ምሳሌ፡ ባለ 2 መኝታ ክፍል ኮንዶሚንየም... )")
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("💵 ወርሃዊ ኪራዩን በብር ይጻፉ:")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("🛏 የመኝታ ቤት ቁጥሩን ይጻፉ:")
    return BEDROOMS

async def get_bedrooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bedrooms'] = update.message.text
    keyboard = [[InlineKeyboardButton(REGION_MAP[rid], callback_data=f"post_region:{rid}")] for rid in REGIONS]
    await update.message.reply_text("📍 ቤትዎ ሚገኝበትን ክልል ይምረጡ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return REGION

async def post_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    region_key = query.data.split(":")[1]
    context.user_data['region'] = REGION_MAP[region_key]
    context.user_data['region_key'] = region_key

    city_keys = REGIONS.get(region_key, [])
    keyboard = [[InlineKeyboardButton(CITY_MAP[c], callback_data=f"post_city:{c}")] for c in city_keys]
    await query.message.reply_text("🏙 ቤትዎ ሚገኝበትን ከተማ ይምረጡ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CITY
# -------------------------------------------------------------------------------------------
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# -------------------------------------------------------------------------------------------


async def rental_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 በስሜ ያሉ ቤቶችን አሳይ", callback_data="show_listings")],
        [InlineKeyboardButton("➕ የሚከራይ ቤትዎን ይለጥፉ እና ለተከራዮች ያስተዋውቁ", callback_data="post")]
    ]
    await query.edit_message_text("አከራይ / ወኪል አማራጮች:", reply_markup=InlineKeyboardMarkup(keyboard))
    return RENTAL_MENU

async def show_my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    print(f"In owners section")
    try:
        response = requests.get(f"{LISTINGS_URL}/user/{user_id}")
        listings = response.json()

        if not listings:
            await query.edit_message_text("⚠️ በእርስዎ ስም የኪራይ ቤት ማግኘት አልቻልንም")
            return RENTAL_MENU

        for listing in listings:
            print(listing)
            caption = (
                    f" 🏠 *{listing['title']}*\n"
                    f" 📍{listing['region']} - {listing['city']} \n"
                    f" ☎️ {listing['contact']} \n"
                    f" 🛏 {listing['bedrooms']} መኝታ \n"           
                    f" 💵 {listing['price']} ብር/ወር \n"                  
                    f" 📝 {listing.get('description', '')}\n"
                    

                )
            image_urls = listing.get("image_urls", "").split(",")
            buttons = [
                [
                    InlineKeyboardButton("✏️ አስተካክል", callback_data=f"update:{listing['id']}"),
                    InlineKeyboardButton("❌ አጥፋ", callback_data=f"delete:{listing['id']}")
                ]
            ]
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=image_urls[0] if image_urls else "",
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    except Exception as e:
        await query.edit_message_text(f"⚠️ በእርስዎ ስም የኪራይ ቤት ማግኘት አልቻልንም: {e}")

    return RENTAL_MENU

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"Callback data received: {data}")

    if data.startswith("delete:"):
        listing_id = data.split(":")[1]
        try:
            res = requests.delete(f"{LISTINGS_URL}/{listing_id}")
            if res.status_code == 200:
                await query.message.reply_text("✅ ቤቱ በተሳካ ሁኔታ ተሰርዟል።")
            else:
                await query.message.reply_text("❌ የመሰረዝ ትእዛዝ አልተሳካም።")
        except Exception as e:
            await query.message.reply_text(f"Error deleting listing: {e}")
        return RENTAL_MENU
    elif data.startswith("update:"):
        listing_id = data.split(":")[1]
        context.user_data["update_listing_id"] = listing_id

        keyboard = [
            [InlineKeyboardButton("📝 Title", callback_data="update_field:title")],
            [InlineKeyboardButton("💵 Price", callback_data="update_field:price")],
            [InlineKeyboardButton("🛏 Bedrooms", callback_data="update_field:bedrooms")],
            [InlineKeyboardButton("📍 City", callback_data="update_field:city")],
            [InlineKeyboardButton("📄 Description", callback_data="update_field:description")],
        ]
        await query.edit_message_text("🛠 What do you want to update?", reply_markup=InlineKeyboardMarkup(keyboard))
        return UPDATE_FIELD
    

async def choose_update_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.split(":")[1]
    context.user_data["update_field"] = field
    await query.message.reply_text(f"✏️ Enter new value for {field}:")
    return UPDATE_VALUE

async def save_updated_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_value = update.message.text
    field = context.user_data["update_field"]
    listing_id = context.user_data["update_listing_id"]

    try:
        response = requests.put(f"{LISTINGS_URL}/{listing_id}", json={field: new_value})
        if response.status_code == 200:
            await update.message.reply_text("✅ Listing updated successfully.")
        else:
            await update.message.reply_text("❌ Failed to update the listing.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

    return ConversationHandler.END

# -------------------------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------------------------




def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    print('Bot started')

   
    
    # Search Menu
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(search_entry, pattern="^search$"))
    app.add_handler(CallbackQueryHandler(region_callback, pattern="^region:"))
    app.add_handler(CallbackQueryHandler(city_callback, pattern="^city:"))
    app.add_handler(CallbackQueryHandler(bed_callback, pattern="^bed:"))

    # Rental Owner Menu
    app.add_handler(CallbackQueryHandler(rental_menu, pattern="^rental_menu$"))
    app.add_handler(CallbackQueryHandler(show_my_listings, pattern="^show_listings$"))
   # app.add_handler(CallbackQueryHandler(handle_action, pattern="^(update|delete):"))

    # Add Listing Menu
    post_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(post_entry, pattern="^post$")],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            BEDROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bedrooms)],
            REGION: [CallbackQueryHandler(post_region_callback, pattern="^post_region:")],
            CITY: [CallbackQueryHandler(post_city_callback, pattern="^post_city:")],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            IMAGES: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, get_images)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)]
        },
        fallbacks=[]
    )

    app.add_handler(post_handler)


    update_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_action, pattern="^update:")],
            states={
                UPDATE_FIELD: [CallbackQueryHandler(choose_update_field, pattern="^update_field:")],
                UPDATE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_updated_value)],
            },
            fallbacks=[]
        )

    # Handlers should be added in this order:
    app.add_handler(update_handler)  # Add the update convo handler first
    app.add_handler(CallbackQueryHandler(handle_action, pattern="^(update|delete):"))  # Fallback for unmatched


    app.run_polling()

if __name__ == "__main__":
    main()
