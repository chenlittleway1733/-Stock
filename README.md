# way_stock

WAY AI 投資戰情室 Streamlit 專案。

## 執行環境

- 建議 Python：3.11 以上
- Streamlit Cloud：`runtime.txt` 已指定 `python-3.11`
- 本機若有 pyenv/asdf，可讀取 `.python-version` 使用 Python 3.11

## 本機啟動

```bash
python -m pip install -r requirements.txt
python tools/check_runtime.py
streamlit run app.py
```

登入密碼請在 Streamlit Secrets 或本機 `.streamlit/secrets.toml` 設定：

```toml
APP_PASSWORD = "你的密碼"
```

## 測試

```bash
python -m unittest tests/test_core_models.py
```

## 打包

```bash
python tools/build_clean_package.py
```

打包規則由 `.packageignore` 控制；預設會排除舊 zip、Python cache、macOS `._*` metadata、`tmp/`、`output/` 與本機 secrets。
