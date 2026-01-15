import streamlit as st
import sqlite3
import os
import json
import base64
from datetime import datetime
import time
from streamlit_option_menu import option_menu
from PIL import Image
import hashlib
import uuid
import io

# --- 1. კონფიგურაცია ---
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'audio'
for folder in [UPLOAD_FOLDER, AUDIO_FOLDER]:
    if not os.path.exists(folder): 
        os.makedirs(folder)

DB_FILE = 'social_db.db'
REACTIONS = ["👍", "❤️", "😂", "😮", "😡", "😢", "🔥"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
PHOTOS_PER_PAGE = 9

# სესიის ცვლადები
if 'user' not in st.session_state: st.session_state.user = None
if 'view_profile' not in st.session_state: st.session_state.view_profile = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0
if 'view_photo_id' not in st.session_state: st.session_state.view_photo_id = None
if 'chat_input_val' not in st.session_state: st.session_state.chat_input_val = ""
if 'active_friend_chat' not in st.session_state: st.session_state.active_friend_chat = None
if 'gallery_page' not in st.session_state: st.session_state.gallery_page = 0

def reset_keys():
    """Reset file uploader keys to clear inputs"""
    st.session_state.uploader_key += 1
    st.session_state.audio_key += 1

# --- 2. უსაფრთხოების ფუნქციები ---
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_file(uploaded_file):
    """Validate uploaded file (type, size)"""
    if not uploaded_file:
        return None, None
    
    # Check file size
    file_size = uploaded_file.size
    if file_size > MAX_FILE_SIZE:
        return None, "ფაილი ძალიან დიდია (მაქს. 5MB)"
    
    # Check extension
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"დაუშვებელი ფორმატი. მხოლოდ: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Validate image with PIL
    try:
        img = Image.open(uploaded_file)
        if img.format.lower() not in ['png', 'jpeg']:
            return None, "დაზიანებული სურათი"
        
        # Reset file pointer
        uploaded_file.seek(0)
        return img, None
    except Exception as e:
        return None, f"შეცდომა სურათის წაკითხვისას: {str(e)}"

def save_file(uploaded_file, prefix='img'):
    """Save uploaded file with UUID filename"""
    img, error = validate_file(uploaded_file)
    if error:
        return None, error
    
    try:
        # Generate unique filename
        ext = uploaded_file.name.split('.')[-1].lower()
        filename = f"{prefix}_{uuid.uuid4()}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Optimize and save image
        img_optimized = img.copy()
        img_optimized.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        img_optimized.save(filepath, optimize=True, quality=85)
        
        return filepath, None
    except Exception as e:
        return None, f"შენახვის შეცდომა: {str(e)}"

# --- 3. SVG აიქონები (IMPROVED & BEAUTIFUL) ---
# ფოტოს ატვირთვა (ლურჯი gradient + camera icon)
ICON_PHOTO = """
<svg width="44" height="44" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="photoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#3390ec;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0088cc;stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="22" cy="22" r="20" fill="url(#photoGrad)" opacity="0.1"/>
  <g transform="translate(10, 10)">
    <rect x="2" y="5" width="20" height="16" rx="2" fill="none" stroke="url(#photoGrad)" stroke-width="2"/>
    <circle cx="12" cy="13" r="3" fill="none" stroke="url(#photoGrad)" stroke-width="2"/>
    <path d="M7 5 L9 2 L15 2 L17 5" fill="none" stroke="url(#photoGrad)" stroke-width="2"/>
  </g>
</svg>
"""

# მიკროფონი (წითელი pulse animation)
ICON_MIC = """
<svg width="44" height="44" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="micGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ff4757;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#ff3838;stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="22" cy="22" r="20" fill="url(#micGrad)" opacity="0.1"/>
  <g transform="translate(12, 8)">
    <rect x="7" y="2" width="6" height="10" rx="3" fill="url(#micGrad)"/>
    <path d="M3 12 Q3 16 10 16 Q17 16 17 12" fill="none" stroke="url(#micGrad)" stroke-width="2"/>
    <line x1="10" y1="16" x2="10" y2="20" stroke="url(#micGrad)" stroke-width="2"/>
    <line x1="7" y1="20" x2="13" y2="20" stroke="url(#micGrad)" stroke-width="2"/>
  </g>
</svg>
"""

# გაგზავნა (თეთრი paper plane)
ICON_SEND = """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M22 2 L11 13" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M22 2 L15 22 L11 13 L2 9 Z" fill="white"/>
</svg>
"""

# წაშლა (წითელი trash can)
ICON_TRASH = """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 6 L5 6 L21 6" stroke="#ff4757" stroke-width="2" stroke-linecap="round"/>
  <path d="M19 6 L19 20 Q19 21 18 21 L6 21 Q5 21 5 20 L5 6" fill="none" stroke="#ff4757" stroke-width="2"/>
  <line x1="10" y1="11" x2="10" y2="17" stroke="#ff4757" stroke-width="2" stroke-linecap="round"/>
  <line x1="14" y1="11" x2="14" y2="17" stroke="#ff4757" stroke-width="2" stroke-linecap="round"/>
  <path d="M8 6 L8 4 Q8 3 9 3 L15 3 Q16 3 16 4 L16 6" fill="none" stroke="#ff4757" stroke-width="2"/>
</svg>
"""

LOGO_SVG = """
<svg width="250" height="60" viewBox="0 0 300 60" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#3390ec;stop-opacity:1" /><stop offset="100%" style="stop-color:#0088cc;stop-opacity:1" /></linearGradient></defs>
  <circle cx="35" cy="30" r="20" fill="url(#grad1)" /><path d="M25 25 Q35 15 45 25 T65 25" stroke="white" stroke-width="2" fill="none"/><path d="M20 30 H50" stroke="white" stroke-width="2" />
  <text x="70" y="40" font-family="Arial, sans-serif" font-size="35" font-weight="bold" fill="#333">Geo<tspan fill="#3390ec">Social</tspan></text>
</svg>
"""

# --- 4. CSS (IMPROVED TELEGRAM STYLE) ---
def inject_custom_code():
    # Convert SVG to base64
    photo_b64 = base64.b64encode(ICON_PHOTO.encode()).decode()
    mic_b64 = base64.b64encode(ICON_MIC.encode()).decode()
    send_b64 = base64.b64encode(ICON_SEND.encode()).decode()
    trash_b64 = base64.b64encode(ICON_TRASH.encode()).decode()
    
    st.markdown(f"""
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            /* === MOBILE OPTIMIZATION === */
            .block-container {{
                padding-top: 4rem !important;
                padding-bottom: 130px !important;
                max-width: 100% !important;
            }}
            header[data-testid="stHeader"] {{ 
                z-index: 100; 
                background: rgba(255,255,255,0.98) !important;
                backdrop-filter: blur(10px);
                height: 3.5rem !important;
                border-bottom: 1px solid #f0f0f0;
            }}

            /* === LOADING SPINNER === */
            .stSpinner > div {{
                border-color: #3390ec !important;
            }}

            /* === 1. SEND BUTTON (TELEGRAM BLUE CIRCLE WITH TEXT) === */
            .telegram-send button {{
                border: none !important;
                background: linear-gradient(135deg, #3390ec 0%, #0088cc 100%) !important;
                min-width: 80px !important;
                height: 48px !important;
                border-radius: 24px !important;
                color: white !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                box-shadow: 0 4px 12px rgba(51, 144, 236, 0.4) !important;
                transition: all 0.2s ease !important;
                cursor: pointer !important;
                padding: 0 20px !important;
            }}
            .telegram-send button p {{
                color: white !important;
                font-weight: 600 !important;
            }}
            .telegram-send button:hover {{
                transform: scale(1.05) !important;
                box-shadow: 0 6px 16px rgba(51, 144, 236, 0.5) !important;
            }}
            .telegram-send button:active {{
                transform: scale(0.95) !important;
            }}

            /* === 2. TRASH BUTTON === */
            .trash-btn button {{
                border: none !important;
                background: #f4f4f5 !important;
                width: 48px !important;
                height: 48px !important;
                border-radius: 24px !important;
                color: #ff4757 !important;
                font-weight: 600 !important;
                font-size: 13px !important;
                transition: all 0.2s ease !important;
                cursor: pointer !important;
            }}
            .trash-btn button p {{
                color: #ff4757 !important;
                font-weight: 600 !important;
            }}
            .trash-btn button:hover {{
                background: #ffebee !important;
                transform: scale(1.05) !important;
            }}
            .trash-btn button:active {{
                transform: scale(0.95) !important;
            }}

            /* === 3. PHOTO UPLOAD BUTTON (BEAUTIFUL GRADIENT) === */
            .photo-upload {{
                position: relative;
                width: 48px !important;
                height: 48px !important;
            }}
            .photo-upload [data-testid="stFileUploader"] {{
                width: 48px !important;
                height: 48px !important;
            }}
            .photo-upload label, 
            .photo-upload span, 
            .photo-upload small {{
                display: none !important;
            }}
            .photo-upload button {{
                border: none !important;
                background: transparent !important;
                width: 48px !important;
                height: 48px !important;
                padding: 0 !important;
                color: transparent !important;
                background-image: url('data:image/svg+xml;base64,{photo_b64}') !important;
                background-repeat: no-repeat !important;
                background-position: center !important;
                background-size: 44px !important;
                transition: transform 0.2s ease !important;
            }}
            .photo-upload button:hover {{
                transform: scale(1.1) !important;
            }}
            .photo-upload button:active {{
                transform: scale(0.95) !important;
            }}
            .photo-upload section {{
                padding: 0 !important;
                min-height: 0 !important;
                border: none !important;
            }}

            /* === 4. MICROPHONE (BEAUTIFUL RED GRADIENT) === */
            .mic-input {{
                position: relative;
                width: 48px !important;
                height: 48px !important;
            }}
            .mic-input .stAudioInput {{
                width: 48px !important;
                height: 48px !important;
            }}
            .mic-input label,
            .mic-input p {{
                display: none !important;
            }}
            .mic-input button {{
                border: none !important;
                background: transparent !important;
                width: 48px !important;
                height: 48px !important;
                border-radius: 50% !important;
                padding: 0 !important;
                color: transparent !important;
                background-image: url('data:image/svg+xml;base64,{mic_b64}') !important;
                background-repeat: no-repeat !important;
                background-position: center !important;
                background-size: 44px !important;
                transition: transform 0.2s ease !important;
                animation: micPulse 2s infinite !important;
            }}
            .mic-input button:hover {{
                transform: scale(1.1) !important;
            }}
            .mic-input button:active {{
                transform: scale(0.95) !important;
            }}
            
            @keyframes micPulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.7; }}
            }}

            /* === BOTTOM BAR (FIXED LAYOUT) === */
            .bottom-bar {{
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background: white;
                padding: 10px 8px 20px 8px;
                border-top: 1px solid #e8e8e8;
                z-index: 9999;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
            }}
            
            /* Container adjustment for bottom bar */
            .main .block-container {{
                padding-bottom: 120px !important;
            }}

            /* === INPUT FIELD === */
            .stTextInput input {{
                border-radius: 24px !important;
                background: #f4f4f5 !important;
                border: 1px solid #e8e8e8 !important;
                padding: 12px 18px !important;
                height: 48px !important;
                font-size: 15px !important;
                transition: all 0.2s ease !important;
            }}
            .stTextInput input:focus {{
                border-color: #ff4757 !important;
                background: white !important;
                box-shadow: 0 0 0 3px rgba(255, 71, 87, 0.1) !important;
                outline: none !important;
            }}

            /* === PROFILE STYLES === */
            .profile-header {{ 
                position: relative; 
                width: 100%; 
                margin-bottom: 70px; 
            }}
            .cover-box {{
                width: 100% !important;
                height: 200px !important;
                object-fit: fill !important;
                border-radius: 0;
                display: block;
            }}
            .avatar-box {{ 
                width: 110px; 
                height: 110px; 
                border-radius: 50%; 
                border: 4px solid white; 
                position: absolute; 
                bottom: -45px; 
                left: 20px; 
                object-fit: cover; 
                background: #fff; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
            }}
            .profile-name-block {{ 
                position: absolute; 
                bottom: -35px; 
                left: 145px; 
            }}
            .profile-nickname {{ 
                font-size: 22px; 
                font-weight: bold; 
            }}

            /* === TOAST NOTIFICATIONS === */
            .stToast {{
                background: #3390ec !important;
                color: white !important;
            }}

            /* === BUTTONS === */
            .stButton button {{
                transition: all 0.2s ease !important;
            }}
            .stButton button:hover {{
                transform: translateY(-1px) !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
            }}
        </style>
    """, unsafe_allow_html=True)

# --- 5. მონაცემთა ბაზა (IMPROVED WITH INDEXES) ---
def run_query(query, params=(), fetch=False, fetch_one=False):
    """Execute SQL query with error handling"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute(query, params)
            if fetch: 
                return c.fetchall()
            if fetch_one: 
                return c.fetchone()
            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return None if (fetch or fetch_one) else False

def init_db():
    """Initialize database with indexes and optimizations"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create tables
    run_query('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, 
        password TEXT, 
        avatar TEXT, 
        bio TEXT, 
        cover_photo TEXT, 
        birthday DATE, 
        hobbies TEXT, 
        real_name TEXT, 
        last_name TEXT
    )''')
    
    run_query('''CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user TEXT, 
        image_path TEXT, 
        timestamp DATETIME, 
        description TEXT, 
        reactions_json TEXT,
        FOREIGN KEY (user) REFERENCES users(username) ON DELETE CASCADE
    )''')
    
    run_query('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        author TEXT, 
        content TEXT, 
        image_path TEXT, 
        timestamp DATETIME, 
        reactions_json TEXT,
        FOREIGN KEY (author) REFERENCES users(username) ON DELETE CASCADE
    )''')
    
    run_query('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        sender TEXT, 
        receiver TEXT, 
        content TEXT, 
        image_path TEXT, 
        audio_path TEXT, 
        timestamp DATETIME, 
        reactions_json TEXT, 
        read_status INTEGER DEFAULT 0,
        FOREIGN KEY (sender) REFERENCES users(username) ON DELETE CASCADE
    )''')
    
    run_query('''CREATE TABLE IF NOT EXISTS friendships (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user1 TEXT, 
        user2 TEXT, 
        status TEXT,
        FOREIGN KEY (user1) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY (user2) REFERENCES users(username) ON DELETE CASCADE
    )''')
    
    # Check if columns exist before adding them
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'real_name' not in columns:
        try: run_query("ALTER TABLE users ADD COLUMN real_name TEXT")
        except: pass
    
    if 'last_name' not in columns:
        try: run_query("ALTER TABLE users ADD COLUMN last_name TEXT")
        except: pass
    
    c.execute("PRAGMA table_info(messages)")
    msg_columns = [col[1] for col in c.fetchall()]
    
    if 'read_status' not in msg_columns:
        try: run_query("ALTER TABLE messages ADD COLUMN read_status INTEGER DEFAULT 0")
        except: pass
    
    conn.close()
    
    # Create indexes for performance
    run_query("CREATE INDEX IF NOT EXISTS idx_gallery_user ON gallery(user)")
    run_query("CREATE INDEX IF NOT EXISTS idx_gallery_timestamp ON gallery(timestamp DESC)")
    run_query("CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp DESC)")
    run_query("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)")
    run_query("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)")
    run_query("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    run_query("CREATE INDEX IF NOT EXISTS idx_friendships_users ON friendships(user1, user2)")

@st.cache_data(ttl=300)
def get_user_info(username):
    """Get user info with caching (5 min TTL)"""
    return run_query("SELECT * FROM users WHERE username = ?", (username,), fetch_one=True)

@st.cache_data(ttl=60)
def get_friends(username):
    """Get friends list with caching (1 min TTL)"""
    data = run_query(
        "SELECT user1, user2 FROM friendships WHERE (user1=? OR user2=?) AND status='accepted'", 
        (username, username), 
        fetch=True
    )
    return [r[1] if r[0] == username else r[0] for r in data] if data else []

@st.cache_data(ttl=3600)
def get_img_64(path):
    """Convert image to base64 with caching (1 hour TTL)"""
    if not path or not os.path.exists(path): 
        return "https://via.placeholder.com/150"
    try:
        with open(path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
            ext = path.split('.')[-1].lower()
            mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'
            return f"data:{mime};base64,{img_data}"
    except Exception as e:
        st.error(f"Image load error: {str(e)}")
        return "https://via.placeholder.com/150"

def get_img_obj(path):
    """Load image as PIL object"""
    if path and os.path.exists(path):
        try: 
            return Image.open(path)
        except Exception as e:
            st.error(f"შეცდომა სურათის ჩატვირთვისას: {str(e)}")
            return None
    return None

def count_notifications(user):
    """Count unread notifications"""
    req_count = run_query(
        "SELECT count(*) FROM friendships WHERE user2=? AND status='pending'", 
        (user,), 
        fetch_one=True
    )
    msg_count = run_query(
        "SELECT count(*) FROM messages WHERE receiver=? AND read_status=0", 
        (user,), 
        fetch_one=True
    )
    return (req_count[0] if req_count else 0), (msg_count[0] if msg_count else 0)

def get_zodiac(date_str):
    """Calculate zodiac sign from birthdate"""
    if not date_str: 
        return ""
    try:
        d = datetime.strptime(str(date_str), '%Y-%m-%d')
        day, month = d.day, d.month
        zodiacs = [
            (20, "თხის რქა"), (19, "მერწყული"), (20, "თევზები"), (20, "ვერძი"), 
            (21, "კურო"), (21, "ტყუპები"), (22, "კირჩხიბი"), (22, "ლომი"), 
            (23, "ქალწული"), (23, "სასწორი"), (23, "მორიელი"), (21, "მშვილდოსანი"), 
            (31, "თხის რქა")
        ]
        if day <= zodiacs[month-1][0]: 
            return zodiacs[month-1][1]
        else: 
            return zodiacs[month][1]
    except:
        return ""

# --- 6. UI კომპონენტები ---
def render_reactions(item_id, current_reactions_json, user, table):
    """Render reaction system"""
    reactions_dict = json.loads(current_reactions_json) if current_reactions_json else {}
    counts = {}
    for r in reactions_dict.values(): 
        counts[r] = counts.get(r, 0) + 1
    status = " ".join([f"{k}{v}" for k, v in counts.items()])
    
    c1, c2 = st.columns([0.85, 0.15])
    with c1: 
        st.caption(status if status else "რეაქციები")
    with c2:
        with st.popover("🙂"):
            cols = st.columns(4)
            for idx, emoji in enumerate(REACTIONS):
                with cols[idx % 4]:
                    if st.button(emoji, key=f"r_{table}_{item_id}_{idx}"):
                        data = run_query(
                            f"SELECT reactions_json FROM {table} WHERE id=?", 
                            (item_id,), 
                            fetch_one=True
                        )
                        curr = json.loads(data[0]) if (data and data[0]) else {}
                        if curr.get(user) == emoji: 
                            del curr[user]
                        else: 
                            curr[user] = emoji
                        run_query(
                            f"UPDATE {table} SET reactions_json=? WHERE id=?", 
                            (json.dumps(curr), item_id)
                        )
                        # Clear cache
                        st.cache_data.clear()
                        st.rerun()

def render_profile_page(target_user, me):
    """Render user profile page with gallery"""
    info = get_user_info(target_user)
    if not info:
        st.error("მომხმარებელი ვერ მოიძებნა")
        return
    
    cv = get_img_64(info[4]) if info[4] else None
    av = get_img_64(info[2]) if info[2] else None
    full_name = f"{info[7]} {info[8]}" if (len(info) > 8 and info[7]) else ""
    
    # Profile Header
    cover_img = cv if cv else "https://via.placeholder.com/800x180/667eea/ffffff?text=Cover"
    avatar_img = av if av else "https://via.placeholder.com/110/3390ec/ffffff?text=Avatar"
    
    st.markdown(f'''
        <div class="profile-header">
            <img src="{cover_img}" class="cover-box">
            <img src="{avatar_img}" class="avatar-box">
            <div class="profile-name-block">
                <span class="profile-nickname">{target_user}</span><br>
                <small style="color: #666;">{full_name}</small>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.write("")
    c1, c2 = st.columns(2)
    with c1: 
        st.info(f"📝 {info[3] if info[3] else 'ბიოგრაფია არ არის'}")
        if info[5]: 
            st.write(f"🎂 {info[5]} ({get_zodiac(info[5])})")
    with c2: 
        st.write(f"🎨 {info[6] if info[6] else 'ჰობი არ არის მითითებული'}")

    # Photo viewer modal
    if st.session_state.view_photo_id:
        st.divider()
        p_data = run_query(
            "SELECT * FROM gallery WHERE id=?", 
            (st.session_state.view_photo_id,), 
            fetch_one=True
        )
        if p_data:
            col_img = st.container()
            with col_img:
                img_obj = get_img_obj(p_data[2])
                if img_obj: 
                    st.image(img_obj, use_container_width=True)
                else:
                    st.error("სურათის ჩატვირთვა ვერ მოხერხდა")
            
            if target_user == me:
                c1, c2, c3 = st.columns(3)
                if c1.button("💤 ავატარად"):
                    if run_query("UPDATE users SET avatar=? WHERE username=?", (p_data[2], me)):
                        st.cache_data.clear()
                        st.toast("✅ ავატარი შეიცვალა!")
                        time.sleep(1)
                        st.rerun()
                
                if c2.button("🖼️ ქავერად"):
                    if run_query("UPDATE users SET cover_photo=? WHERE username=?", (p_data[2], me)):
                        st.cache_data.clear()
                        st.toast("✅ ქავერი შეიცვალა!")
                        time.sleep(1)
                        st.rerun()
                
                if c3.button("🗑️ წაშლა"):
                    if run_query("DELETE FROM gallery WHERE id=?", (p_data[0],)):
                        # Delete physical file
                        try:
                            if os.path.exists(p_data[2]):
                                os.remove(p_data[2])
                        except:
                            pass
                        st.session_state.view_photo_id = None
                        st.cache_data.clear()
                        st.toast("✅ წაშლილია!")
                        time.sleep(1)
                        st.rerun()
            
            if st.button("❌ დახურვა", use_container_width=True):
                st.session_state.view_photo_id = None
                st.rerun()
            
            render_reactions(p_data[0], p_data[5], me, 'gallery')
            return

    # Tabs
    if target_user == me:
        t_gal, t_edit = st.tabs(["📷 გალერეა", "⚙️ რედაქტირება"])
    else:
        t_gal, = st.tabs(["📷 გალერეა"])
    
    with t_gal:
        if target_user == me:
            st.write("**ფოტოს დამატება:**")
            
            # File uploader with proper styling
            col1, col2 = st.columns([0.2, 0.8])
            with col1:
                st.markdown('<div class="photo-upload">', unsafe_allow_html=True)
                upl = st.file_uploader(
                    "ფოტო", 
                    type=['png', 'jpg', 'jpeg'], 
                    key=f"gallery_upload_{st.session_state.uploader_key}",
                    label_visibility="collapsed"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                if upl:
                    with st.spinner("იტვირთება..."):
                        filepath, error = save_file(upl, prefix='gallery')
                        if error:
                            st.error(error)
                        else:
                            success = run_query(
                                "INSERT INTO gallery (user, image_path, timestamp, description, reactions_json) VALUES (?,?,?,?,?)",
                                (me, filepath, datetime.now(), "", "{}")
                            )
                            if success:
                                st.cache_data.clear()
                                reset_keys()
                                st.toast("✅ ფოტო დაემატა!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("შენახვის შეცდომა")
        
        st.divider()
        
        # Gallery with pagination
        photos = run_query(
            "SELECT id, image_path FROM gallery WHERE user=? ORDER BY timestamp DESC", 
            (target_user,), 
            fetch=True
        )
        
        if not photos:
            st.info("📷 გალერეა ცარიელია")
        else:
            total_photos = len(photos)
            total_pages = (total_photos - 1) // PHOTOS_PER_PAGE + 1
            current_page = st.session_state.gallery_page
            
            # Pagination controls
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if current_page > 0:
                        if st.button("◀ წინა"):
                            st.session_state.gallery_page -= 1
                            st.rerun()
                with col2:
                    st.write(f"გვერდი {current_page + 1} / {total_pages}")
                with col3:
                    if current_page < total_pages - 1:
                        if st.button("შემდეგი ▶"):
                            st.session_state.gallery_page += 1
                            st.rerun()
            
            # Display photos
            start_idx = current_page * PHOTOS_PER_PAGE
            end_idx = min(start_idx + PHOTOS_PER_PAGE, total_photos)
            page_photos = photos[start_idx:end_idx]
            
            cols = st.columns(3)
            for i, ph in enumerate(page_photos):
                with cols[i % 3]:
                    img_obj = get_img_obj(ph[1])
                    if img_obj:
                        st.image(img_obj, use_container_width=True)
                        if st.button("გახსნა", key=f"open_photo_{ph[0]}", use_container_width=True):
                            st.session_state.view_photo_id = ph[0]
                            st.rerun()
    
    if target_user == me:
        with t_edit:
            st.write("**პროფილის რედაქტირება**")
            with st.form("edit_profile"):
                rn = st.text_input("სახელი", value=info[7] if len(info) > 7 and info[7] else "")
                ln = st.text_input("გვარი", value=info[8] if len(info) > 8 and info[8] else "")
                nbd = st.date_input(
                    "დაბადების თარიღი", 
                    value=datetime.strptime(info[5], '%Y-%m-%d') if info[5] else None
                )
                nh = st.text_input("ჰობი", value=info[6] if info[6] else "")
                bio = st.text_area("ბიო", value=info[3] if info[3] else "", height=100)
                
                if st.form_submit_button("💾 შენახვა", use_container_width=True):
                    with st.spinner("ინახება..."):
                        success = run_query(
                            "UPDATE users SET bio=?, real_name=?, last_name=?, birthday=?, hobbies=? WHERE username=?",
                            (bio, rn, ln, str(nbd) if nbd else None, nh, me)
                        )
                        if success:
                            st.cache_data.clear()
                            st.toast("✅ პროფილი განახლდა!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("შენახვის შეცდომა")

def render_chat_input_bar(receiver_id):
    """Render beautiful chat input bar with icons"""
    st.markdown('<div class="bottom-bar">', unsafe_allow_html=True)
    
    # Layout: Photo | Mic | Text Input | Send | Delete
    c1, c2, c3, c4, c5 = st.columns(
        [0.11, 0.11, 0.54, 0.13, 0.11], 
        gap="small", 
        vertical_alignment="center"
    )
    
    # Photo upload
    with c1:
        st.markdown('<div class="photo-upload">', unsafe_allow_html=True)
        up_img = st.file_uploader(
            "img", 
            type=['png', 'jpg', 'jpeg'], 
            key=f"chat_img_{receiver_id}_{st.session_state.uploader_key}",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Audio recorder
    with c2:
        st.markdown('<div class="mic-input">', unsafe_allow_html=True)
        aud_rec = st.audio_input(
            "audio", 
            key=f"chat_aud_{receiver_id}_{st.session_state.audio_key}",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Text input
    with c3:
        txt_in = st.text_input(
            "message", 
            key=f"chat_txt_{receiver_id}",
            label_visibility="collapsed",
            placeholder="ტექსტი...",
            value=st.session_state.chat_input_val
        )
    
    # Send button
    with c4:
        st.markdown('<div class="telegram-send">', unsafe_allow_html=True)
        if st.button("გაგზავნა", key=f"send_{receiver_id}"):
            img_path, aud_path = None, None
            
            # Handle image upload
            if up_img:
                with st.spinner("სურათი იტვირთება..."):
                    img_path, error = save_file(up_img, prefix='chat')
                    if error:
                        st.error(error)
                        img_path = None
            
            # Handle audio
            if aud_rec:
                try:
                    aud_path = os.path.join(AUDIO_FOLDER, f"aud_{uuid.uuid4()}.wav")
                    with open(aud_path, "wb") as f:
                        f.write(aud_rec.getbuffer())
                except Exception as e:
                    st.error(f"აუდიოს შენახვის შეცდომა: {str(e)}")
                    aud_path = None
            
            # Send message
            if txt_in or img_path or aud_path:
                with st.spinner("იგზავნება..."):
                    success = run_query(
                        "INSERT INTO messages (sender, receiver, content, image_path, audio_path, timestamp, reactions_json) VALUES (?,?,?,?,?,?,?)",
                        (st.session_state.user, receiver_id, txt_in, img_path, aud_path, datetime.now(), "{}")
                    )
                    if success:
                        st.session_state.chat_input_val = ""
                        st.cache_data.clear()
                        reset_keys()
                        st.rerun()
                    else:
                        st.error("შეტყობინების გაგზავნა ვერ მოხერხდა")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Delete button
    with c5:
        st.markdown('<div class="trash-btn">', unsafe_allow_html=True)
        if st.button("წაშლა", key=f"del_{receiver_id}"):
            st.session_state.chat_input_val = ""
            reset_keys()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. MAIN APP ---
def main():
    st.set_page_config(
        page_title="GeoSocial", 
        layout="wide", 
        initial_sidebar_state="expanded",
        page_icon="💬"
    )
    inject_custom_code()
    init_db()

    # Session management
    if 'user' not in st.session_state or st.session_state.user is None:
        params = st.query_params
        if "logged_in_user" in params:
            st.session_state.user = params["logged_in_user"]
        else:
            st.session_state.user = None

    # Login/Register Page
    if not st.session_state.user:
        _, c, _ = st.columns([1, 1.5, 1])
        with c:
            st.markdown(LOGO_SVG, unsafe_allow_html=True)
            t_log, t_reg = st.tabs(["🔓 შესვლა", "📝 რეგისტრაცია"])
            
            with t_log:
                with st.form("login_form"):
                    u = st.text_input("ნიკნეიმი", key="log_u")
                    p = st.text_input("პაროლი", type="password", key="log_p")
                    
                    if st.form_submit_button("🔑 შესვლა", use_container_width=True):
                        if not u or not p:
                            st.error("შეავსეთ ყველა ველი")
                        else:
                            with st.spinner("შემოწმება..."):
                                hashed_p = hash_password(p)
                                user_data = run_query(
                                    "SELECT * FROM users WHERE username=? AND password=?", 
                                    (u, hashed_p), 
                                    fetch_one=True
                                )
                                if user_data:
                                    st.session_state.user = u
                                    st.query_params["logged_in_user"] = u
                                    st.success("✅ წარმატებით შეხვედით!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ არასწორი მონაცემები")
            
            with t_reg:
                with st.form("register_form"):
                    ru = st.text_input("ნიკნეიმი (უნიკალური)", key="reg_u")
                    rp = st.text_input("პაროლი (მინ. 6 სიმბოლო)", type="password", key="reg_p")
                    rp2 = st.text_input("გაიმეორეთ პაროლი", type="password", key="reg_p2")
                    rn = st.text_input("სახელი", key="reg_rn")
                    rl = st.text_input("გვარი", key="reg_rl")
                    
                    if st.form_submit_button("📝 რეგისტრაცია", use_container_width=True):
                        # Validation
                        if not ru or not rp or not rn or not rl:
                            st.error("შეავსეთ ყველა ველი")
                        elif len(rp) < 6:
                            st.error("პაროლი უნდა იყოს მინ. 6 სიმბოლო")
                        elif rp != rp2:
                            st.error("პაროლები არ ემთხვევა")
                        else:
                            with st.spinner("რეგისტრაცია..."):
                                hashed_p = hash_password(rp)
                                success = run_query(
                                    "INSERT INTO users (username, password, bio, real_name, last_name) VALUES (?,?,?,?,?)",
                                    (ru, hashed_p, "ახალი მომხმარებელი", rn, rl)
                                )
                                if success:
                                    st.success("✅ რეგისტრაცია წარმატებით დასრულდა!")
                                    st.info("ახლა შეგიძლიათ შეხვიდეთ")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("❌ ნიკნეიმი უკვე დაკავებულია")
        return

    # Main App (Logged In)
    me = st.session_state.user
    reqs, msgs = count_notifications(me)
    
    # Sidebar
    with st.sidebar:
        st.markdown(LOGO_SVG, unsafe_allow_html=True)
        menu = option_menu(
            None, 
            [
                "სიახლეები", 
                "საერთო ჩათი", 
                f"წერილები {'🔴' if msgs else ''}", 
                f"მეგობრები {'🔴' if reqs else ''}", 
                "პროფილი"
            ],
            icons=['newspaper', 'chat', 'envelope', 'people', 'person'],
            default_index=0
        )
        st.divider()
        if st.button("🚪 გასვლა", use_container_width=True):
            st.session_state.user = None
            st.query_params.clear()
            st.cache_data.clear()
            st.rerun()

    # === NEWS FEED ===
    if menu == "სიახლეები":
        # New post form
        with st.container(border=True):
            st.write("📝 **ახალი პოსტი**")
            with st.form("new_post"):
                txt = st.text_area(
                    "შინაარსი", 
                    label_visibility="collapsed",
                    height=80,
                    placeholder="რა ხდება?"
                )
                
                col1, col2 = st.columns([0.3, 0.7])
                with col1:
                    st.markdown('<div class="photo-upload">', unsafe_allow_html=True)
                    img = st.file_uploader(
                        "სურათი", 
                        type=['png', 'jpg', 'jpeg'],
                        label_visibility="collapsed",
                        key=f"post_img_{st.session_state.uploader_key}"
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    submit = st.form_submit_button("📤 გამოქვეყნება", use_container_width=True)
                
                if submit:
                    if not txt and not img:
                        st.error("დაწერეთ ტექსტი ან ატვირთეთ სურათი")
                    else:
                        with st.spinner("იქვეყნება..."):
                            path = None
                            if img:
                                path, error = save_file(img, prefix='post')
                                if error:
                                    st.error(error)
                                    path = None
                            
                            success = run_query(
                                "INSERT INTO posts (author, content, image_path, timestamp, reactions_json) VALUES (?,?,?,?,?)",
                                (me, txt, path, datetime.now(), "{}")
                            )
                            if success:
                                st.cache_data.clear()
                                reset_keys()
                                st.toast("✅ პოსტი გამოქვეყნდა!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("გამოქვეყნება ვერ მოხერხდა")
        
        # Display posts
        st.divider()
        posts = run_query(
            """SELECT p.*, u.avatar, u.real_name, u.last_name 
               FROM posts p 
               LEFT JOIN users u ON p.author = u.username 
               ORDER BY p.timestamp DESC""",
            fetch=True
        )
        
        if not posts:
            st.info("📭 პოსტები არ არის")
        else:
            for p in posts:
                with st.container(border=True):
                    c_head, c_body = st.columns([0.12, 0.88])
                    with c_head:
                        avatar_path = p[6] if len(p) > 6 and p[6] else None
                        if avatar_path:
                            st.image(get_img_64(avatar_path), width=50)
                        else:
                            st.write("👤")
                        if st.button("პროფ.", key=f"prof_post_{p[0]}"):
                            st.session_state.view_profile = p[1]
                            st.rerun()
                    
                    with c_body:
                        author_name = f"{p[7]} {p[8]}" if (len(p) > 8 and p[7]) else p[1]
                        st.write(f"**{author_name}** (@{p[1]})")
                        st.caption(str(p[4])[:16])
                        if p[2]:
                            st.write(p[2])
                        if p[3]:
                            img_obj = get_img_obj(p[3])
                            if img_obj:
                                st.image(img_obj, use_container_width=True)
                        render_reactions(p[0], p[5], me, 'posts')

    # === GROUP CHAT ===
    elif menu == "საერთო ჩათი":
        st.subheader("💬 საერთო ჩათი")
        
        # Chat messages container with fixed height
        chat_container = st.container()
        with chat_container:
            with st.container(height=500, border=False):
                messages = run_query(
                    """SELECT m.*, u.avatar 
                       FROM messages m 
                       LEFT JOIN users u ON m.sender = u.username 
                       WHERE m.receiver='general' 
                       ORDER BY m.timestamp""",
                    fetch=True
                )
                
                if not messages:
                    st.info("📭 შეტყობინებები არ არის")
                else:
                    for m in messages:
                        avatar_path = m[8] if len(m) > 8 and m[8] else None
                        avatar_img = get_img_64(avatar_path) if avatar_path else None
                        
                        with st.chat_message(m[1], avatar=avatar_img):
                            if st.button(m[1], key=f"mention_{m[0]}"):
                                st.session_state.chat_input_val = f"@{m[1]}: "
                                st.rerun()
                            
                            if m[3]:  # content
                                st.write(m[3])
                            if m[4]:  # image
                                img_obj = get_img_obj(m[4])
                                if img_obj:
                                    st.image(img_obj, width=250)
                            if m[5]:  # audio
                                st.audio(m[5])
        
        # Fixed space for bottom bar
        st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
        
        # Chat input bar
        render_chat_input_bar('general')

    # === PRIVATE MESSAGES ===
    elif menu.startswith("წერილები"):
        friends = get_friends(me)
        c_list, c_view = st.columns([0.3, 0.7])
        
        with c_list:
            st.write("**მეგობრები**")
            if not friends:
                st.info("მეგობრები არ გყავთ")
            else:
                for f in friends:
                    unr = run_query(
                        "SELECT count(*) FROM messages WHERE sender=? AND receiver=? AND read_status=0",
                        (f, me),
                        fetch_one=True
                    )
                    unread_count = unr[0] if unr else 0
                    
                    if st.button(
                        f"{f} {'🔴' if unread_count else ''}",
                        key=f"friend_{f}",
                        use_container_width=True
                    ):
                        st.session_state.active_friend_chat = f
                        run_query(
                            "UPDATE messages SET read_status=1 WHERE sender=? AND receiver=?",
                            (f, me)
                        )
                        st.cache_data.clear()
                        st.rerun()
        
        with c_view:
            tgt = st.session_state.active_friend_chat
            if not tgt:
                st.info("📭 აირჩიეთ მეგობარი")
            else:
                st.subheader(f"💬 საუბარი: {tgt}")
                
                # Chat messages container
                chat_container = st.container()
                with chat_container:
                    with st.container(height=500, border=False):
                        msgs_data = run_query(
                            """SELECT m.*, u.avatar 
                               FROM messages m 
                               LEFT JOIN users u ON m.sender = u.username 
                               WHERE (m.sender=? AND m.receiver=?) OR (m.sender=? AND m.receiver=?) 
                               ORDER BY m.timestamp""",
                            (me, tgt, tgt, me),
                            fetch=True
                        )
                        
                        if not msgs_data:
                            st.info("📭 შეტყობინებები არ არის")
                        else:
                            for m in msgs_data:
                                avatar_path = m[8] if len(m) > 8 and m[8] else None
                                avatar_img = get_img_64(avatar_path) if avatar_path else None
                                
                                with st.chat_message(m[1], avatar=avatar_img):
                                    if m[3]:  # content
                                        st.write(m[3])
                                    if m[4]:  # image
                                        img_obj = get_img_obj(m[4])
                                        if img_obj:
                                            st.image(img_obj, width=250)
                                    if m[5]:  # audio
                                        st.audio(m[5])
                
                # Fixed space for bottom bar
                st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
                
                # Chat input bar
                render_chat_input_bar(tgt)

    # === FRIENDS ===
    elif menu.startswith("მეგობრები"):
        t_search, t_req = st.tabs(["🔍 ძებნა", "📩 მოთხოვნები"])
        
        with t_search:
            src = st.text_input("მოძებნეთ მომხმარებელი...")
            if src:
                results = run_query(
                    "SELECT username, real_name, last_name FROM users WHERE username LIKE ? OR real_name LIKE ? OR last_name LIKE ?",
                    (f"%{src}%", f"%{src}%", f"%{src}%"),
                    fetch=True
                )
                
                if not results:
                    st.info("არავინ მოიძებნა")
                else:
                    for r in results:
                        c1, c2 = st.columns([0.7, 0.3])
                        full_name = f"{r[1]} {r[2]}" if r[1] else r[0]
                        c1.write(f"**{full_name}** (@{r[0]})")
                        
                        stt = run_query(
                            "SELECT status FROM friendships WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)",
                            (me, r[0], r[0], me),
                            fetch_one=True
                        )
                        
                        if r[0] == me:
                            c2.info("თქვენ")
                        elif not stt:
                            if c2.button("➕ დამატება", key=f"add_friend_{r[0]}"):
                                success = run_query(
                                    "INSERT INTO friendships (user1, user2, status) VALUES (?,?,'pending')",
                                    (me, r[0])
                                )
                                if success:
                                    st.toast("✅ მოთხოვნა გაიგზავნა")
                                    time.sleep(1)
                                    st.rerun()
                        elif stt[0] == 'pending':
                            c2.info("⏳ მოლოდინი")
                        else:
                            c2.success("✅ მეგობარი")
        
        with t_req:
            reqs_data = run_query(
                """SELECT f.id, f.user1, u.real_name, u.last_name 
                   FROM friendships f 
                   LEFT JOIN users u ON f.user1 = u.username 
                   WHERE f.user2=? AND f.status='pending'""",
                (me,),
                fetch=True
            )
            
            if not reqs_data:
                st.info("📭 მოთხოვნები არ არის")
            else:
                for rq in reqs_data:
                    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                    full_name = f"{rq[2]} {rq[3]}" if rq[2] else rq[1]
                    c1.write(f"**{full_name}** (@{rq[1]})")
                    
                    if c2.button("✅", key=f"accept_{rq[0]}"):
                        success = run_query(
                            "UPDATE friendships SET status='accepted' WHERE id=?",
                            (rq[0],)
                        )
                        if success:
                            st.cache_data.clear()
                            st.toast("✅ მეგობრობა დადასტურდა!")
                            time.sleep(1)
                            st.rerun()
                    
                    if c3.button("❌", key=f"reject_{rq[0]}"):
                        success = run_query(
                            "DELETE FROM friendships WHERE id=?",
                            (rq[0],)
                        )
                        if success:
                            st.cache_data.clear()
                            st.toast("❌ მოთხოვნა უარყოფილია")
                            time.sleep(1)
                            st.rerun()

    # === PROFILE ===
    elif menu == "პროფილი":
        render_profile_page(me, me)

    # === OTHER PROFILE VIEW ===
    if st.session_state.view_profile:
        st.write("---")
        if st.button("❌ დახურვა"):
            st.session_state.view_profile = None
            st.rerun()
        if st.session_state.view_profile:
            render_profile_page(st.session_state.view_profile, me)

if __name__ == '__main__':
    main()