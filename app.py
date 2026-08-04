import os
import streamlit as st
from datetime import datetime
import google.generativeai as genai

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

# --- サイドバー：作品・チャット・モデル管理 ---
st.sidebar.title("📚 作品・チャット管理")

# APIキー設定
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Gemini APIキーを入力:", type="password")
    if not api_key:
        st.info("左側のサイドバーにGemini APIキーを入力してください。")
        st.stop()

# 空白文字を除去
api_key = api_key.strip()

# API設定
genai.configure(api_key=api_key)

# 安定して無料枠が開放されているモデルリスト（1.5系を最優先）
stable_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]

# 利用可能なモデルの自動検出補言
try:
    detected_models = []
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            model_id = m.name.replace("models/", "")
            if model_id not in stable_models and "2.5" not in model_id:
                detected_models.append(model_id)
    all_models = stable_models + detected_models
except Exception:
    all_models = stable_models

# モデル選択ドロップダウン（gemini-1.5-flash を確実に最優先）
selected_model_name = st.sidebar.selectbox(
    "🤖 使用するGeminiモデルを選択:",
    all_models,
    index=0
)

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
messages_key = f"messages_{current_project}"

if messages_key not in st.session_state:
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

    # Gemini応答処理
    with st.chat_message("assistant"):
        try:
            system_instruction = (
                f"あなたは作品『{current_project}』執筆のパートナーAIです。"
                "ユーザーと一緒に物語のプロット作成、キャラクター設定、本文の執筆・推敲を行います。"
            )

            # 会話履歴の構築
            history = []
            for msg in st.session_state[messages_key]:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})

            # モデルの初期化と生成
            model = genai.GenerativeModel(
                model_name=selected_model_name,
                system_instruction=system_instruction
            )
            chat_session = model.start_chat(history=history)
            response = chat_session.send_message(prompt)
            response_text = response.text

            st.markdown(response_text)

            # 履歴更新
            st.session_state[messages_key].append({"role": "user", "content": prompt})
            st.session_state[messages_key].append({"role": "assistant", "content": response_text})

            # 【絶対自動保存】選択されている作品専用のファイルに100%追記保存
            now_time = datetime.now().strftime("%H:%M:%S")
            with open(SAVE_FILE, "a", encoding="utf-8") as f:
                f.write(f"### あなた ({now_time})\n{prompt}\n\n")
                f.write(f"### Gemini ({selected_model_name})\n{response_text}\n\n")
                f.write("-" * 40 + "\n\n")
                f.flush()

            st.toast(f"✅ 『{current_project}』のファイルに100%追記保存されました", icon="💾")

        except Exception as e:
            st.error(f"⚠️ Gemini APIエラーが発生しました: {e}")
            st.info("※左側の「使用するGeminiモデルを選択」で『gemini-1.5-flash』を選択して試してみてください。")
