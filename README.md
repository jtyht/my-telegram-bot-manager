# 🤖 Telegram Group Management Bot

## ফাইলগুলো
```
bot.py           — মূল bot কোড
data_manager.py  — data সেভ করার সিস্টেম
requirements.txt — প্রয়োজনীয় library
data.json        — bot নিজে তৈরি করবে (warn/settings)
```

---

## ✅ Setup করার নিয়ম

### ধাপ ১ — Bot Token নিন
1. Telegram এ @BotFather এ যান
2. `/newbot` লিখুন
3. নাম ও username দিন
4. Token কপি করুন (যেমন: `7123456789:AAF...`)

### ধাপ ২ — Python Install করুন
- Python 3.10+ লাগবে → https://python.org

### ধাপ ৩ — Library Install করুন
```bash
pip install -r requirements.txt
```

### ধাপ ৪ — Token বসান
`bot.py` ফাইলে এই লাইনটি খুঁজুন:
```python
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
```
`YOUR_BOT_TOKEN_HERE` এর জায়গায় আপনার token বসান।

অথবা environment variable সেট করুন:
```bash
# Linux/Mac
export BOT_TOKEN="আপনার_token"

# Windows
set BOT_TOKEN=আপনার_token
```

### ধাপ ৫ — Bot চালান
```bash
python bot.py
```

### ধাপ ৬ — Bot কে গ্রুপে Promote করুন
গ্রুপে bot যোগ করার পর অবশ্যই **Admin** করুন এবং এই permissions দিন:
- ✅ Delete messages
- ✅ Ban users
- ✅ Restrict members
- ✅ Pin messages
- ✅ Add new admins

---

## 📋 সব কমান্ড

| কমান্ড | কাজ |
|--------|-----|
| `/start` | Bot শুরু |
| `/help` | সব কমান্ড দেখুন |
| `/setwelcome <msg>` | Welcome message সেট |
| `/setleave <msg>` | Leave message সেট |
| `/warn` | User কে warn করুন (reply করে) |
| `/warns` | কতটি warn দেখুন |
| `/resetwarn` | Warn রিসেট করুন |
| `/ban` | User ব্যান করুন |
| `/unban` | ব্যান তুলুন |
| `/kick` | User কিক করুন |
| `/mute` | User মিউট করুন |
| `/unmute` | মিউট তুলুন |
| `/promote` | Admin করুন |
| `/demote` | Admin থেকে সরান |
| `/pin` | Message pin করুন |
| `/unpin` | সব pin তুলুন |
| `/del` | Message মুছুন |
| `/info` | User তথ্য দেখুন |
| `/antilink` | Anti-link চালু/বন্ধ |
| `/antiflood` | Anti-flood চালু/বন্ধ |
| `/addbadword` | Bad word যোগ করুন |
| `/rmbadword` | Bad word সরান |
| `/badwords` | Bad word তালিকা |
| `/rules` | গ্রুপের নিয়ম দেখুন |
| `/setrules <rules>` | নিয়ম সেট করুন |
| `/broadcast <msg>` | সবাইকে message পাঠান |

---

## 🌐 VPS/Server এ চালানো (24/7)

### Railway (ফ্রি)
1. https://railway.app এ account খুলুন
2. New Project → Deploy from GitHub
3. Environment variable এ `BOT_TOKEN` সেট করুন

### Koyeb (ফ্রি)
1. https://koyeb.com এ account খুলুন
2. Web Service → GitHub repo connect করুন
3. `BOT_TOKEN` environment variable দিন

---

## ⚠️ সমস্যা হলে
- Bot কে group Admin না করলে কাজ করবে না
- Token ভুল হলে bot চালু হবে না
- Python 3.10+ না থাকলে error আসবে
