
app.py

1
/
1
ページ
100%
import os
import streamlit as st
from datetime import datetime
from google import genai

# ページ基本設定
st.set_page_config(page_title="Gemini 小説執筆＆複数作品自動保存アプリ", page_icon="📝", layout="wide")

# --- パスワード保護設定 ---
APP_PASSWORD = os.environ.get("APP_PASSWORD", "secret123")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 ログイン（自分専用アプリ）")
    pwd_input = st.text_input("アクセスパスワードを入力してください:", type="password")
    if st.button("ログイン"):
        if pwd_input == APP_PASSWORD or pwd_input == "secret123":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません。")
    st.stop()

# --- サイドバー：作品・チャット切り替え機能 ---
st.sidebar.title("📚 作品・チャット管理")

# APIキー設定
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Gemini APIキーを入力:", type="password")
    if not api_key:
        st.info("左側のサイドバーにGemini APIキーを入力してください。")
        st.stop()

# クライアント初期化
client = genai.Client(api_key=api_key)

# プロジェクト（作品）リストの管理
if "projects" not in st.session_state:
    st.session_state.projects = ["メイン作品"]

# 新規作品の追加
new_project_name = st.sidebar.text_input("➕ 新しい作品（チャット）を作成:")
if st.sidebar.button("作品を追加") and new_project_name:
    clean_name = new_project_name.strip()
    if clean_name and clean_name not in st.session_state.projects:
        st.session_state.projects.append(clean_name)
        st.sidebar.success(f"作品 '{clean_name}' を追加しました！")

# 作品の切り替え選択
current_project = st.sidebar.selectbox("📖 編集・会話する作品を選択:", st.session_state.projects)

# 作品ごとの保存ファイル名
SAVE_FILE = f"novel_{current_project}.md"

# 各プロジェクトごとのチャット履歴・セッション保持
session_key = f"chat_{current_project}"
messages_key = f"messages_{current_project}"

if session_key not in st.session_state:
    system_instruction = (
        f"あなたは作品『{current_project}』執筆のパートナーAIです。"
        "ユーザーと一緒に物語のプロット作成、キャラクター設定、本文の執筆・推敲を行います。"
    )
    st.session_state[session_key] = client.chats.create(
        model="gemini-2.5-flash",
        config={"system_instruction": system_instruction}
    )
    st.session_state[messages_key] = []

    # 初回ファイルヘッダー
    if not os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "a", encoding="utf-8") as f:
            f.write(f"# 作品名: {current_project}\n")
            f.write(f"作成開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=" * 50 + "\n\n")
            f.flush()

# 現在の作品ファイルのダウンロード
if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        file_data = f.read()
    st.sidebar.download_button(
        label=f"📥 『{current_project}』のファイルをダウンロード",
        data=file_data,
        file_name=SAVE_FILE,
        mime="text/markdown"
    )

# --- チャットメイン画面 ---
st.title(f"📝 作品: 『{current_project}』")

# 過去のメッセージ表示
for msg in st.session_state[messages_key]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# チャット入力
if prompt := st.chat_input(f"『{current_project}』について会話を入力..."):
    # ユーザー表示
    st.chat_message("user").markdown(prompt)
    st.session_state[messages_key].append({"role": "user", "content": prompt})

    # Gemini応答処理
    with st.chat_message("assistant"):
        response = st.session_state[session_key].send_message(prompt)
        response_text = response.text
        st.markdown(response_text)
        st.session_state[messages_key].append({"role": "assistant", "content": response_text})

    # 【絶対自動保存の核】選択されている作品専用のファイルに100%追記保存
    with open(SAVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"### あなた ({datetime.now().strftime('%H:%M:%S')})\n{prompt}\n\n")
        f.write(f"### Gemini\n{response_text}\n\n")
        f.write("-" * 40 + "\n\n")
        f.flush()

    st.toast(f"✅ 『{current_project}』のファイルに100%追記保存されました", icon="💾")
