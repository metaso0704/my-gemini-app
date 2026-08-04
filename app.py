import os
import streamlit as st
from datetime import datetime
from google import genai

# ページ基本設定
st.set_page_config(page_title="Gemini 小説執筆＆絶対自動保存アプリ", page_icon="📝")

# --- パスワード保護設定 ---
APP_PASSWORD = os.environ.get("APP_PASSWORD", "secret123") # デフォルトパスワード（自由に変更可能）

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

# --- チャットアプリ本体 ---
st.title("📝 Gemini 小説執筆＆絶対自動保存チャット")

# サイドバー設定
st.sidebar.title("設定・ダウンロード")
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Gemini APIキーを入力:", type="password")
    if not api_key:
        st.info("左側のサイドバーにGemini APIキーを入力してください。")
        st.stop()

# クライアント初期化
client = genai.Client(api_key=api_key)

SAVE_FILE = "my_novel_master_draft.md"

# セッション状態の初期化
if "chat" not in st.session_state:
    system_instruction = (
        "あなたは小説執筆のパートナーAIです。"
        "ユーザーと一緒に物語のプロット作成、キャラクター設定、本文の執筆・推敲を行います。"
    )
    st.session_state.chat = client.chats.create(
        model="gemini-2.5-flash",
        config={"system_instruction": system_instruction}
    )
    st.session_state.messages = []

    # 初回ファイルヘッダーの作成
    if not os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "a", encoding="utf-8") as f:
            f.write(f"# 小説執筆マスターログ（全会話絶対保存）\n")
            f.write(f"作成開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=" * 50 + "\n\n")
            f.flush()

# いつでも蓄積された小説ファイルをスマホにダウンロードできるボタン
if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        file_data = f.read()
    st.sidebar.download_button(
        label="📥 蓄積された小説ファイルをダウンロード",
        data=file_data,
        file_name="my_novel_master_draft.md",
        mime="text/markdown"
    )

# 過去のメッセージ表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# チャット入力
if prompt := st.chat_input("会話を入力..."):
    # ユーザー表示
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Gemini応答処理
    with st.chat_message("assistant"):
        response = st.session_state.chat.send_message(prompt)
        response_text = response.text
        st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})

    # 【絶対自動保存の核】
    # システムプログラムが毎回必ず同じファイルの末尾に追記を実行します。
    with open(SAVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"### あなた ({datetime.now().strftime('%H:%M:%S')})\n{prompt}\n\n")
        f.write(f"### Gemini\n{response_text}\n\n")
        f.write("-" * 40 + "\n\n")
        f.flush()

    st.toast("✅ 1つのファイルに絶対漏れなく即座に追記保存されました", icon="💾")
